"""
Sporting Life Results Fetcher
=============================
Fetches race results from sportinglife.com and records WIN/LOSS for pending picks.
Run 30+ minutes after each race or once at end of day.

Usage:
    python sl_results_fetcher.py              # today
    python sl_results_fetcher.py 2026-03-20   # specific date
"""

import re
import sys
import json
import requests
import boto3
from datetime import date, datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

sys.stdout.reconfigure(encoding='utf-8')

# ── Config ────────────────────────────────────────────────────────────────────
TARGET_DATE = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime('%Y-%m-%d')

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.5',
    'Referer': 'https://www.sportinglife.com/',
}

# SL URL slug  →  DB course name
COURSE_MAP = {
    'musselburgh': 'Musselburgh', 'lingfield': 'Lingfield',
    'newbury': 'Newbury', 'wolverhampton': 'Wolverhampton',
    'cheltenham': 'Cheltenham', 'kempton': 'Kempton',
    'ascot': 'Ascot', 'haydock': 'Haydock',
    'sandown': 'Sandown', 'chester': 'Chester',
    'goodwood': 'Goodwood', 'york': 'York',
    'leicester': 'Leicester', 'nottingham': 'Nottingham',
    'carlisle': 'Carlisle', 'catterick': 'Catterick',
    'newcastle': 'Newcastle', 'hamilton': 'Hamilton',
    'perth': 'Perth', 'ayr': 'Ayr',
    'wetherby': 'Wetherby', 'doncaster': 'Doncaster',
    'exeter': 'Exeter', 'taunton': 'Taunton',
    'hereford': 'Hereford', 'huntingdon': 'Huntingdon',
    'ludlow': 'Ludlow', 'market-rasen': 'Market Rasen',
    'plumpton': 'Plumpton', 'stratford': 'Stratford',
    'uttoxeter': 'Uttoxeter', 'windsor': 'Windsor',
    'wincanton': 'Wincanton', 'ffos-las': 'Ffos Las',
    'sedgefield': 'Sedgefield', 'southwell': 'Southwell',
    'bangor': 'Bangor', 'worcester': 'Worcester',
    'warwick': 'Warwick', 'bath': 'Bath',
    'chepstow': 'Chepstow', 'epsom': 'Epsom',
    'pontefract': 'Pontefract', 'ripon': 'Ripon',
    'redcar': 'Redcar', 'beverley': 'Beverley',
    'thirsk': 'Thirsk', 'brighton': 'Brighton',
}

SL_BASE = 'https://www.sportinglife.com'

# ── Helpers ───────────────────────────────────────────────────────────────────
def norm(name: str) -> str:
    """Normalise horse name for comparison: lower, strip country code."""
    n = re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', name or '').strip().lower()
    return n

def fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.text
        print(f"  HTTP {r.status_code}: {url}")
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
    return None

# ── Step 1: Get completed race URLs from results index ─────────────────────────
def get_race_urls(date_str):
    """Return list of (course_slug, course_name, race_id, race_url)."""
    idx_url = f'{SL_BASE}/racing/results/{date_str}/'
    print(f"Fetching results index: {idx_url}")
    html = fetch(idx_url)
    if not html:
        return []

    # Extract the FULL race links from the index - pattern:
    # href="/racing/results/2026-03-20/musselburgh/908670/race-name-slug"
    pat = r'href="(/racing/results/' + re.escape(date_str) + r'/([^/]+)/(\d+)/[^"]+)"'
    seen = set()
    races = []
    for m in re.finditer(pat, html):
        full_path, course_slug, race_id = m.group(1), m.group(2), m.group(3)
        key = (course_slug, race_id)
        if key in seen:
            continue
        seen.add(key)
        course_name = COURSE_MAP.get(course_slug, course_slug.replace('-', ' ').title())
        race_url = SL_BASE + full_path
        races.append((course_slug, course_name, race_id, race_url))

    print(f"  Found {len(races)} completed race(s)")
    return races

