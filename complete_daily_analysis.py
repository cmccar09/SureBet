# -*- coding: utf-8 -*-
"""
COMPLETE DAILY WORKFLOW -- 5-PICK SELECTION ENGINE
===================================================
Strategy:
  1. Score EVERY horse in EVERY race with the comprehensive 7-factor model
  2. For each race, identify the single best-scoring horse  (race winner candidate)
  3. Across all races, rank those race-bests by score — select TOP 5
  4. Mark exactly those 5 as show_in_ui=True; everything else is learning data
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
from notify_picks import send_pick_notifications

# ── Form enricher (deep per-run history from Racing Post/Sporting Life) ──────
# Unlocks: exact_course_win (+20), exact_distance_win (+20), going_win_match
# (+16/32), close_2nd_last_time (+14), fresh_days_optimal (+10), OR trajectory
try:
    from form_enricher import enrich_runners as _form_enrich
    _FORM_ENRICHER_AVAILABLE = True
except ImportError:
    _FORM_ENRICHER_AVAILABLE = False
    def _form_enrich(races, **kw): return races

db    = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

TARGET_PICKS   = 5      # RESTORED 3→5 (2026-03-30): 42.9% SR × 3 picks = 1.3 winners/day;
                        # need 5 picks for reliable 2+ winners.  Quality gates still filter junk.
MIN_CONFIDENCE = 78     # 2026-03-27: restored from over-corrected 85 back to 78.
                        # Raising to 85 + halving market_leader_bonus (12→6) created a deadlock:
                        # no horses reached 85 on Mar 26-27 (best was 83). 78 is the new floor.


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
    # UPDATED 2026-03-25: Aligning thresholds with deployed Lambda (STRONG was 80, now 85).
    # LESSON: All losses (81-92) were in the old STRONG zone. Raising thresholds reduces
    # overconfident labelling — only genuinely elite picks earn the STRONG badge.
    if score >= 92: return "ELITE",   "ELITE (Top-tier confidence)", "green"
    if score >= 85: return "STRONG",  "STRONG (High confidence)",    "green"   # was 80
    if score >= 75: return "GOOD",    "GOOD (Solid pick)",           "light-green"  # was 70
    if score >= 60: return "FAIR",    "FAIR (Decent chance)",        "light-amber"
    if score >= 45: return "RISKY",   "RISKY (Lower confidence)",    "dark-amber"
    return              "POOR",   "POOR (Very unlikely)",        "red"


def analyze_and_save_all():
    """
    Two-pass algorithm:
      Pass 1 — Score every horse, collect per-race bests.
      Select top-5 cross-race bests.
      Pass 2 — Save everything with correct show_in_ui flag.
    """
    races = load_races()
    if not races:
        print("No races found — run betfair_odds_fetcher.py first")
        return

    # ── STAGE 1: Deep form enrichment ────────────────────────────────────────
    # Fetches last-6-race run history from Racing Post / Sporting Life for every
    # runner and injects it as 'form_runs'. The scoring engine reads this to fire
    # exact_course_win (+20), exact_distance_win (+20), going_win_match (+32),
    # close_2nd_last_time (+14), fresh_days_optimal (+10), or_trajectory (+10).
    # Without this step all deep_form signals score 0 for every horse.
    _form_total_horses = sum(len(r.get('runners', [])) for r in races)
    _form_enriched_count = 0
    if _FORM_ENRICHER_AVAILABLE:
        print(f"\n[STAGE 1/5] Deep form enrichment — {_form_total_horses} horses from Racing Post/SL...")
        races = _form_enrich(races, verbose=True)
        _form_enriched_count = sum(
            1 for race in races for runner in race.get('runners', [])
            if runner.get('form_runs')
        )
        print(f"  ✓ Form enriched {_form_enriched_count}/{_form_total_horses} horses "
              f"({round(100*_form_enriched_count/_form_total_horses) if _form_total_horses else 0}%)")
    else:
        print("[STAGE 1/5] Form enrichment unavailable — deep form signals will score 0")

    print("\n" + "=" * 100)
    print("DAILY 3-PICK SELECTION ENGINE")
    print("=" * 100)
    print(f"  Races    : {len(races)}")
    print(f"  Strategy : Best horse per race -> top {TARGET_PICKS} cross-race bests (min score {MIN_CONFIDENCE})")
    print("=" * 100 + "\n")

    today        = datetime.now().strftime('%Y-%m-%d')
    avg_winner_odds = 4.65  # UK average winning SP

    # ── STAGE 2: Horse history from DynamoDB ─────────────────────────────────
    print("[STAGE 2/5] Loading horse history from DynamoDB...")
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
                n_runners=len(runners),
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
                market_leader_bonus = 16   # Race favourite — INCREASED 9→16 (2026-03-30): market leads 36% of losses
                score += market_leader_bonus
                reasons.append(f"Race market leader (lowest odds): +{market_leader_bonus}pts")
                breakdown['market_leader'] = market_leader_bonus
            elif odds > 1.0 and odds <= favourite_odds * 1.20:
                market_leader_bonus = 10   # Joint/co-favourite — INCREASED 4→10 (2026-03-30)
                score += market_leader_bonus
                reasons.append(f"Market co-favourite: +{market_leader_bonus}pts")
                breakdown['market_leader'] = market_leader_bonus
            elif odds > 1.0 and odds <= favourite_odds * 1.40:
                market_leader_bonus = 5    # Second choice within 40% of favourite — NEW tier (2026-03-30)
                score += market_leader_bonus
                reasons.append(f"Market second choice: +{market_leader_bonus}pts")
                breakdown['market_leader'] = market_leader_bonus

            # ── Price steam / drift bonus (2026-03-30) ───────────────────────
            # Detected by betfair_odds_fetcher.py price_history comparison.
            # 'steaming' = price dropped ≥20% since last fetch (smart money in).
            # 'drifting'  = price rose ≥25% since last fetch (money going out).
            _pm = runner.get('price_movement', 'stable')
            _pm_pct = float(runner.get('price_move_pct', 0) or 0)
            if _pm == 'steaming' and _pm_pct >= 20:
                _steam_pts = min(15, int(_pm_pct * 0.5))   # e.g. 25% drop → +12 pts
                score += _steam_pts
                breakdown['price_steam'] = _steam_pts
                reasons.append(f"Market steaming: backed {_pm_pct:.0f}% shorter: +{_steam_pts}pts")
            elif _pm == 'drifting' and _pm_pct <= -25:
                _drift_pts = min(8, int(abs(_pm_pct) * 0.3))  # e.g. 30% rise → -9 → cap -8
                score -= _drift_pts
                breakdown['price_steam'] = -_drift_pts
                reasons.append(f"Market drifting: {abs(_pm_pct):.0f}% longer than last fetch: -{_drift_pts}pts")
            else:
                breakdown['price_steam'] = 0

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
                'pick_rank':           0,       # 1-5 for top picks; 0 = learning
                'analysis_type':       'comprehensive_7factor',
                'score_breakdown':     breakdown,
                'selection_reasons':   reasons,
                'sport':               'horses',
                'market_id':           market_id,
                'selection_id':        runner.get('selectionId', 0),
                'race_coverage_pct':   Decimal('100'),
                'race_total_count':    len(runners),
                'created_at':          datetime.now().isoformat(),
                'updated_at':          datetime.now().isoformat(),
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
            'venue':        venue,
            'race_time':    race_time,
            'market_name':  race.get('market_name', ''),   # e.g. "6f Nov Stks"
            'runners':      race_runners,
            'raw_runners':  runners,                       # original Betfair dicts with form/odds
            'best':         best,
            'n_runners':    len(runners),
        })

    # ── SELECT TOP 5 CROSS-RACE BESTS ────────────────────────────────────────
    def _passes_quality_gates(r):
        """Quality gate filters applied at pick-selection time.
        S1: Non-market-backed picks need score >= 85 (or 80 if tr/cd anchor present; unexposed >= 50).
        S2: Must have at least one contextual anchor: market_leader, trainer, cd_bonus, OR unexposed_bonus.
            Override: score >= 88 AND gap >= 20 passes without anchor (clear model conviction).
        S3: Age-propped picks (age_bonus >= 10, no market/trainer) need score >= 92 (unexposed >= 50).
        S4: Score gap must be >= 8 (too-close races are coin-flips). Elite (>= 88) bypass.
        S5: Saturday gate — data shows only 9.3pt winner/loser gap on Saturdays vs 21.5pt on Sundays.
            Saturday races: score_gap must be >= 15, AND market_leader signal required for 16+ fields.
        S6: Large field (16+ runners) without market backing: require score_gap >= 12.
        S7: Novice/debut-heavy race — ≥60% runners with ≤1 career run in a named novice/conditions
            stakes, or ≥80% debut runners in any race → skip (model has no rivals form to compare).
            Override: our pick has ≥3 runs AND score >= 88 (we have form, others don't).
        2026-03-27: Relaxed S1 threshold (90→85/80) and added S2 override + S4 elite bypass.
        2026-03-29: Added S5 Saturday tightening + S6 large-field market requirement.
        2026-03-30: Added S7 novice/debut-heavy race gate.
        LESSON: Over-correcting on 2026-03-25 (85 threshold + halved ml bonus) → 0 picks for 2 days.
        LESSON: Saturday analysis — losers averaged 94.2pts (hardly below winners at 103.5); Sunday
                 losers averaged 74.7pts (clearly below winners at 96.2). Saturdays need harder gates.
        LESSON: 2026-03-30 Kempton 14:10 — picked Barefoot Beach (85pts, CD win) but 4/5 runners
                 had only 1 career run → Sizzling Seixas won at 9/1 → novice races are ungradeable.
        """
        score      = r['best']['score']
        bd         = r['best']['item'].get('score_breakdown', {})
        ml         = float(bd.get('market_leader', 0))
        tr         = float(bd.get('trainer_reputation', 0))
        cd         = float(bd.get('cd_bonus', 0))
        age        = float(bd.get('age_bonus', 0))
        unexposed  = float(bd.get('unexposed_bonus', 0))
        deep_form  = float(bd.get('deep_form', 0))   # SL form signals (course/distance/going wins)
        score_gap  = float(r['best']['item'].get('score_gap', 0))
        n_runners  = r.get('n_runners', 0)

        # Detect day of week from race_time
        is_saturday = False
        try:
            _rt = r.get('race_time', '')
            if _rt:
                _d = datetime.fromisoformat(_rt[:19])
                is_saturday = (_d.weekday() == 5)  # 5 = Saturday
        except Exception:
            pass

        # S5 — Saturday-specific tightening
        # Data: Saturday model discrimination gap is only 9.3pts (winner 103.5 vs loser 94.2).
        # Require a larger gap between our pick and the next-best horse in the race.
        if is_saturday:
            sat_gap_req = 15
            if score < 88 and score_gap < sat_gap_req:
                print(f"  [GATE-S5 REJECTED] {r['best']['horse']} score={score:.0f}: "
                      f"SATURDAY gate — score_gap={score_gap:.1f} < {sat_gap_req} required "
                      f"(Saturday model discrimination historically weak — 9.3pt winner/loser gap)")
                return False
            # For 16+ runner races on Saturday, must have market backing — too chaotic otherwise
            if n_runners >= 16 and ml == 0:
                print(f"  [GATE-S5 REJECTED] {r['best']['horse']} score={score:.0f}: "
                      f"SATURDAY large field ({n_runners} runners) — market leader signal required")
                return False

        # S6 — Large field without market backing
        # 16+ runner fields have pace/draw/traffic variance the model cannot see.
        # Without market agreement, our pick is essentially a coin-flip.
        if n_runners >= 16 and ml == 0 and score < 92:
            if score_gap < 12:
                print(f"  [GATE-S6 REJECTED] {r['best']['horse']} score={score:.0f}: "
                      f"large field ({n_runners} runners), no market signal, gap={score_gap:.1f} < 12")
                return False

        # S2 — hard gate: at least one contextual anchor required
        # Anchors: market_leader, trainer, cd_bonus, unexposed_bonus, OR strong deep_form (≥16pts)
        # deep_form ≥ 16 = horse won on this going/course/distance → legitimate evidence
        # Override: high-conviction picks (88+ score, 20+ point gap) bypass anchor check
        if ml == 0 and tr == 0 and cd == 0 and unexposed == 0 and deep_form < 16:
            if score >= 88 and score_gap >= 20:
                print(f"  [GATE-S2 OVERRIDE] {r['best']['horse']} score={score:.0f} gap={score_gap:.0f}: "
                      f"high-conviction override — no anchor but clear model advantage")
            else:
                print(f"  [GATE-S2 REJECTED] {r['best']['horse']} score={score:.0f}: "
                      f"no market_leader/trainer_rep/cd_bonus/unexposed signal")
                return False

        # S1 — non-market-backed picks need good score
        # If horse has another anchor (trainer or cd), threshold is 80; otherwise 85
        if ml == 0:
            if unexposed >= 10:
                min_s1 = 50
            elif tr > 0 or cd > 0:
                min_s1 = 80   # Has other anchor signal — lower bar than pure market picks
            else:
                min_s1 = 85   # No market AND no other anchor except S2 override
            if score < min_s1:
                print(f"  [GATE-S1 REJECTED] {r['best']['horse']} score={score:.0f}: "
                      f"not market-backed, needs >= {min_s1}")
                return False

        # S3 — age-padded with no market or trainer support needs >= 92; unexposed ≤5yo >= 50
        if age >= 10 and ml == 0 and tr == 0:
            min_s3 = 50 if unexposed >= 10 else 92
            if score < min_s3:
                print(f"  [GATE-S3 REJECTED] {r['best']['horse']} score={score:.0f}: "
                      f"age_bonus={age:.0f} dominant, needs >= {min_s3}")
                return False

        # S4 — Score gap gate: require the race-best to outscore 2nd-best by at least 8 points.
        # ELITE bypass: scores >= 88 already indicate strong model conviction.
        if score < 88 and score_gap < 8:
            print(f"  [GATE-S4 REJECTED] {r['best']['horse']} score={score:.0f}: "
                  f"score_gap={score_gap:.1f} < 8 (too tight, race is a coin-flip)")
            return False

        # S7 — Novice/debut-heavy race gate (2026-03-30)
        # LESSON: 14:10 Kempton — 4/5 runners had 1 career run; won by a 9/1 shot.
        #   Barefoot Beach scored 85 (CD win, co-fav) but form data was nearly non-existent
        #   for most rivals → model has nothing to compare against → effectively a coin-flip.
        # Rule: if ≥ 60% of runners are on debut or have a single career run, SKIP unless:
        #   (a) our pick is the ONLY runner with real form (>= 3 runs), AND score >= 88, OR
        #   (b) race_name explicitly isn't a novice/conditions stakes
        _all_runners = r.get('raw_runners', [])
        if _all_runners:
            _debut_count = 0
            for _ru in _all_runners:
                _form = str(_ru.get('form', '') or '').strip()
                # Betfair FORM field: '-' = no runs, single char = 1 run, '1-' = debut win, etc.
                _run_chars = _form.replace('-', '').replace('/', '').replace('P', '') \
                                  .replace('F', '').replace('U', '').replace('0', '')
                _is_debut_or_one_run = len(_form) == 0 or _form == '-' or len(_run_chars) <= 1
                if _is_debut_or_one_run:
                    _debut_count += 1
            _debut_ratio = _debut_count / len(_all_runners)
            if _debut_ratio >= 0.60:
                _our_form = str(r['best']['item'].get('form', '') or '').strip()
                _our_runs = len(_our_form.replace('-', '').replace('/', ''))
                _market_name = r.get('market_name', '').lower()
                _is_novice_name = any(kw in _market_name for kw in
                                      ['nov', 'novice', 'mdn', 'maiden', 'cond', 'nstks', 'nst'])
                if _debut_ratio >= 0.80 and not (_our_runs >= 3 and score >= 88):
                    print(f"  [GATE-S7 REJECTED] {r['best']['horse']} score={score:.0f}: "
                          f"debut-heavy field — {_debut_count}/{len(_all_runners)} runners "
                          f"({_debut_ratio:.0%} ≤1 run) → model has no rivals form to compare")
                    return False
                if _is_novice_name and not (_our_runs >= 3 and score >= 88):
                    print(f"  [GATE-S7 REJECTED] {r['best']['horse']} score={score:.0f}: "
                          f"novice stakes ('{r.get('market_name','')}') — "
                          f"{_debut_count}/{len(_all_runners)} runners ≤1 run → skip")
                    return False

        return True

    eligible = [r for r in all_races_data
                if r['best']['score'] >= MIN_CONFIDENCE and _passes_quality_gates(r)]
    eligible.sort(key=lambda r: r['best']['score'], reverse=True)

    # ── DIVERSE PICK SELECTION (2026-03-30) ────────────────────────────────────
    # Naively taking top-N by score often yields all picks in the same 3.5-5.0 odds band.
    # Mix across three price tiers so at least 1 pick is in each band when available:
    #   Tier A: 1.5-3.9  (short-priced, lower payout but higher SR)
    #   Tier B: 4.0-7.9  (value sweet-spot, avg winner odds 3.7)
    #   Tier C: 8.0+     (outsider/value pick, higher upside)
    # Fill strategy: take greedy top score but don't exceed 2 picks per tier.
    _tier_counts = {'A': 0, 'B': 0, 'C': 0}
    def _odds_tier(odds):
        if odds < 4.0:  return 'A'
        if odds < 8.0:  return 'B'
        return 'C'
    top_picks = []
    for r in eligible:
        if len(top_picks) >= TARGET_PICKS:
            break
        tier = _odds_tier(float(r['best']['odds']))
        if _tier_counts[tier] < 2:
            top_picks.append(r)
            _tier_counts[tier] += 1
    # If we didn't fill 5 (rare — all remaining from already-full tiers), top up greedily
    if len(top_picks) < TARGET_PICKS:
        remaining = [r for r in eligible if r not in top_picks]
        top_picks += remaining[:TARGET_PICKS - len(top_picks)]

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

    # ── STAGE 5: Save analysis manifest ──────────────────────────────────────
    # Stores the pipeline completion status in DynamoDB so the UI can display
    # a real-time checklist showing which analysis stages fired today.
    try:
        _all_scored_items = [r['item'] for rd in all_races_data for r in rd['runners']]

        def _sig_pct(key):
            if not _all_scored_items: return 0
            n = sum(1 for i in _all_scored_items
                    if float((i.get('score_breakdown') or {}).get(key, 0)) != 0)
            return round(100 * n / len(_all_scored_items))

        from comprehensive_pick_logic import get_going_conditions as _gwc
        _going_ok = bool(_gwc())
        _form_pct = (round(100 * _form_enriched_count / _form_total_horses)
                     if _form_total_horses else 0)
        manifest = {
            'bet_id':   'SYSTEM_ANALYSIS_MANIFEST',
            'bet_date': 'STATUS',
            'run_time': datetime.now().isoformat(),
            'today':    today,
            'picks_generated':        Decimal(str(ui_promoted)),
            'horses_scored':          Decimal(str(len(_all_scored_items))),
            'analysis_complete':      (ui_promoted > 0),
            # Stage statuses
            'stage_betfair':          'ok',
            'stage_betfair_races':    Decimal(str(len(races))),
            'stage_betfair_horses':   Decimal(str(_form_total_horses)),
            'stage_history':          'ok',
            'stage_history_horses':   Decimal(str(len(horse_history))),
            'stage_going':            'ok' if _going_ok else 'missing',
            'stage_form_enricher':    'ok' if _form_enriched_count > 0 else 'not_run',
            'stage_form_enriched':    Decimal(str(_form_enriched_count)),
            'stage_form_total':       Decimal(str(_form_total_horses)),
            'stage_form_pct':         Decimal(str(_form_pct)),
            'stage_scoring':          'ok',
            'stage_picks':            'ok' if ui_promoted > 0 else 'no_picks',
            # Signal coverage (% of scored horses where each signal fired > 0)
            'sig_market_leader':      Decimal(str(_sig_pct('market_leader'))),
            'sig_deep_form':          Decimal(str(_sig_pct('deep_form'))),
            'sig_trainer':            Decimal(str(_sig_pct('trainer_reputation'))),
            'sig_going':              Decimal(str(_sig_pct('going_suitability'))),
            'sig_consistency':        Decimal(str(_sig_pct('consistency'))),
            'sig_cd_bonus':           Decimal(str(_sig_pct('cd_bonus'))),
            'sig_jockey':             Decimal(str(_sig_pct('jockey_quality'))),
            'sig_distance':           Decimal(str(_sig_pct('distance_suitability'))),
        }
        table.put_item(Item=manifest)
        print(f"[STAGE 5/5] Analysis manifest saved — pipeline "
              f"{'COMPLETE ✓' if ui_promoted > 0 and _form_enriched_count > 0 else 'PARTIAL ⚠'}")
    except Exception as _me:
        print(f"[STAGE 5/5] Warning: manifest save failed — {_me}")

    # ── WHATSAPP NOTIFICATIONS ────────────────────────────────────────────────
    if ui_promoted > 0:
        ui_pick_items = [
            r['item']
            for race_data in all_races_data
            for r in race_data['runners']
            if top_bet_ids.get(r['item']['bet_id'], 0) > 0
        ]
        # Sort by race_time so message is in chronological order
        ui_pick_items.sort(key=lambda x: str(x.get('race_time', '')))
        sent, err = send_pick_notifications(ui_pick_items)
        if sent:
            print(f'[WhatsApp] Notifications sent to {sent} recipient(s)')
        elif err:
            print(f'[WhatsApp] Skipped: {err}')

    return {'total': total_saved, 'ui_picks': ui_promoted, 'learning': total_saved - ui_promoted}


if __name__ == "__main__":
    stats = analyze_and_save_all()
    if stats:
        if stats['ui_picks']:
            print(f"OK {stats['ui_picks']} picks ready - run 'python show_todays_ui_picks.py' to review")
        else:
            print("WARNING: No high-confidence picks today -- check response_horses.json for race data")


