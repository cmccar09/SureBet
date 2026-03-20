"""
FORM ENRICHER — Fetches detailed last-6-race history from Racing Post for each runner.

Data per run:
  date         : "2026-01-17"
  course       : "Ascot"
  distance_f   : 18.5        # furlongs (e.g. 2m3f≈18.5f)
  going        : "Sft"       # abbreviated going string
  position     : 1
  field_size   : 10
  official_rating: 124       # OR on that day (None if N/A)
  race_class   : "Grd1"      # race class string from RP

New scoring power these unlock:
  - exact_course_win       +20pts  (won here before → C marker confirmed)
  - exact_distance_win     +20pts  (won within 0.5f of today → D marker confirmed)
  - going_win_match        +16pts  (won on same going type as today)
  - fresh_days_optimal     +10pts  (14-35 days since last run)
  - close_2nd_last_time    +14pts  (beaten < 4 lengths when 2nd last time)
  - or_trajectory_up       +10pts  (rising OR over last 3 runs)
  - big_field_win          +8pts   (won in field of 10+)

Usage:
  from form_enricher import enrich_runners, get_form_signals

  # Before running comprehensive_workflow:
  enriched_races = enrich_runners(races)   # adds 'form_runs' to each runner
  # analyze_horse_comprehensive picks up form_runs from horse_data automatically
"""

import json
import re
import time
import os
import hashlib
from datetime import datetime, timedelta

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.parse
    _HAS_REQUESTS = False

# ---------------------------------------------------------------------------
# Cache file — avoids re-scraping the same horses on every refresh
# ---------------------------------------------------------------------------
CACHE_FILE = 'form_cache.json'
CACHE_TTL_HOURS = 12   # refresh form data after 12 hours

_cache = {}   # in-memory; loaded from file at module import


def _load_cache():
    global _cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}


def _save_cache():
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(_cache, f, indent=2)
    except Exception:
        pass


_load_cache()


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
_RP_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.racingpost.com/',
    'DNT': '1',
    'Connection': 'keep-alive',
}

_SL_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.9',
    'Referer': 'https://www.sportinglife.com/',
    'DNT': '1',
}


def _http_get(url, headers, timeout=15):
    """Minimal HTTP GET — works with or without `requests` package."""
    if _HAS_REQUESTS:
        try:
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return None
    else:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read().decode('utf-8', errors='replace')
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Horse name → slug conversions
# ---------------------------------------------------------------------------
def _rp_slug(name: str) -> str:
    """Convert horse name to Racing Post URL slug."""
    s = name.lower()
    s = re.sub(r"'", '', s)          # remove apostrophes
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', '-', s.strip())
    return s


def _sl_slug(name: str) -> str:
    """Convert horse name to Sporting Life URL slug."""
    return _rp_slug(name)            # same pattern


# ---------------------------------------------------------------------------
# Racing Post parser
# ---------------------------------------------------------------------------

# Going abbreviation normaliser — maps RP short codes to standard terms
_GOING_NORM = {
    'HY': 'Heavy', 'Hy': 'Heavy', 'HVY': 'Heavy',
    'SF': 'Soft', 'Sft': 'Soft', 'Soft': 'Soft', 'GS': 'Good to Soft',
    'GF': 'Good to Firm', 'GD': 'Good', 'G': 'Good', 'Gd': 'Good',
    'F': 'Firm', 'Fm': 'Firm', 'Firm': 'Firm',
    'SD': 'Slow', 'STD': 'Standard', 'Standard': 'Standard', 'AW': 'Standard',
}


def _norm_going(g: str) -> str:
    return _GOING_NORM.get(g, g)


# Distance string → furlongs
def _dist_to_furlongs(dist_str: str) -> float | None:
    """
    Convert distance strings like '2m3f 63yds', '1m7f 50yds', '2m4f' → furlongs.
    1 mile = 8 furlongs, 1 furlong = 220 yards → 63yds ≈ 0.29f
    """
    if not dist_str:
        return None
    dist_str = str(dist_str).strip().lower()
    total_f = 0.0
    # miles
    m = re.search(r'(\d+)m', dist_str)
    if m:
        total_f += int(m.group(1)) * 8
    # furlongs
    f = re.search(r'(\d+)f', dist_str)
    if f:
        total_f += int(f.group(1))
    # yards
    y = re.search(r'(\d+)y(?:ds?)?', dist_str)
    if y:
        total_f += int(y.group(1)) / 220
    return round(total_f, 2) if total_f > 0 else None


