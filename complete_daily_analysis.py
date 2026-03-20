# -*- coding: utf-8 -*-
"""
COMPLETE DAILY WORKFLOW -- 3-PICK SELECTION ENGINE
===================================================
Strategy:
  1. Score EVERY horse in EVERY race with the comprehensive 7-factor model
  2. For each race, identify the single best-scoring horse  (race winner candidate)
  3. Across all races, rank those race-bests by score — select TOP 3
  4. Mark exactly those 3 as show_in_ui=True; everything else is learning data
  5. Minimum confidence gate: a race-best must score >= 60 to be eligible as a UI pick
     (if a race has no horse above 60, we consider it too unpredictable and skip it)

This ensures:
  - Exactly 3 picks per day (or fewer if fewer than 3 races have enough confidence)
  - Each pick comes from a DIFFERENT race (no duplicates)
  - We always back the BEST horse in each race, not any horse above an arbitrary threshold
  - The self-learning system (daily_learning.py) continues to refine weights nightly
"""

import json
import boto3
from boto3.dynamodb.conditions import Attr
from datetime import datetime
from decimal import Decimal
from comprehensive_pick_logic import analyze_horse_comprehensive

db    = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

TARGET_PICKS   = 3      # How many UI picks to surface each day
MIN_CONFIDENCE = 60     # Minimum score for a race-best to qualify as a UI pick


def load_horse_history():
    """
    Scan DynamoDB for all previous results (analysis_type=comprehensive_7factor)
    where result_won is set.  Returns a dict: horse_name -> {wins, runs, win_rate}.
    Used to enrich scoring context with database knowledge of each horse.
    """
    print("Loading horse history from DynamoDB...")
    history = {}  # horse -> {'wins': int, 'runs': int}
    kwargs = {'FilterExpression': Attr('analysis_type').eq('comprehensive_7factor') & Attr('result_won').exists()}
    while True:
        resp = table.scan(**kwargs)
        for item in resp.get('Items', []):
            name = item.get('horse', item.get('horse_name', ''))
            if not name:
                continue
            won = item.get('result_won') in (True, 'true', 'True', 1, '1')
            rec = history.setdefault(name, {'wins': 0, 'runs': 0})
            rec['runs'] += 1
            if won:
                rec['wins'] += 1
        lk = resp.get('LastEvaluatedKey')
        if not lk:
            break
        kwargs['ExclusiveStartKey'] = lk
    # Compute win rate
    for name, rec in history.items():
        rec['win_rate'] = rec['wins'] / rec['runs'] if rec['runs'] > 0 else 0.0
    print(f"  Horse history loaded: {len(history)} horses tracked in DB")
    return history


def load_races():
    """Load races from Betfair fetch (response_horses.json)."""
    try:
        with open('response_horses.json', 'r') as f:
            data = json.load(f)
        return data.get('races', [])
    except FileNotFoundError:
        print("ERROR: Run 'python betfair_odds_fetcher.py' first")
        return []


def tier_from_score(score):
    if score >= 90: return "ELITE",   "ELITE (Top-tier confidence)", "green"
    if score >= 80: return "STRONG",  "STRONG (High confidence)",    "green"
    if score >= 70: return "GOOD",    "GOOD (Solid pick)",           "light-green"
    if score >= 60: return "FAIR",    "FAIR (Decent chance)",        "light-amber"
    if score >= 45: return "RISKY",   "RISKY (Lower confidence)",    "dark-amber"
    return              "POOR",   "POOR (Very unlikely)",        "red"


