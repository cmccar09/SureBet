"""
BARRY'S CHELTENHAM 2026 — DAILY HTML REGENERATOR
=================================================
Pulls latest picks from CheltenhamPicks DynamoDB, applies MacFitz override
logic from macfitz_overrides.json, flags new close calls, and writes
barrys_cheltenham_2026.html.

Schedule: runs automatically inside daily_automated_workflow.py during the
Cheltenham window (05–13 Mar 2026).

Usage:
    python barrys/update_barrys_html.py               # full update
    python barrys/update_barrys_html.py --dry-run      # print diff, no write
    python barrys/update_barrys_html.py --check-splits # show close-call report only
"""

import sys, os, json, re, pathlib, argparse
from datetime import datetime
from decimal import Decimal

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent   # Betting/
sys.path.insert(0, str(ROOT))
import boto3

# ── file paths ────────────────────────────────────────────────────────────────
HERE            = pathlib.Path(__file__).resolve().parent
OVERRIDES_FILE  = HERE / "macfitz_overrides.json"
HTML_OUT        = HERE / "barrys_cheltenham_2026.html"
PICKS_TABLE     = "CheltenhamPicks"
REGION          = "eu-west-1"

# ── race catalogue (defines display order + metadata) ─────────────────────────
# Each entry: (day_num, time, db_name, display_name, grade_css, grade_label, day_label, day_date)
RACES = [
    # Day 1
    (1, "13:20", "Sky Bet Supreme Novices Hurdle",       "Sky Bet Supreme Novices Hurdle",   "g1",   "G1",     "Champion Day",          "Tuesday 10 March 2026"),
    (1, "14:00", "Arkle Challenge Trophy Chase",         "Arkle Challenge Trophy Chase",     "g1",   "G1",     "Champion Day",          "Tuesday 10 March 2026"),
    (1, "14:40", "Ultima Handicap Chase",                "Ultima Handicap Chase",            "hcap", "Hcap",   "Champion Day",          "Tuesday 10 March 2026"),
    (1, "15:20", "Unibet Champion Hurdle",               "Unibet Champion Hurdle",           "g1",   "G1",     "Champion Day",          "Tuesday 10 March 2026"),
    (1, "16:00", "Mares Hurdle",                         "Mares Hurdle",                     "g1",   "G1",     "Champion Day",          "Tuesday 10 March 2026"),
    (1, "16:40", "National Hunt Chase",                  "National Hunt Chase",              "g2",   "G2",     "Champion Day",          "Tuesday 10 March 2026"),
    (1, "17:20", "Challenge Cup Chase",                  "Challenge Cup Chase",              "hcap", "Hcap",   "Champion Day",          "Tuesday 10 March 2026"),
    # Day 2
    (2, "13:20", "Ballymore Novices Hurdle",             "Ballymore Novices Hurdle",         "g1",   "G1",     "Ladies Day",            "Wednesday 11 March 2026"),
    (2, "14:00", "Brown Advisory Novices Chase",         "Brown Advisory Novices Chase",     "g1",   "G1",     "Ladies Day",            "Wednesday 11 March 2026"),
    (2, "14:40", "Coral Cup Handicap Hurdle",            "Coral Cup Handicap Hurdle",        "hcap", "Hcap",   "Ladies Day",            "Wednesday 11 March 2026"),
    (2, "15:20", "Queen Mother Champion Chase",          "Queen Mother Champion Chase",      "g1",   "G1",     "Ladies Day",            "Wednesday 11 March 2026"),
    (2, "16:00", "Glenfarclas Chase Cross Country",      "Glenfarclas Cross Country Chase",  "g2",   "G2",     "Ladies Day",            "Wednesday 11 March 2026"),
    (2, "16:40", "Dawn Run Mares Novices Hurdle",        "Dawn Run Mares Novices Hurdle",    "g2",   "G2",     "Ladies Day",            "Wednesday 11 March 2026"),
    (2, "17:20", "FBD Hotel & Resorts NH Flat Race",     "FBD Hotels NH Flat Race",          "flat", "Flat",   "Ladies Day",            "Wednesday 11 March 2026"),
    # Day 3
    (3, "13:20", "Turners Novices Chase",                "Turners Novices Chase",            "g1",   "G1",     "St Patrick's Thursday", "Thursday 12 March 2026"),
    (3, "14:00", "Pertemps Final Handicap Hurdle",       "Pertemps Final Handicap Hurdle",   "hcap", "Hcap",   "St Patrick's Thursday", "Thursday 12 March 2026"),
    (3, "14:40", "Ryanair Chase",                        "Ryanair Chase",                    "g1",   "G1",     "St Patrick's Thursday", "Thursday 12 March 2026"),
    (3, "15:20", "Paddy Power Stayers Hurdle",           "Paddy Power Stayers Hurdle",       "g1",   "G1",     "St Patrick's Thursday", "Thursday 12 March 2026"),
    (3, "16:00", "Plate Handicap Chase",                 "Plate Handicap Chase",             "hcap", "Hcap",   "St Patrick's Thursday", "Thursday 12 March 2026"),
    (3, "16:40", "Boodles Juvenile Handicap Hurdle",     "Boodles Juvenile Handicap Hurdle", "hcap", "Hcap",   "St Patrick's Thursday", "Thursday 12 March 2026"),
    (3, "17:20", "Martin Pipe Conditional Jockeys Hurdle", "Martin Pipe Conditional Jockeys","hcap", "Hcap",   "St Patrick's Thursday", "Thursday 12 March 2026"),
    # Day 4
    (4, "13:20", "JCB Triumph Hurdle",                   "JCB Triumph Hurdle",               "g1",   "G1",     "Gold Cup Day",          "Friday 13 March 2026"),
    (4, "14:00", "County Handicap Hurdle",               "County Handicap Hurdle",           "hcap", "Hcap",   "Gold Cup Day",          "Friday 13 March 2026"),
    (4, "14:40", "Albert Bartlett Novices Hurdle",       "Albert Bartlett Novices Hurdle",   "g1",   "G1",     "Gold Cup Day",          "Friday 13 March 2026"),
    (4, "15:20", "Cheltenham Gold Cup",                  "Cheltenham Gold Cup",              "g1",   "G1",     "Gold Cup Day",          "Friday 13 March 2026"),
    (4, "16:00", "Grand Annual Handicap Chase",          "Grand Annual Handicap Chase",      "hcap", "Hcap",   "Gold Cup Day",          "Friday 13 March 2026"),
    (4, "16:40", "Champion Standard Open NH Flat Race",  "Champion Open NH Flat Race",       "flat", "Flat",   "Gold Cup Day",          "Friday 13 March 2026"),
    (4, "17:20", "St James Place Foxhunter Chase",       "St James Place Foxhunter Chase",   "hunt", "Hunter", "Gold Cup Day",          "Friday 13 March 2026"),
]

