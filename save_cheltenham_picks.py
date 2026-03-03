"""
SAVE CHELTENHAM PICKS TO DYNAMODB
===================================
Runs daily to:
  1. Score ALL 28 2026 Festival races via the SureBet engine (surebet_intel.py)
  2. Compare with yesterday's pick for each race
  3. Detect any changes and record WHY the pick changed
  4. Save to CheltenhamPicks DynamoDB table with full history + per-horse scoring

Usage:
    python save_cheltenham_picks.py            # Save today's picks
    python save_cheltenham_picks.py --history  # Show pick change history
    python save_cheltenham_picks.py --today    # Print today's picks only (no save)
"""

import sys, os
import boto3
import argparse
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

# ── path setup so barrys/ sub-package is importable ─────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Import the full 28-race SureBet scoring engine
from barrys.surebet_intel import build_all_picks

# Festival day → DynamoDB day-key mapping
DAY_TO_DYNAMO = {
    1: "Tuesday_10_March",
    2: "Wednesday_11_March",
    3: "Thursday_12_March",
    4: "Friday_13_March",
}

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

# Table: CheltenhamPicks
# PK: race_name   SK: pick_date
PICKS_TABLE = 'CheltenhamPicks'


def get_picks_table():
    return dynamodb.Table(PICKS_TABLE)


def ensure_table_exists():
    """Create CheltenhamPicks if it doesn't exist"""
    try:
        client = boto3.client('dynamodb', region_name='eu-west-1')
        existing = client.list_tables().get('TableNames', [])   # list of strings
        if PICKS_TABLE not in existing:
            print(f"Creating {PICKS_TABLE} table...")
            client.create_table(
                TableName=PICKS_TABLE,
                KeySchema=[
                    {'AttributeName': 'race_name', 'KeyType': 'HASH'},
                    {'AttributeName': 'pick_date', 'KeyType': 'RANGE'},
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'race_name', 'AttributeType': 'S'},
                    {'AttributeName': 'pick_date', 'AttributeType': 'S'},
                ],
                BillingMode='PAY_PER_REQUEST',
            )
            # Wait for table to be active
            waiter = client.get_waiter('table_exists')
            waiter.wait(TableName=PICKS_TABLE)
            print(f"Table {PICKS_TABLE} created.")
        else:
            print(f"Table {PICKS_TABLE} already exists.")
    except Exception as e:
        print(f"Warning: Could not check/create table: {e}")


def _tier(score):
    if score >= 155: return "A+  ELITE"
    if score >= 140: return "A   ELITE"
    if score >= 120: return "B   EXCELLENT"
    if score >= 100: return "C   STRONG"
    if score >= 80:  return "D   FAIR"
    return               "E   WEAK"


def score_all_races():
    """
    Score all 28 Cheltenham 2026 races using the SureBet engine.
    Returns a dict keyed by race_name with enriched pick data including
    the full ordered field (all_horses).
    """
    raw_picks = build_all_picks(verbose=True)   # verbose=True → full scored list

    picks = {}
    for race_key, r in raw_picks.items():
        scored = r.get("scored", [])
        if not scored:
            continue

        top = scored[0]
        second_score = scored[1]["score"] if len(scored) > 1 else 0

        top_score = top["score"]
        confidence = (
            'HIGH'   if top_score >= 140 else
            'MEDIUM' if top_score >= 100 else
            'LOW'
        )

        race_name = r["race_name"]
        dynamo_day = DAY_TO_DYNAMO.get(r["day"], f"Day_{r['day']}")

        picks[race_name] = {
            'race_name':    race_name,
            'race_key':     race_key,
            'day':          dynamo_day,
            'race_time':    r.get("time", ""),
            'grade':        r["grade"],
            'distance':     '',
            'horse':        top["name"],
            'trainer':      top.get("trainer", ""),
            'jockey':       top.get("jockey", ""),
            'odds':         '?',                     # live odds via Betfair
            'age':          '',
            'form':         '',
            'rating':       0,
            'score':        top_score,
            'tier':         _tier(top_score),
            'value_rating': top.get("value_r", 0),
            'second_score': second_score,
            'score_gap':    top_score - second_score,
            'confidence':   confidence,
            'reasons':      top.get("tips", [])[:6],
            'warnings':     top.get("warnings", []),
            # Full ordered field ──────────────────────────────────────────
            'all_horses':   [
                {
                    'name':             h["name"],
                    'trainer':          h.get("trainer", ""),
                    'jockey':           h.get("jockey", ""),
                    'score':            h["score"],
                    'tier':             _tier(h["score"]),
                    'value_rating':     h.get("value_r", 0),
                    'tips':             h.get("tips", []),
                    'warnings':         h.get("warnings", []),
                    'cheltenham_record': h.get("cheltenham_record", ""),
                    'is_surebet_pick':  h["name"] == top["name"],
                }
                for h in scored
            ],
        }

    return picks