# Course abbreviation → full name (RP uses short codes in form table)
_COURSE_MAP = {
    'Asc': 'Ascot', 'Chp': 'Chepstow', 'Her': 'Hereford', 'Wnc': 'Wincanton',
    'Str': 'Stratford', 'Utt': 'Uttoxeter', 'Ch': 'Cheltenham', 'Chf': 'Cheltenham',
    'Nby': 'Newbury', 'Snd': 'Sandown', 'Kmp': 'Kempton', 'Wlv': 'Wolverhampton',
    'Lyn': 'Lingfield', 'Ntn': 'Newmarket', 'Yar': 'Yarmouth', 'Lat': 'Catterick',
    'CF': 'Carlisle', 'Car': 'Carlisle', 'Hay': 'Haydock', 'Wet': 'Wetherby',
    'Hun': 'Huntingdon', 'MR': 'Market Rasen', 'MktR': 'Market Rasen',
    'Exe': 'Exeter', 'Plm': 'Plymouth', 'Tnt': 'Taunton', 'Fau': 'Fakenham',
    'Ban': 'Bangor', 'Bng': 'Bangor', 'Lud': 'Ludlow', 'Wrc': 'Worcester',
    'Pon': 'Pontefract', 'Red': 'Redcar', 'Bhm': 'Birmingham', 'Ayr': 'Ayr',
    'Ham': 'Hamilton', 'Mss': 'Musselburgh', 'Edi': 'Edinburgh', 'Per': 'Perth',
    'Nav': 'Navan', 'Leo': 'Leopardstown', 'Pun': 'Punchestown', 'Frf': 'Fairyhouse',
    'Gwy': 'Galway', 'Bal': 'Ballinrobe', 'Clo': 'Clonmel', 'Gol': 'Gowran',
    'Lip': 'Listowel', 'Kil': 'Killarney', 'Naa': 'Naas', 'Cur': 'Curragh',
}


def _expand_course(abbr: str) -> str:
    return _COURSE_MAP.get(abbr, abbr)


# ---------------------------------------------------------------------------
# Scrape Racing Post horse form page
# ---------------------------------------------------------------------------

def _fetch_rp_form(horse_name: str, max_runs: int = 6) -> list[dict]:
    """
    Attempt to scrape the Racing Post form page for a horse.
    Returns list of run dicts (most recent first).
    Returns [] on failure.
    """
    slug = _rp_slug(horse_name)
    url = f"https://www.racingpost.com/horses/{slug}/form"
    html = _http_get(url, _RP_HEADERS, timeout=15)
    if not html:
        return []

    runs = []

    # RP form tables have class="rp-table" or data rows.
    # Look for the <table> that contains form history rows.
    # Each row looks like:
    #   <td class="rp-horseTable__raceDate">17 Jan 26</td>
    #   <td class="rp-horseTable__raceCourse">Ascot</td>
    #   <td>2m3f 63yds</td>   <!-- distance -->
    #   <td>Sft</td>          <!-- going -->
    #   <td class="rp-horseTable__horsePos"><span>1</span>/10</td>
    #   <td>124</td>          <!-- OR -->
    # The exact selectors vary; we fall back to regex patterns.

    # Pattern approach 1: JSON-LD / inline JSON embedded in page
    json_match = re.search(r'"horseFormResults"\s*:\s*(\[.*?\])', html, re.DOTALL)
    if json_match:
        try:
            runs_raw = json.loads(json_match.group(1))
            for r in runs_raw[:max_runs]:
                run = {
                    'date': r.get('date', ''),
                    'course': r.get('courseName', r.get('course', '')),
                    'distance_f': _dist_to_furlongs(r.get('distanceFurlongs', r.get('distance', ''))),
                    'going': _norm_going(r.get('going', '')),
                    'position': _safe_int(r.get('position', r.get('finishingPosition', ''))),
                    'field_size': _safe_int(r.get('numberOfRunners', r.get('fieldSize', ''))),
                    'official_rating': _safe_int(r.get('officialRating', r.get('or', ''))),
                    'race_class': r.get('raceClass', r.get('class', '')),
                    'beaten_lengths': _safe_float(r.get('beatenLengths', '')),
                }
                runs.append(run)
            if runs:
                return runs
        except Exception:
            pass

    # Pattern approach 2: Parse HTML table rows
    # Match rows from the form table — look for date + course + position pattern
    row_pattern = re.compile(
        r'(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{2})'    # date like "17 Jan 26"
        r'.*?'
        r'([A-Z][a-z]{2,4})\s+'                   # course abbr like "Asc"
        r'(\d+m\d*f?\s*\d*y?d?s?)'                # distance like "2m3f 63yds"
        r'\s*'
        r'([A-Za-z]{1,6})\s+'                      # going like "Sft"
        r'Hdl|Chase|Hrd|Flt'                        # race type (discard)
        r'.*?'
        r'(\d{1,2})/(\d{1,2})',                    # pos/field like "1/10"
        re.DOTALL,
    )

    for m in list(row_pattern.finditer(html))[:max_runs]:
        date_raw = m.group(1)
        course_raw = m.group(2)
        dist_raw = m.group(3)
        going_raw = m.group(4)
        pos = _safe_int(m.group(5))
        field = _safe_int(m.group(6))
        try:
            date_str = datetime.strptime(date_raw.strip(), '%d %b %y').strftime('%Y-%m-%d')
        except Exception:
            date_str = date_raw.strip()
        runs.append({
            'date': date_str,
            'course': _expand_course(course_raw),
            'distance_f': _dist_to_furlongs(dist_raw),
            'going': _norm_going(going_raw),
            'position': pos,
            'field_size': field,
            'official_rating': None,
            'race_class': '',
            'beaten_lengths': None,
        })

    return runs[:max_runs]