def analyze_and_save_all():
    """
    Two-pass algorithm:
      Pass 1 — Score every horse, collect per-race bests.
      Select top-3 cross-race bests.
      Pass 2 — Save everything with correct show_in_ui flag.
    """
    races = load_races()
    if not races:
        print("No races found — run betfair_odds_fetcher.py first")
        return

    print("\n" + "=" * 100)
    print("DAILY 3-PICK SELECTION ENGINE")
    print("=" * 100)
    print(f"  Races    : {len(races)}")
    print(f"  Strategy : Best horse per race -> top {TARGET_PICKS} cross-race bests (min score {MIN_CONFIDENCE})")
    print("=" * 100 + "\n")

    today        = datetime.now().strftime('%Y-%m-%d')
    avg_winner_odds = 4.65  # UK average winning SP

    # Pre-load horse history from DynamoDB so we can enrich each pick
    horse_history = load_horse_history()

    # ── PASS 1 ───────────────────────────────────────────────────────────────
    # Build a list of races, each containing scored runner items.
    # Also track the best-scoring horse in each race.
    all_races_data = []  # [{venue, race_time, market_id, runners:[{item, score}], best_idx}]

    for race in races:
        venue      = race.get('venue', 'Unknown')
        race_time  = race.get('start_time', '')
        market_id  = race.get('marketId', '')
        runners    = race.get('runners', [])

        print(f"[{venue}  {race_time[:16]}]  {len(runners)} runners")

        # Find the race favourite (lowest decimal odds) — used as market signal
        valid_runners = [r for r in runners if float(r.get('odds', 0)) > 1.0]
        favourite_odds = min((float(r.get('odds', 99)) for r in valid_runners), default=99)

        # Collect weight_lbs for every runner in this race so scoring can do relative comparison
        field_weights = [int(r.get('weight_lbs', 0) or 0) for r in runners if int(r.get('weight_lbs', 0) or 0) > 0]

        race_runners = []
        for runner in runners:
            horse_name = runner.get('name', 'Unknown')
            odds       = float(runner.get('odds', 0))

            score, breakdown, reasons = analyze_horse_comprehensive(
                runner,
                venue,
                avg_winner_odds=avg_winner_odds,
                course_winners_today=0,
                field_weights=field_weights,
            )

            # ── Database history bonus ───────────────────────────────────────
            # If we've seen this horse before and it has a meaningful win rate,
            # reward it.  A >40% DB win rate is genuinely exceptional.
            db_stats = horse_history.get(horse_name, {})
            if db_stats.get('runs', 0) >= 2:
                win_rate = db_stats.get('win_rate', 0.0)
                if win_rate >= 0.40:
                    db_bonus = 15
                elif win_rate >= 0.25:
                    db_bonus = 8
                elif win_rate >= 0.10:
                    db_bonus = 4
                else:
                    db_bonus = 0
                if db_bonus:
                    score += db_bonus
                    reasons.append(f"DB history: {int(win_rate*100)}% win rate ({db_stats['wins']}/{db_stats['runs']} runs): +{db_bonus}pts")
                    breakdown['db_history'] = db_bonus

            # ── Market-leader bonus ──────────────────────────────────────────
            # The race favourite aggregates all public information.
            # When our model agrees with the market (our top scorer is also the
            # market favourite), confidence increases significantly.
            market_leader_bonus = 0
            if odds > 1.0 and odds == favourite_odds:
                market_leader_bonus = 12   # Race favourite
                score += market_leader_bonus
                reasons.append(f"Race market leader (lowest odds): +{market_leader_bonus}pts")
                breakdown['market_leader'] = market_leader_bonus
            elif odds > 1.0 and odds <= favourite_odds * 1.25:
                market_leader_bonus = 5    # Within 25% of favourite = second choice
                score += market_leader_bonus
                reasons.append(f"Market second choice: +{market_leader_bonus}pts")
                breakdown['market_leader'] = market_leader_bonus

            confidence_level, confidence_grade, confidence_color = tier_from_score(score)

            bet_id = (f"{race_time}_{venue}_{horse_name}"
                      .replace(' ', '_').replace(':', '').replace('.', ''))

            item = {
                'bet_id':              bet_id,
                'bet_date':            today,
                'course':              venue,
                'race_course':         venue,
                'race_time':           race_time,
                'horse':               horse_name,
                'jockey':              runner.get('jockey', ''),
                'trainer':             runner.get('trainer', ''),
                'form':                runner.get('form', ''),
                'weight_lbs':          runner.get('weight_lbs', 0),
                'age':                 runner.get('age', ''),
                'official_rating':     runner.get('official_rating', ''),
                'draw':                runner.get('draw', ''),
                'odds':                Decimal(str(odds)) if odds else Decimal('0'),
                'decimal_odds':        Decimal(str(odds)) if odds else Decimal('0'),
                'combined_confidence': Decimal(str(score)),
                'comprehensive_score': Decimal(str(score)),
                'confidence_level':    confidence_level,
                'confidence_grade':    confidence_grade,
                'confidence_color':    confidence_color,
                'show_in_ui':          False,   # will be set in pass 2
                'recommended_bet':     False,   # will be set in pass 2
                'is_learning_pick':    True,    # will be set in pass 2
                'pick_rank':           0,       # 1/2/3 for top picks; 0 = learning
                'analysis_type':       'comprehensive_7factor',
                'score_breakdown':     breakdown,
                'selection_reasons':   reasons,
                'sport':               'horses',
                'market_id':           market_id,
                'selection_id':        runner.get('selectionId', 0),
                'race_coverage_pct':   Decimal('100'),
                'race_total_count':    len(runners),
                'created_at':          datetime.now().isoformat(),
                # Horse history from DB
                'history_wins':        db_stats.get('wins', 0),
                'history_runs':        db_stats.get('runs', 0),
                'history_win_rate':    Decimal(str(round(db_stats.get('win_rate', 0.0), 4))),
            }

            race_runners.append({'item': item, 'score': score, 'horse': horse_name, 'odds': odds, 'history': db_stats})

        if not race_runners:
            continue

        # Best horse in this race; also compute score_gap vs second-best
        best = max(race_runners, key=lambda x: x['score'])
        sorted_by_score = sorted(race_runners, key=lambda x: x['score'], reverse=True)
        second_score = sorted_by_score[1]['score'] if len(sorted_by_score) > 1 else best['score']
        score_gap = max(0, best['score'] - second_score)
        best['item']['score_gap'] = Decimal(str(round(score_gap, 1)))
        all_races_data.append({
            'venue':     venue,
            'race_time': race_time,
            'runners':   race_runners,
            'best':      best,
        })

    # ── SELECT TOP 3 CROSS-RACE BESTS ────────────────────────────────────────
    eligible = [r for r in all_races_data if r['best']['score'] >= MIN_CONFIDENCE]
    eligible.sort(key=lambda r: r['best']['score'], reverse=True)
    top_picks = eligible[:TARGET_PICKS]

    # Build a set of bet_ids for the 3 winners
    top_bet_ids = {r['best']['item']['bet_id']: rank
                   for rank, r in enumerate(top_picks, start=1)}

    print("\n" + "=" * 100)
    print(f"TOP {len(top_picks)} PICKS SELECTED")
    print("=" * 100)
    for rank, r in enumerate(top_picks, start=1):
        b = r['best']
        print(f"  #{rank}  {b['horse']:28}  @{b['odds']:5.2f}  Score: {b['score']:3.0f}  "
              f"[{r['venue']}  {r['race_time'][:16]}]")
    if not top_picks:
        print("  WARNING: No races met the minimum confidence threshold — no UI picks today")
    print("=" * 100 + "\n")

    # ── PASS 2 — SAVE ALL ITEMS ───────────────────────────────────────────────
    total_saved = 0
    ui_promoted = 0

    for race_data in all_races_data:
        race_total = len(race_data['runners'])
        for r in race_data['runners']:
            item  = r['item']
            bid   = item['bet_id']
            rank  = top_bet_ids.get(bid, 0)
            is_ui = rank > 0

            item['show_in_ui']      = is_ui
            item['recommended_bet'] = is_ui
            item['is_learning_pick']= not is_ui
            item['pick_rank']       = rank
            item['race_analyzed_count'] = race_total

            try:
                table.put_item(Item=item)
                total_saved += 1
                if is_ui:
                    ui_promoted += 1
                    print(f"  >> PICK #{rank}: {item['horse']:28} @{float(item['odds']):5.2f}  "
                          f"Score:{r['score']:3.0f}  [{race_data['venue']}]")
                else:
                    print(f"  -  Learning: {item['horse']:28} @{float(item['odds']):5.2f}  "
                          f"Score:{r['score']:3.0f}")
            except Exception as e:
                print(f"  ERROR saving {item['horse']}: {e}")

    print(f"\nSaved {total_saved} horses | {ui_promoted} UI picks | "
          f"{total_saved - ui_promoted} learning records\n")
    return {'total': total_saved, 'ui_picks': ui_promoted, 'learning': total_saved - ui_promoted}


if __name__ == "__main__":
    stats = analyze_and_save_all()
    if stats:
        if stats['ui_picks']:
            print(f"✓ {stats['ui_picks']} picks ready — run 'python show_todays_ui_picks.py' to review")
        else:
            print("⚠ No high-confidence picks today — check response_horses.json for race data")