def get_yesterday_picks(table, today_str):
    """Fetch all picks saved for yesterday"""
    yesterday = (datetime.strptime(today_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        response = table.scan(
            FilterExpression='pick_date = :d',
            ExpressionAttributeValues={':d': yesterday},
        )
        items = response.get('Items', [])
        return {item['race_name']: item for item in items}
    except Exception as e:
        print(f"Warning: could not fetch yesterday's picks: {e}")
        return {}


def detect_changes(today_pick, yesterday_pick):
    """Compare today vs yesterday pick for a race and return change info"""
    if not yesterday_pick:
        return False, None, None, 'First time pick recorded'

    prev_horse = yesterday_pick.get('horse', '')
    curr_horse = today_pick['horse']

    if prev_horse != curr_horse:
        prev_score = float(yesterday_pick.get('score', 0))
        curr_score  = today_pick['score']
        reason = (
            f"Pick changed from {prev_horse} (score {prev_score:.0f}) "
            f"to {curr_horse} (score {curr_score:.0f}) "
            f"+{curr_score - prev_score:.0f} pts difference"
        )
        return True, prev_horse, yesterday_pick.get('odds', ''), reason

    return False, None, None, 'Pick unchanged'


def save_picks(dry_run=False):
    """Main function: score races, detect changes, save to DynamoDB"""
    today = datetime.now().strftime('%Y-%m-%d')

    print(f"\n{'='*70}")
    print(f"  CHELTENHAM PICKS SAVE  -  {today}")
    print(f"{'='*70}\n")

    if not dry_run:
        ensure_table_exists()

    table = get_picks_table()
    today_picks = score_all_races()
    yesterday_picks = get_yesterday_picks(table, today) if not dry_run else {}

    changes = []
    saved = 0
    unchanged = 0

    for race_name, pick in sorted(today_picks.items(), key=lambda x: x[1]['day']):
        yesterday = yesterday_picks.get(race_name)
        changed, prev_horse, prev_odds, change_reason = detect_changes(pick, yesterday)

        if changed:
            changes.append({
                'race': race_name,
                'from': prev_horse,
                'to':   pick['horse'],
                'reason': change_reason,
            })
            marker = '>> CHANGED <<'
        else:
            marker = '             '

        print(f"  {marker}  {race_name}")
        print(f"              -> {pick['horse']} @ {pick['odds']}  "
              f"[score {pick['score']}  |  {pick['tier']}  |  {pick['confidence']}]")
        if changed:
            print(f"              ** Was: {prev_horse} @ {prev_odds}")
        print()

        if not dry_run:
            item = {
                'race_name':       race_name,
                'pick_date':       today,
                'day':             pick['day'],
                'race_time':       pick['race_time'],
                'grade':           pick['grade'],
                'distance':        pick['distance'],
                'horse':           pick['horse'],
                'trainer':         pick['trainer'],
                'jockey':          pick['jockey'],
                'odds':            pick['odds'],
                'age':             str(pick['age']),
                'form':            pick['form'],
                'rating':          Decimal(str(pick['rating'])),
                'score':           Decimal(str(pick['score'])),
                'tier':            pick['tier'],
                'value_rating':    Decimal(str(round(pick['value_rating'], 1))),
                'second_score':    Decimal(str(pick['second_score'])),
                'score_gap':       Decimal(str(pick['score_gap'])),
                'confidence':      pick['confidence'],
                'reasons':         pick['reasons'],
                'warnings':        pick['warnings'],
                'pick_changed':    changed,
                'previous_horse':  prev_horse or '',
                'previous_odds':   prev_odds or '',
                'change_reason':   change_reason,
                'updated_at':      datetime.now().isoformat(),
                # Full ordered field with scoring breakdown
                'all_horses':     [
                    {
                        'name':              h['name'],
                        'trainer':           h['trainer'],
                        'jockey':            h['jockey'],
                        'score':             Decimal(str(h['score'])),
                        'tier':              h['tier'],
                        'value_rating':      Decimal(str(round(h['value_rating'], 1))),
                        'tips':              h['tips'],
                        'warnings':          h['warnings'],
                        'cheltenham_record': h['cheltenham_record'],
                        'is_surebet_pick':   h['is_surebet_pick'],
                    }
                    for h in pick['all_horses']
                ],
            }
            try:
                table.put_item(Item=item)
                saved += 1
            except Exception as e:
                print(f"  ERROR saving {race_name}: {e}")

    print(f"\n{'='*70}")
    print(f"  SUMMARY:")
    print(f"  Races processed: {len(today_picks)}")
    if not dry_run:
        print(f"  Saved to DynamoDB: {saved}")
    print(f"  Pick changes today: {len(changes)}")

    if changes:
        print(f"\n  CHANGED PICKS:")
        for c in changes:
            print(f"    {c['race']}: {c['from']} -> {c['to']}")
            print(f"      Reason: {c['reason']}")
    else:
        print(f"\n  All picks unchanged from yesterday.")
    print(f"{'='*70}\n")

    return today_picks, changes


def show_history(race_name=None, days=14):
    """Show pick change history from DynamoDB"""
    table = get_picks_table()

    print(f"\n{'='*70}")
    print(f"  PICK HISTORY (last {days} days)")
    if race_name:
        print(f"  Race: {race_name}")
    print(f"{'='*70}\n")

    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    try:
        if race_name:
            response = table.query(
                KeyConditionExpression='race_name = :r AND pick_date >= :d',
                ExpressionAttributeValues={
                    ':r': race_name,
                    ':d': cutoff,
                },
                ScanIndexForward=False,   # newest first
            )
            items = response.get('Items', [])
        else:
            response = table.scan(
                FilterExpression='pick_date >= :d',
                ExpressionAttributeValues={':d': cutoff},
            )
            items = response.get('Items', [])

        if not items:
            print("  No history found.")
            return

        # Group by race
        by_race = defaultdict(list)
        for item in items:
            by_race[item['race_name']].append(item)

        for rname in sorted(by_race.keys()):
            entries = sorted(by_race[rname], key=lambda x: x['pick_date'], reverse=True)
            print(f"  {rname}")
            for e in entries:
                changed_marker = '>> CHANGED <<' if e.get('pick_changed') else '             '
                print(f"    {e['pick_date']}  {changed_marker}  "
                      f"{e['horse']} @ {e['odds']}  "
                      f"[{e['score']}/100  {e['confidence']}]")
                if e.get('pick_changed') and e.get('previous_horse'):
                    print(f"              Was: {e['previous_horse']} @ {e.get('previous_odds', '')}")
            print()

    except Exception as e:
        print(f"  Error reading history: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Save/view Cheltenham 2026 picks')
    parser.add_argument('--history', action='store_true', help='Show pick change history')
    parser.add_argument('--today',   action='store_true', help='Print today\'s picks without saving')
    parser.add_argument('--race',    type=str,  default=None, help='Filter history to a specific race')
    parser.add_argument('--days',    type=int,  default=14,   help='Days of history to show (default 14)')
    args = parser.parse_args()

    if args.history:
        show_history(race_name=args.race, days=args.days)
    elif args.today:
        save_picks(dry_run=True)
    else:
        save_picks(dry_run=False)