# ---------------------------------------------------------------------------
# Sporting Life fallback parser
# ---------------------------------------------------------------------------

def _fetch_sl_form(horse_name: str, max_runs: int = 6) -> list[dict]:
    """
    Try Sporting Life horse form as fallback.
    URL: https://www.sportinglife.com/racing/horses/{slug}/form
    """
    slug = _sl_slug(horse_name)
    url = f"https://www.sportinglife.com/racing/horses/{slug}/form"
    html = _http_get(url, _SL_HEADERS, timeout=15)
    if not html:
        return []

    runs = []

    # SL embeds a window.__PRELOADED_STATE__ JSON blob - very reliable
    json_match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});\s*</script>', html, re.DOTALL)
    if json_match:
        try:
            state = json.loads(json_match.group(1))
            # Navigate to form results — path varies; search recursively
            form_data = _deep_find(state, 'formResults') or _deep_find(state, 'raceHistory') or []
            for r in form_data[:max_runs]:
                run = {
                    'date': _extract_date(r),
                    'course': r.get('courseName', r.get('venue', '')),
                    'distance_f': _dist_to_furlongs(r.get('distance', '')),
                    'going': _norm_going(r.get('going', '')),
                    'position': _safe_int(r.get('position', r.get('finishingPosition', ''))),
                    'field_size': _safe_int(r.get('runners', r.get('fieldSize', ''))),
                    'official_rating': _safe_int(r.get('officialRating', r.get('or', ''))),
                    'race_class': r.get('class', r.get('raceClass', '')),
                    'beaten_lengths': _safe_float(r.get('beatenLengths', '')),
                }
                if run['date']:
                    runs.append(run)
            if runs:
                return runs
        except Exception:
            pass

    return []


# ---------------------------------------------------------------------------
# Parse Paddy Power-style form text (fallback if HTML is provided as text)
# ---------------------------------------------------------------------------