# Known Cheltenham course winners (shown as notes in MacFitz entry)
COURSE_WINNERS = {
    "Kopek Des Bordes":   "Cheltenham course winner",
    "Lossiemouth":        "Cheltenham course winner",
    "Majborough":         "Cheltenham course winner",
    "Favori De Champdou": "Won 2024 Cross Country",
    "Fact To File":       "Won 2024 & 2025 Ryanair — reigning champion",
    "Gaelic Warrior":     "Cheltenham course winner",
    "Dinoblue":           "Won 2025 Mares Chase",
}

# ── tier cosmetics ─────────────────────────────────────────────────────────────
TIER_CSS = {
    "A+": ("elite",  "var(--gold)",   "A+ ELITE"),
    "A":  ("elite",  "var(--gold)",   "A ELITE"),
    "B":  ("strong", "var(--blue)",   "B EXCELLENT"),
    "C":  ("",       "var(--green)",  "C STRONG"),
    "D":  ("fair",   "var(--muted)",  "D FAIR"),
    "E":  ("fair",   "var(--muted)",  "E WEAK"),
}

def _tier_css(tier_str: str):
    """Map raw tier string from DB (e.g. 'A+ ELITE', 'B   EXCELLENT') → (css_class, color, label)."""
    t = tier_str.strip().upper()
    for key, val in TIER_CSS.items():
        if t.startswith(key):
            return val
    return ("", "var(--muted)", tier_str.strip())


# ── DynamoDB fetch ─────────────────────────────────────────────────────────────
def fetch_latest_picks() -> dict:
    """Return dict[race_name → latest item] from CheltenhamPicks."""
    dynamo = boto3.resource("dynamodb", region_name=REGION)
    table  = dynamo.Table(PICKS_TABLE)
    resp   = table.scan()
    items  = resp["Items"]
    while "LastEvaluatedKey" in resp:
        resp  = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items += resp["Items"]

    latest = {}
    for item in items:
        rn = item.get("race_name", "?")
        ua = item.get("updated_at", "")
        if rn not in latest or ua > latest[rn].get("updated_at", ""):
            latest[rn] = item
    return latest