# ── Step 2: Parse winner + off-time from a race result page ────────────────────
def parse_race_result(race_url):
    """Return (off_time_HHMM, winner_name) or (None, None)."""
    html = fetch(race_url)
    if not html:
        return None, None

    # Off time
    off_m = re.search(r'Off time:\s*(\d{1,2}:\d{2})', html)
    off_time = off_m.group(1).zfill(5) if off_m else None   # ensure HH:MM

    # ── Winner extraction strategies ──────────────────────────────────────────
    winner = None

    # 1) SL React component: first ResultRunner__StyledHorseName is the winner
    #    (results listed in finishing order; class hash changes but base name is stable)
    m = re.search(
        r'ResultRunner__StyledHorseName[^"]*"[^>]*>'
        r'<a\s+href="/racing/profiles/horse/\d+"[^>]*>([^<]+)</a>',
        html
    )
    if m:
        winner = m.group(1).strip()

    # 2) Fallback: any horse profile link near a "1" position indicator
    if not winner:
        snippets = re.findall(
            r'(?:>1\s*</|position["\'][^>]*>1[^0-9<][^<]{0,100})'
            r'.{0,600}?/racing/profiles/horse/\d+"[^>]*>([^<]+)</a>',
            html, re.DOTALL
        )
        for s in snippets:
            candidate = s.strip()
            if len(candidate) > 2:
                winner = candidate
                break

    # 3) JSON-LD structured data
    if not winner:
        for block in re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
            try:
                data = json.loads(block)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    w = item.get('winner', {})
                    if isinstance(w, dict) and w.get('name'):
                        winner = w['name']
                        break
            except Exception:
                pass
            if winner:
                break

    # 4) og:description  "HorseName won the RaceName"
    if not winner:
        for attr in ('og:description', 'twitter:description'):
            for pattern in [
                r'<meta[^>]+(?:name|property)=["\']' + re.escape(attr) + r'["\'][^>]+content=["\']([^"\']*)["\']',
                r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:name|property)=["\']' + re.escape(attr) + r'["\']',
            ]:
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    wm = re.match(r'^([A-Z][^\.]+?)\s+won\b', m.group(1))
                    if wm:
                        winner = wm.group(1).strip()
                        break
            if winner:
                break

    return off_time, winner