def parse_pp_form_text(text: str) -> list[dict]:
    """
    Parse the tabular form section from Paddy Power / similar text:
        17 Jan 26  Ascot  Asc 2m3f 63yds Sft Hdl  1/10  124
    Returns list of run dicts.
    """
    runs = []
    # Match date + course + details line
    row_re = re.compile(
        r'(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{2})\s+'                    # date
        r'(.+?)\s+'                                                    # full course name
        r'[A-Z][a-z]{2,4}\s+'                                         # course abbr
        r'(\d+m\d*f?\s*\d*y?d?s?)\s+'                                # distance
        r'([A-Za-z]{1,6})\s+'                                         # going
        r'(?:Hdl|Chase|Hrd|Flt|Nov|Hcp)\s*'                          # race type
        r'(\d{1,2})/(\d{1,2})\s*'                                    # pos/field
        r'(\d+|N/A)?',                                                # OR
    )
    for m in row_re.finditer(text):
        date_raw = m.group(1).strip()
        course = m.group(2).strip()
        dist_raw = m.group(3).strip()
        going_raw = m.group(4).strip()
        pos = _safe_int(m.group(5))
        field = _safe_int(m.group(6))
        or_raw = m.group(7) or ''
        try:
            date_str = datetime.strptime(date_raw, '%d %b %y').strftime('%Y-%m-%d')
        except Exception:
            date_str = date_raw
        runs.append({
            'date': date_str,
            'course': course,
            'distance_f': _dist_to_furlongs(dist_raw),
            'going': _norm_going(going_raw),
            'position': pos,
            'field_size': field,
            'official_rating': _safe_int(or_raw) if or_raw != 'N/A' else None,
            'race_class': '',
            'beaten_lengths': None,
        })
    return runs


# ---------------------------------------------------------------------------
# Main public entry points
# ---------------------------------------------------------------------------

def fetch_form(horse_name: str, max_runs: int = 6, force_refresh: bool = False) -> list[dict]:
    """
    Return last `max_runs` race history for a horse.
    Uses cache (12h TTL) to avoid hammering scraped sites.
    """
    cache_key = horse_name.lower().strip()
    now = datetime.utcnow()

    if not force_refresh and cache_key in _cache:
        entry = _cache[cache_key]
        cached_at = datetime.fromisoformat(entry.get('cached_at', '2000-01-01'))
        age_h = (now - cached_at).total_seconds() / 3600
        if age_h < CACHE_TTL_HOURS:
            return entry.get('runs', [])

    # Try Racing Post first, Sporting Life as fallback
    runs = _fetch_rp_form(horse_name, max_runs)
    time.sleep(0.8)   # polite delay

    if not runs:
        runs = _fetch_sl_form(horse_name, max_runs)
        if runs:
            time.sleep(0.6)

    _cache[cache_key] = {
        'runs': runs,
        'cached_at': now.isoformat(),
        'source': 'rp' if runs else 'none',
    }
    _save_cache()
    return runs


def enrich_runners(races: list[dict], verbose: bool = True) -> list[dict]:
    """
    Add 'form_runs' list to every runner in every race.
    Mutates races in-place and also returns them.
    """
    total_horses = sum(len(r.get('runners', [])) for r in races)
    done = 0
    for race in races:
        for runner in race.get('runners', []):
            name = runner.get('name', '')
            if name:
                runs = fetch_form(name)
                runner['form_runs'] = runs
                done += 1
                if verbose:
                    status = f"✓ {len(runs)} runs" if runs else "✗ no data"
                    print(f"  [{done}/{total_horses}] {name}: {status}")
    return races


# ---------------------------------------------------------------------------
# Scoring signals derived from form_runs
# ---------------------------------------------------------------------------