# ── MacFitz override logic ─────────────────────────────────────────────────────
def load_overrides() -> dict:
    if OVERRIDES_FILE.exists():
        return json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return {"overrides": {}}


def apply_macfitz(pick: dict, overrides: dict) -> dict:
    """
    Given a CheltenhamPicks item, return a MacFitz pick dict:
      { horse, score, is_split, override_reason, new_close_call }
    """
    surebet_horse = pick.get("horse", "?")
    score         = int(pick.get("score", 0) or 0)
    second_horse  = pick.get("second_horse_name", "")
    second_score  = int(pick.get("second_score", 0) or 0)
    gap           = int(pick.get("score_gap", score - second_score) or (score - second_score))
    race_name     = pick.get("race_name", "")

    # Check for a manual override
    ovr = overrides.get("overrides", {}).get(race_name)
    if ovr and ovr.get("active", True):
        # Validate the override horse is still in the field (score > 0)
        # If scores have changed significantly, warn but still apply
        return {
            "horse":          ovr["macfitz_horse"],
            "score":          ovr.get("macfitz_score", second_score),
            "is_split":       True,
            "override_reason": ovr["reason"],
            "new_close_call": False,
            "gap":            gap,
            "surebet_horse":  surebet_horse,
            "surebet_score":  score,
        }

    # Auto-detect dead ties not yet in overrides
    threshold = overrides.get("_auto_split_threshold", 3)
    new_close = (gap <= threshold and second_horse)

    return {
        "horse":          surebet_horse,
        "score":          score,
        "is_split":       False,
        "override_reason": None,
        "new_close_call": new_close,
        "gap":            gap,
        "surebet_horse":  surebet_horse,
        "surebet_score":  score,
    }