# ── Step 3: Match race results against pending DynamoDB picks ──────────────────
def update_results(date_str):
    db = boto3.resource('dynamodb', region_name='eu-west-1')
    t = db.Table('SureBetBets')

    # Get all UI picks for the date
    resp = t.query(
        KeyConditionExpression=Key('bet_date').eq(date_str),
        FilterExpression=Attr('show_in_ui').eq(True)
    )
    picks = resp['Items']
    pending = [p for p in picks if not p.get('outcome')]
    if not pending:
        print(f"\nNo pending picks for {date_str}")
        return

    print(f"\n{len(pending)} pending pick(s) to resolve:")
    for p in pending:
        horse = p.get('horse') or p.get('horse_name', '?')
        rt = p.get('race_time', '')[:16].replace('T', ' ')
        print(f"  - {horse} @ {p.get('course','?')} {rt}")

    # Build lookup: course_name_lower → list of (off_time_minutes, winner)
    # We match against DB pick time with ±15 min window
    race_results = {}   # course_lower → list[(minutes_since_midnight, winner)]
    races = get_race_urls(date_str)
    print(f"\nFetching individual race pages...")
    for course_slug, course_name, race_id, race_url in races:
        off_time, winner = parse_race_result(race_url)
        if off_time and winner:
            h, mn = map(int, off_time.split(':'))
            mins = h * 60 + mn
            key = course_name.lower()
            if key not in race_results:
                race_results[key] = []
            race_results[key].append((mins, winner, off_time))
            print(f"  {course_name} {off_time}  →  WINNER: {winner}")

    def find_winner(course: str, hhmm: str, window_min=15):
        """Find winner by course + approximate time."""
        h, mn = map(int, hhmm.split(':'))
        target = h * 60 + mn
        course_key = course.lower()
        candidates = race_results.get(course_key, [])
        for mins, winner, off_time in candidates:
            if abs(mins - target) <= window_min:
                return winner, off_time
        return None, None

    # Match and update
    print(f"\n{'='*55}")
    updated = 0
    _extra_dates_fetched = set()  # track cross-date SL index fetches
    for pick in pending:
        horse = pick.get('horse') or pick.get('horse_name', '')
        course = pick.get('course', '').strip()
        race_time_raw = pick.get('race_time', '')   # ISO e.g. "2026-03-20T15:22:00.000Z"
        bet_id = pick['bet_id']
        odds = float(pick.get('odds', 0))
        stake = float(pick.get('bet_amount', 6))

        # Extract date and HH:MM from race_time (may differ from bet_date for cross-day picks)
        tm_m = re.search(r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})', race_time_raw)
        if not tm_m:
            print(f"  [SKIP] {horse} – can't parse time from {race_time_raw}")
            continue
        race_date, race_hhmm = tm_m.group(1), tm_m.group(2)

        # If race ran on a different date, we need that date's SL index
        if race_date != date_str and race_date not in _extra_dates_fetched:
            _extra_dates_fetched.add(race_date)
            print(f"\n  [Cross-date] Fetching {race_date} results for {horse}...")
            extra_races = get_race_urls(race_date)
            for cs, cn, rid, rurl in extra_races:
                ot, w = parse_race_result(rurl)
                if ot and w:
                    h2, mn2 = map(int, ot.split(':'))
                    mins2 = h2 * 60 + mn2
                    key2 = cn.lower()
                    if key2 not in race_results:
                        race_results[key2] = []
                    # Avoid duplicates
                    if not any(abs(m3 - mins2) < 1 for m3, _, _ in race_results[key2]):
                        race_results[key2].append((mins2, w, ot))
                        print(f"    {cn} {ot}  →  {w}")

        winner, actual_off = find_winner(course, race_hhmm)

        if not winner:
            print(f"  [SKIP] {horse} @ {course} {race_hhmm} – no result found")
            continue

        won = norm(horse) == norm(winner)
        outcome = 'WON' if won else 'LOST'
        profit = round((odds - 1) * stake, 2) if won else -round(stake, 2)

        print(f"  {'✅ WIN ' if won else '❌ LOSS'} | {horse:<30} | Winner: {winner:<25} | P&L: {profit:+.2f}")

        t.update_item(
            Key={'bet_date': date_str, 'bet_id': bet_id},
            UpdateExpression='SET outcome = :o, profit = :p, actual_result = :r, winner_name = :w',
            ExpressionAttributeValues={
                ':o': outcome,
                ':p': Decimal(str(profit)),
                ':r': outcome,
                ':w': winner,
            }
        )
        updated += 1

    print(f"\nUpdated {updated}/{len(pending)} pending picks")

    # Final summary
    resp2 = t.query(
        KeyConditionExpression=Key('bet_date').eq(date_str),
        FilterExpression=Attr('show_in_ui').eq(True)
    )
    all_picks = resp2['Items']
    wins = sum(1 for p in all_picks if p.get('outcome') == 'WON')
    losses = sum(1 for p in all_picks if p.get('outcome') in ('LOST', 'LOSS'))
    pending_count = sum(1 for p in all_picks if not p.get('outcome'))
    total_pnl = sum(float(p.get('profit', 0)) for p in all_picks)

    print(f"\n{'='*55}")
    print(f"=== {date_str} RESULTS SUMMARY ===")
    print(f"W:{wins}  L:{losses}  Pending:{pending_count}  |  P&L: {total_pnl:+.2f}")
    for p in sorted(all_picks, key=lambda x: x.get('race_time', '')):
        horse = p.get('horse') or p.get('horse_name', '?')
        outcome = p.get('outcome', 'PEND')
        pnl = float(p.get('profit', 0))
        course = p.get('course', '?')
        rt = str(p.get('race_time', ''))[:16]
        print(f"  {outcome:<5} | {horse:<30} | {course:<15} | {rt} | {pnl:+.2f}")


if __name__ == '__main__':
    print(f"\n{'='*55}")
    print(f" Sporting Life Results Fetcher — {TARGET_DATE}")
    print(f"{'='*55}")
    update_results(TARGET_DATE)