def get_form_signals(horse_data: dict, today_course: str, today_distance_f: float | None,
                      today_going: str) -> dict:
    """
    Compute new scoring signals from the horse's detailed form history.

    Returns dict of signal values:
        exact_course_win      bool
        exact_distance_win    bool
        going_win_match       bool
        going_place_match     bool
        days_since_last_run   int | None
        fresh_days_optimal    bool    — 14-35 days = optimal freshness window
        close_2nd_last_time   bool    — 2nd with beaten_lengths < 4
        or_trajectory_up      bool    — OR rising over last 3 runs
        big_field_win         bool    — won in field of 10+
        going_win_count       int     — # wins on similar going
        course_run_count      int     — # starts at this course
        course_win_count      int     — # wins at this course
        distance_win_count    int     — # wins within 0.5f of today
    """
    runs = horse_data.get('form_runs', [])
    signals = {
        'exact_course_win': False,
        'exact_distance_win': False,
        'going_win_match': False,
        'going_place_match': False,
        'days_since_last_run': None,
        'fresh_days_optimal': False,
        'close_2nd_last_time': False,
        'or_trajectory_up': False,
        'big_field_win': False,
        'going_win_count': 0,
        'course_run_count': 0,
        'course_win_count': 0,
        'distance_win_count': 0,
    }

    if not runs:
        return signals

    today_going_type = _going_type(today_going)

    for i, run in enumerate(runs):
        pos = run.get('position')
        course = str(run.get('course', '')).lower()
        dist_f = run.get('distance_f')
        going = run.get('going', '')
        going_type = _going_type(going)
        field = run.get('field_size') or 0
        beaten = run.get('beaten_lengths')

        # Days since last run
        if i == 0 and run.get('date'):
            try:
                last_date = datetime.strptime(run['date'], '%Y-%m-%d')
                days = (datetime.now() - last_date).days
                signals['days_since_last_run'] = days
                signals['fresh_days_optimal'] = 14 <= days <= 35
            except Exception:
                pass

        # Close 2nd last time
        if i == 0 and pos == 2 and beaten is not None and beaten < 4:
            signals['close_2nd_last_time'] = True

        # Course records
        today_course_norm = today_course.lower().strip()
        course_norm = course.strip()
        if today_course_norm and (today_course_norm in course_norm or course_norm in today_course_norm):
            signals['course_run_count'] += 1
            if pos == 1:
                signals['exact_course_win'] = True
                signals['course_win_count'] += 1

        # Distance records (±0.5 furlongs tolerance)
        if today_distance_f and dist_f:
            if abs(today_distance_f - dist_f) <= 0.5:
                signals['distance_win_count'] += (1 if pos == 1 else 0)
                if pos == 1:
                    signals['exact_distance_win'] = True

        # Going records
        if going_type == today_going_type:
            if pos == 1:
                signals['going_win_count'] += 1
                signals['going_win_match'] = True
            elif pos in (2, 3):
                signals['going_place_match'] = True

        # Big field win
        if pos == 1 and field >= 10:
            signals['big_field_win'] = True

    # OR trajectory — check last 3 runs with valid OR
    valid_ors = [(r.get('official_rating') or 0) for r in runs[:3] if r.get('official_rating')]
    if len(valid_ors) >= 2:
        signals['or_trajectory_up'] = valid_ors[0] > valid_ors[-1]   # most recent > oldest

    return signals


def _going_type(going: str) -> str:
    """Bucket going into broad categories for matching."""
    g = str(going).lower()
    if 'heavy' in g:
        return 'heavy'
    if 'soft' in g:
        return 'soft'
    if 'good to soft' in g or 'gs' in g:
        return 'gd_soft'
    if 'good to firm' in g or 'gf' in g:
        return 'gd_firm'
    if 'good' in g:
        return 'good'
    if 'firm' in g:
        return 'firm'
    if 'standard' in g or 'aw' in g or 'all' in g:
        return 'aw'
    return 'unknown'


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _safe_int(v) -> int | None:
    try:
        return int(str(v).strip())
    except Exception:
        return None


def _safe_float(v) -> float | None:
    try:
        return float(str(v).strip())
    except Exception:
        return None


def _extract_date(d: dict) -> str:
    for k in ('date', 'raceDate', 'race_date', 'dateTime', 'startTime'):
        v = d.get(k)
        if v:
            try:
                return datetime.fromisoformat(str(v)[:10]).strftime('%Y-%m-%d')
            except Exception:
                return str(v)[:10]
    return ''


def _deep_find(obj, key: str):
    """Recursively search a dict/list for a given key."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _deep_find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = _deep_find(item, key)
            if r is not None:
                return r
    return None


# ---------------------------------------------------------------------------
# Quick CLI test
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    horse = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'Came From Nowhere'
    print(f"\nFetching form for: {horse}")
    runs = fetch_form(horse, force_refresh=True)
    if runs:
        print(f"Found {len(runs)} runs:")
        for r in runs:
            print(f"  {r['date']} | {r['course']} | {r['distance_f']}f | {r['going']} | "
                  f"{r['position']}/{r['field_size']} | OR={r['official_rating']}")
    else:
        print("No form data retrieved (RP may have blocked — normal, still works via cache/fallback)")
    sigs = get_form_signals({'form_runs': runs}, 'Newbury', 18.5, 'Soft')
    print(f"\nSignals: {json.dumps(sigs, indent=2)}")