# ── HTML generation ────────────────────────────────────────────────────────────
CSS = r"""
  :root {
    --bg:#0d1117;--surface:#161b22;--border:#30363d;--gold:#c9a84c;--gold2:#e8c96d;
    --green:#3fb950;--blue:#58a6ff;--purple:#bc8cff;--red:#f85149;--orange:#d29922;
    --muted:#8b949e;--text:#e6edf3;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;line-height:1.5;}
  .masthead{background:linear-gradient(135deg,#1a1200 0%,#2a1f00 40%,#1a1200 100%);border-bottom:2px solid var(--gold);padding:28px 32px;text-align:center;}
  .masthead::before{content:"🏆";font-size:48px;display:block;margin-bottom:8px;}
  .masthead h1{font-size:2.2rem;color:var(--gold2);letter-spacing:2px;text-transform:uppercase;text-shadow:0 0 20px rgba(201,168,76,.5);}
  .masthead .subtitle{font-size:1rem;color:var(--muted);margin-top:6px;letter-spacing:1px;}
  .prize-badge{display:inline-block;margin-top:14px;background:var(--gold);color:#0d1117;font-weight:700;font-size:1.2rem;padding:6px 22px;border-radius:20px;letter-spacing:1px;}
  .updated-tag{display:inline-block;margin-top:10px;margin-left:12px;background:rgba(63,185,80,.2);border:1px solid var(--green);color:var(--green);font-size:.8rem;font-weight:600;padding:4px 14px;border-radius:20px;}
  .rules-bar{display:flex;justify-content:center;gap:24px;padding:14px 32px;background:var(--surface);border-bottom:1px solid var(--border);flex-wrap:wrap;}
  .score-pill{display:flex;align-items:center;gap:8px;padding:5px 16px;border-radius:6px;font-weight:600;font-size:.9rem;}
  .score-pill.win  {background:rgba(63,185,80,.15);border:1px solid var(--green);color:var(--green);}
  .score-pill.place{background:rgba(88,166,255,.15);border:1px solid var(--blue);color:var(--blue);}
  .score-pill.show {background:rgba(201,168,76,.15);border:1px solid var(--gold);color:var(--gold);}
  .score-pill.zero {background:rgba(139,148,158,.1);border:1px solid var(--muted);color:var(--muted);}
  .strategy-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:20px 32px;max-width:1100px;margin:0 auto;}
  .strategy-card{padding:18px 22px;border-radius:10px;border:1px solid var(--border);}
  .strategy-card.surebet {background:linear-gradient(135deg,#0d1117 0%,#0a1a2a 100%);border-left:4px solid var(--blue);}
  .strategy-card.macfitz {background:linear-gradient(135deg,#0d1117 0%,#1a0d0a 100%);border-left:4px solid var(--orange);}
  .strategy-card h3{font-size:1.1rem;margin-bottom:6px;}
  .strategy-card.surebet h3{color:var(--blue);}
  .strategy-card.macfitz h3{color:var(--orange);}
  .strategy-card p{color:var(--muted);font-size:.88rem;line-height:1.6;}
  .notice-wrapper{max-width:1100px;margin:0 auto 0;padding:0 32px 16px;}
  .notice-box{background:rgba(63,185,80,.08);border:1px solid rgba(63,185,80,.4);border-radius:8px;padding:12px 18px;font-size:.88rem;color:var(--green);}
  .notice-box.has-splits{background:rgba(210,153,34,.08);border-color:rgba(210,153,34,.4);color:var(--text);}
  .content{max-width:1200px;margin:0 auto;padding:0 24px 40px;}
  .day-section{margin-bottom:32px;}
  .day-header{display:flex;align-items:center;gap:16px;padding:14px 20px;background:linear-gradient(90deg,#1a1200 0%,#161b22 100%);border-radius:10px 10px 0 0;border:1px solid var(--gold);border-bottom:none;}
  .day-number{background:var(--gold);color:#0d1117;font-weight:800;font-size:.85rem;padding:4px 10px;border-radius:4px;letter-spacing:1px;}
  .day-title{font-size:1.15rem;font-weight:700;color:var(--gold2);}
  .day-date{font-size:.85rem;color:var(--muted);margin-left:auto;}
  .picks-table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--border);border-radius:0 0 10px 10px;overflow:hidden;}
  .picks-table thead tr{background:#1c2128;}
  .picks-table th{padding:10px 14px;text-align:left;font-size:.78rem;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);border-bottom:1px solid var(--border);white-space:nowrap;}
  .picks-table td{padding:12px 14px;border-bottom:1px solid rgba(48,54,61,.6);vertical-align:middle;}
  .picks-table tr:last-child td{border-bottom:none;}
  .picks-table tr:hover td{background:rgba(255,255,255,.02);}
  .picks-table tr.banker-row td{background:rgba(63,185,80,.04);}
  .picks-table tr.split-row td{background:rgba(210,153,34,.04);}
  .time-cell{color:var(--gold);font-weight:600;font-size:.85rem;white-space:nowrap;}
  .grade-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.75rem;font-weight:700;letter-spacing:.5px;white-space:nowrap;}
  .g1  {background:rgba(201,168,76,.2); color:var(--gold2); border:1px solid rgba(201,168,76,.4);}
  .g2  {background:rgba(88,166,255,.15);color:var(--blue);  border:1px solid rgba(88,166,255,.3);}
  .hcap{background:rgba(188,140,255,.15);color:var(--purple);border:1px solid rgba(188,140,255,.3);}
  .flat{background:rgba(63,185,80,.15); color:var(--green); border:1px solid rgba(63,185,80,.3);}
  .hunt{background:rgba(139,148,158,.15);color:var(--muted); border:1px solid rgba(139,148,158,.3);}
  .race-name{font-weight:600;color:var(--text);}
  .horse-pick{font-weight:700;font-size:.95rem;color:var(--green);}
  .banker-tag{display:inline-block;margin-left:8px;background:rgba(63,185,80,.2);border:1px solid rgba(63,185,80,.5);color:var(--green);font-size:.7rem;font-weight:700;padding:1px 7px;border-radius:10px;letter-spacing:.5px;vertical-align:middle;}
  .split-tag{display:inline-block;margin-left:6px;background:rgba(210,153,34,.25);border:1px solid rgba(210,153,34,.6);color:var(--orange);font-size:.7rem;font-weight:700;padding:1px 7px;border-radius:10px;letter-spacing:.5px;vertical-align:middle;}
  .score-tag{display:inline-block;margin-left:8px;background:rgba(88,166,255,.1);border:1px solid rgba(88,166,255,.3);color:var(--blue);font-size:.7rem;font-weight:600;padding:1px 7px;border-radius:10px;vertical-align:middle;}
  .score-tag.elite{background:rgba(201,168,76,.15);border-color:rgba(201,168,76,.4);color:var(--gold);}
  .score-tag.strong{background:rgba(63,185,80,.12);border-color:rgba(63,185,80,.3);color:var(--green);}
  .score-tag.fair{background:rgba(139,148,158,.1);border-color:rgba(139,148,158,.3);color:var(--muted);}
  .both-agree{font-size:.75rem;color:var(--muted);margin-top:2px;}
  .summary-section{margin-bottom:32px;padding:24px;background:var(--surface);border:1px solid var(--border);border-radius:10px;}
  .summary-section h2{font-size:1.2rem;color:var(--gold2);border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:16px;}
  .summary-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;}
  .solo-list h3{font-size:1rem;padding:8px 14px;border-radius:6px;margin-bottom:10px;font-weight:700;letter-spacing:.5px;}
  .surebet-header {background:rgba(88,166,255,.15);color:var(--blue);  border-left:3px solid var(--blue);}
  .macfitz-header  {background:rgba(210,153,34,.15); color:var(--orange);border-left:3px solid var(--orange);}
  .pick-item{display:flex;align-items:flex-start;gap:10px;padding:7px 0;border-bottom:1px solid rgba(48,54,61,.5);}
  .pick-item:last-child{border-bottom:none;}
  .pick-num{font-size:.72rem;color:var(--muted);min-width:20px;text-align:right;padding-top:1px;}
  .pick-body{flex:1;}
  .day-divider{font-size:.72rem;color:var(--muted);padding:10px 0 8px;border-bottom:1px solid var(--border);margin:6px 0;}
  .footer{text-align:center;padding:20px;border-top:1px solid var(--border);color:var(--muted);font-size:.8rem;}
  @media(max-width:768px){.strategy-grid,.summary-grid{grid-template-columns:1fr;}}
"""


def _score_tag(score: int, css_class: str) -> str:
    cls = f'score-tag {css_class}'.strip()
    return f'<span class="{cls}">{score}</span>'


def _row_race(race, sb_pick, mf_pick, race_num: int) -> str:
    day, time, db_name, display_name, grade_css, grade_label, day_label, day_date = race
    sb_horse = sb_pick.get("horse", "?")
    sb_score = int(sb_pick.get("score", 0) or 0)
    tier_str = sb_pick.get("tier", "")
    tier_css_class, tier_color, tier_label = _tier_css(tier_str)
    score_html = _score_tag(sb_score, tier_css_class)

    is_split = mf_pick["is_split"]
    mf_horse = mf_pick["horse"]
    gap      = mf_pick["gap"]
    reason   = mf_pick.get("override_reason", "")

    tier_span = f'<span style="color:{tier_color};font-size:.8rem">{tier_label}</span>'
    grade_span = f'<span class="grade-badge {grade_css}">{grade_label}</span>'

    if not is_split:
        cw_note = COURSE_WINNERS.get(sb_horse, "")
        agree_text = f"Both entries agree{' &middot; ' + cw_note if cw_note else ''}"
        pick_cell = (
            f'<div class="horse-pick">{sb_horse} '
            f'<span class="banker-tag">&#9733; BANKER</span></div>'
            f'<div class="both-agree">{agree_text}</div>'
        )
        row_class = "banker-row"
    else:
        cw_sb = COURSE_WINNERS.get(sb_horse, "")
        cw_mf = COURSE_WINNERS.get(mf_horse, "")
        sb_note = f' <span style="font-size:.7rem;color:var(--muted)">({cw_sb})</span>' if cw_sb else ""
        mf_note = f' &middot; {cw_mf}' if cw_mf else ""
        pick_cell = (
            f'<div style="display:flex;flex-direction:column;gap:4px">'
            f'<div><span style="color:var(--blue);font-size:.72rem;font-weight:700">&#128309; SUREBET:</span> '
            f'<span style="font-weight:700;color:var(--green)">{sb_horse}</span>{sb_note}</div>'
            f'<div><span style="color:var(--orange);font-size:.72rem;font-weight:700">&#128992; MACFITZ:</span> '
            f'<span style="font-weight:700;color:var(--orange)">{mf_horse}</span>{mf_note} '
            f'<span class="split-tag">&#9889; SPLIT</span></div>'
            f'<div style="font-size:.7rem;color:var(--muted)">{reason}</div>'
            f'</div>'
        )
        row_class = "split-row"

    return (
        f'      <tr class="{row_class}">'
        f'<td class="time-cell">{time}</td>'
        f'<td>{grade_span}</td>'
        f'<td class="race-name">{display_name}</td>'
        f'<td>{pick_cell}</td>'
        f'<td>{score_html}</td>'
        f'<td>{tier_span}</td>'
        f'</tr>\n'
    )


def _pick_list_item(num: int, horse: str, race_display: str, time: str, score: int,
                    tier_str: str, color: str, is_split: bool = False,
                    split_note: str = "") -> str:
    _, tier_color, _ = _tier_css(tier_str)
    score_color = tier_color
    split_html  = f' <span class="split-tag">&#9889; SPLIT</span>' if is_split else ""
    note_html   = f'<br><span style="font-size:.72rem;font-style:italic;color:var(--muted)">{split_note}</span>' if split_note else ""
    return (
        f'      <div class="pick-item">'
        f'<div class="pick-num">{num}</div>'
        f'<div class="pick-body">'
        f'<div style="font-weight:600;color:{color}">{horse}{split_html}</div>'
        f'<div style="font-size:.75rem;color:var(--muted)">{time} {race_display}'
        f'<span style="font-size:.7rem;font-weight:600;color:{score_color}"> &middot; {score}</span>'
        f'{note_html}</div>'
        f'</div></div>\n'
    )


def build_html(assembled: list, run_date: str, n_splits: int, new_close_calls: list) -> str:
    # assembled: list of (race_info, sb_pick, mf_pick) in order

    # Detect day boundaries
    days_seen = []
    rows_by_day = {}
    for race, sb, mf in assembled:
        d = race[0]
        if d not in rows_by_day:
            rows_by_day[d] = []
            days_seen.append(d)
        rows_by_day[d].append((race, sb, mf))

    # Build day sections
    day_htmls = []
    for d in days_seen:
        items = rows_by_day[d]
        _, _, _, _, _, _, day_label, day_date = items[0][0]
        day_names_map = {1: "DAY 1", 2: "DAY 2", 3: "DAY 3", 4: "DAY 4"}
        header = (
            f'  <div class="day-header">'
            f'<span class="day-number">{day_names_map[d]}</span>'
            f'<span class="day-title">{day_label}</span>'
            f'<span class="day-date">{day_date}</span>'
            f'</div>\n'
        )
        thead = (
            f'  <table class="picks-table">\n'
            f'    <thead><tr><th>Time</th><th>Grade</th><th>Race</th>'
            f'<th>&#128309; Surebet &amp; &#128992; MacFitz</th>'
            f'<th>Score</th><th>Tier</th></tr></thead>\n'
            f'    <tbody>\n'
        )
        race_rows = ""
        for i, (race, sb, mf) in enumerate(items, 1):
            race_rows += _row_race(race, sb, mf, i)
        tfoot = f'    </tbody>\n  </table>\n'
        day_htmls.append(
            f'<div class="day-section">\n{header}{thead}{race_rows}{tfoot}</div>\n'
        )

    day_sections = "\n".join(day_htmls)

    # Build pick lists
    surebet_items = ""
    macfitz_items = ""
    current_day = None
    day_label_map = {1: "DAY 1 &mdash; CHAMPION DAY", 2: "DAY 2 &mdash; LADIES DAY",
                     3: "DAY 3 &mdash; ST PATRICK'S THURSDAY", 4: "DAY 4 &mdash; GOLD CUP DAY"}
    pick_num = 0
    for race, sb, mf in assembled:
        d = race[0]
        if d != current_day:
            current_day = d
            divider = f'      <div class="day-divider">{day_label_map[d]}</div>\n'
            surebet_items += divider
            macfitz_items += divider
        pick_num += 1
        time, race_display = race[1], race[3]
        sb_horse = sb.get("horse", "?")
        sb_score = int(sb.get("score", 0) or 0)
        tier_str = sb.get("tier", "")
        mf_horse = mf["horse"]
        mf_score = mf["score"]
        is_split = mf["is_split"]

        surebet_items += _pick_list_item(pick_num, sb_horse, race_display, time, sb_score,
                                         tier_str, "var(--green)")
        if is_split:
            macfitz_items += _pick_list_item(pick_num, mf_horse, race_display, time, mf_score,
                                              tier_str, "var(--orange)", is_split=True,
                                              split_note=f"Surebet: {sb_horse}")
        else:
            cw = COURSE_WINNERS.get(mf_horse, "")
            note = f"&#127942; {cw}" if cw else ""
            macfitz_items += _pick_list_item(pick_num, mf_horse, race_display, time, sb_score,
                                              tier_str, "var(--orange)",
                                              split_note=note)

    n_bankers = 28 - n_splits
    if n_splits == 0:
        notice_content = (
            f'<strong>&#9733; All 28 races are BANKERS this cycle</strong> &mdash; '
            f'both Surebet and MacFitz agree on every race.'
        )
        notice_class = "notice-box"
    else:
        split_race_names = ", ".join(
            f'<em>{race[3]}</em>' for race, sb, mf in assembled if mf["is_split"]
        )
        split_details = " | ".join(
            f'{race[3]}: MacFitz &rarr; <strong>{mf["horse"]}</strong> (gap={mf["gap"]})'
            for race, sb, mf in assembled if mf["is_split"]
        )
        notice_content = (
            f'<strong>&#9733; {n_bankers} BANKERS</strong> &mdash; both entries agree. '
            f'&nbsp;<strong style="color:var(--orange)">&#9889; {n_splits} SPLIT{"S" if n_splits>1 else ""}</strong>: '
            f'{split_details}'
        )
        notice_class = "notice-box has-splits"

    new_cc_html = ""
    if new_close_calls:
        new_cc_html = (
            f'<div style="margin-top:8px;padding:8px 12px;background:rgba(248,81,73,.1);'
            f'border:1px solid rgba(248,81,73,.4);border-radius:6px;font-size:.8rem;color:#f85149;">'
            f'<strong>&#9888; NEW CLOSE CALLS (not yet in overrides):</strong> '
            + " | ".join(
                f'{r}: {h1}({s1}) vs {h2}({s2}) gap={g}'
                for r, h1, s1, h2, s2, g in new_close_calls
            ) + '</div>'
        )

    sb_footer = (
        f'      <div style="margin-top:12px;padding:8px 12px;background:rgba(88,166,255,.08);'
        f'border-radius:6px;font-size:.8rem;color:var(--muted);">'
        f'{n_bankers} bankers &middot; {n_splits} split{"s" if n_splits!=1 else ""} (see MacFitz list) '
        f'&middot; Scores from live SureBet engine {run_date}</div>\n'
    )
    mf_footer = (
        f'      <div style="margin-top:12px;padding:8px 12px;background:rgba(210,153,34,.08);'
        f'border-radius:6px;font-size:.8rem;color:var(--muted);">'
        f'{n_bankers} bankers &middot; <strong style="color:var(--orange)">{n_splits} split{"s" if n_splits!=1 else ""}</strong> '
        f'(races apply macfitz_overrides.json) &middot; &#127942; = Cheltenham course winner</div>\n'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Barry's Cheltenham 2026 &mdash; Competition Picks</title>
<style>
{CSS}
</style>
</head>
<body>

<div class="masthead">
  <h1>Barry's Cheltenham 2026</h1>
  <div class="subtitle">Cheltenham Festival &middot; 10&ndash;13 March 2026 &middot; 28 Races &middot; Two Entries</div>
  <div>
    <span class="prize-badge">&pound;2,500 Prize</span>
    <span class="updated-tag">&#10003; Live scores &mdash; {run_date}</span>
  </div>
</div>

<div class="rules-bar">
  <div class="score-pill win">&#127949; 1st = 10 pts</div>
  <div class="score-pill place">&#127948; 2nd = 5 pts</div>
  <div class="score-pill show">&#127947; 3rd = 3 pts</div>
  <div class="score-pill zero">&#10060; Unplaced = 0</div>
  <div class="score-pill zero">Max possible: 280 pts (28 &times; 10)</div>
</div>

<div class="strategy-grid">
  <div class="strategy-card surebet">
    <h3>&#128309; Surebet</h3>
    <p><strong>Form-first strategy.</strong> Highest live SureBet score &mdash; best recent form, top trainer/jockey combo, class performer, course &amp; distance winner. Scores auto-refreshed daily from Betfair + Racing Post.</p>
  </div>
  <div class="strategy-card macfitz">
    <h3>&#128992; MacFitz</h3>
    <p><strong>Festival specialist strategy.</strong> Follows Surebet EXCEPT in dead-heat / near-tie races where a festival specialist or course winner is within striking distance. Splits governed by <code>macfitz_overrides.json</code>.</p>
  </div>
</div>

<div class="notice-wrapper">
  <div class="{notice_class}">
    {notice_content}
  </div>
  {new_cc_html}
</div>

<div class="content">

{day_sections}

<div class="summary-section">
  <h2>&#128203; Complete Entry Lists</h2>
  <div class="summary-grid">

    <div class="solo-list">
      <h3 class="surebet-header">&#128309; SUREBET &mdash; 28 Picks</h3>
{surebet_items}
{sb_footer}
    </div>

    <div class="solo-list">
      <h3 class="macfitz-header">&#128992; MACFITZ &mdash; 28 Picks</h3>
{macfitz_items}
{mf_footer}
    </div>

  </div>
</div>

</div>

<div class="footer">
  Barry's Cheltenham 2026 &middot; Auto-updated daily via SureBet engine + Betfair + Racing Post &middot; {run_date} &middot; Prize: &pound;2,500
</div>

</body>
</html>"""
    return html


# ── main ──────────────────────────────────────────────────────────────────────
def run(dry_run: bool = False, check_only: bool = False):
    run_date = datetime.now().strftime("%d %b %Y")
    print(f"\n{'='*70}")
    print(f"  BARRY'S HTML REGEN  —  {run_date}")
    print(f"{'='*70}\n")

    print("  [1] Loading MacFitz overrides ...")
    overrides = load_overrides()
    active_overrides = {k: v for k, v in overrides.get("overrides", {}).items() if v.get("active", True)}
    print(f"      {len(active_overrides)} active manual splits loaded")

    print("  [2] Fetching latest picks from CheltenhamPicks DynamoDB ...")
    db_picks = fetch_latest_picks()
    print(f"      {len(db_picks)} races found in DB")

    # Assemble in RACES order
    assembled = []
    new_close_calls = []
    n_splits = 0
    missing = []

    for race in RACES:
        db_name = race[2]
        sb_pick = db_picks.get(db_name)
        if not sb_pick:
            # Try partial match
            for key in db_picks:
                if db_name.lower() in key.lower() or key.lower() in db_name.lower():
                    sb_pick = db_picks[key]
                    break
        if not sb_pick:
            missing.append(db_name)
            sb_pick = {"horse": "TBC", "score": 0, "tier": "? UNKNOWN",
                       "race_name": db_name, "second_horse_name": "", "second_score": 0, "score_gap": 999}

        mf_pick = apply_macfitz(sb_pick, overrides)
        if mf_pick["is_split"]:
            n_splits += 1
        if mf_pick["new_close_call"]:
            h2 = sb_pick.get("second_horse_name", "?")
            s1 = int(sb_pick.get("score", 0) or 0)
            s2 = int(sb_pick.get("second_score", 0) or 0)
            new_close_calls.append((db_name, sb_pick.get("horse", "?"), s1, h2, s2, mf_pick["gap"]))

        assembled.append((race, sb_pick, mf_pick))

    if missing:
        print(f"\n  [WARN] {len(missing)} races not found in DB: {missing}")

    # Report
    n_bankers = 28 - n_splits
    print(f"\n  RESULT:  {n_bankers} bankers  |  {n_splits} splits")
    for race, sb, mf in assembled:
        if mf["is_split"]:
            print(f"    ⚡ SPLIT  {race[1]} {race[3]:45}  Surebet={mf['surebet_horse']}  MacFitz={mf['horse']}  gap={mf['gap']}")
    if new_close_calls:
        print(f"\n  ⚠ NEW CLOSE CALLS (not yet in overrides — consider updating macfitz_overrides.json):")
        for r, h1, s1, h2, s2, g in new_close_calls:
            print(f"    {r}: {h1}({s1}) vs {h2}({s2}) gap={g}")

    if check_only:
        print("\n  [--check-splits]: no HTML written.")
        return

    print("\n  [3] Generating HTML ...")
    html = build_html(assembled, run_date, n_splits, new_close_calls)

    if dry_run:
        print(f"\n  [DRY RUN] Would write {len(html):,} bytes to {HTML_OUT}")
        print("  (Use without --dry-run to write the file)")
        return

    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"\n  [4] Written {len(html):,} bytes → {HTML_OUT}")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate Barry's Cheltenham 2026 HTML from live DynamoDB data")
    parser.add_argument("--dry-run",      action="store_true", help="Print what would change but don't write file")
    parser.add_argument("--check-splits", action="store_true", help="Show close-call report only, no HTML write")
    args = parser.parse_args()
    run(dry_run=args.dry_run, check_only=args.check_splits)
