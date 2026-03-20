"""
COMPREHENSIVE BETTING WORKFLOW with 4-Tier Grading
Replaces odds-only analysis with full 7-factor comprehensive analysis

This script:
1. Fetches races from Betfair
2. Analyzes each race using comprehensive_pick_logic.py
3. Applies 4-tier grading validation
4. Only shows picks passing validation on UI

4-TIER GRADING SYSTEM (Default):
- EXCELLENT: 75+ points (Green)       - 2.0x stake
- GOOD:      60-74 points (Light amber) - 1.5x stake
- FAIR:      45-59 points (Dark amber)  - 1.0x stake
- POOR:      <45 points (Red)         - 0.5x stake

MANDATORY COVERAGE:
- Analyze ALL horses in ALL races (100% target)
- Minimum 90% coverage - races below this are SKIPPED
- Lesson from Carlisle 15:35: 9% coverage = system failure
- Never make picks without analyzing the full field
"""

import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from comprehensive_pick_logic import analyze_horse_comprehensive, get_comprehensive_pick, should_skip_race
from enforce_comprehensive_analysis import validate_pick_for_ui, add_pick_to_ui

# Optional: enrich runners with detailed last-6-race history from Racing Post
try:
    from form_enricher import enrich_runners
    FORM_ENRICHER_AVAILABLE = True
except ImportError:
    FORM_ENRICHER_AVAILABLE = False
    def enrich_runners(races, verbose=True): return races

def fetch_upcoming_races(hours_ahead=6):
    """
    Get upcoming races from Betfair or JSON file
    """
    # Try to load from recent Betfair fetch
    try:
        with open('response_horses.json', 'r') as f:
            data = json.load(f)
        
        races = data.get('races', [])
        
        # Filter to upcoming races
        now = datetime.now()
        upcoming = []
        
        for race in races:
            race_time_str = race.get('start_time', '')
            if race_time_str:
                try:
                    race_dt = datetime.fromisoformat(race_time_str.replace('Z', '+00:00'))
                    race_dt_local = race_dt.replace(tzinfo=None)
                    
                    if now < race_dt_local < now + timedelta(hours=hours_ahead):
                        upcoming.append(race)
                except:
                    continue
        
        return upcoming
    except FileNotFoundError:
        print("⚠️  response_horses.json not found - run betfair_odds_fetcher.py first")
        return []

def process_race_comprehensive(race, meeting_context=None):
    """
    Process a single race using comprehensive analysis
    Returns pick dict if suitable horse found, None otherwise
    """
    venue = race.get('venue', 'Unknown')
    race_time = race.get('start_time', '')
    race_name = race.get('market_name', 'Unknown Race')
    runners = race.get('runners', [])

    # ------------------------------------------------------------------
    # SKIP FILTER: Class 3/4/5/6 handicaps are too unpredictable for our
    # model (lesson: 2026-03-01 Huntingdon 14:45 Reallyntruthfully PU)
    # ------------------------------------------------------------------
    skip, skip_reason = should_skip_race(race)
    if skip:
        print(f"\n[SKIP] {race_time} {venue} | {race_name}")
        print(f"   Reason: {skip_reason}")
        return None

    print(f"\n{'='*80}")
    print(f"ANALYZING: {race_time} - {venue} - {race_name}")
    print(f"Runners: {len(runners)}")
    print(f"{'='*80}")
    
    # Course stats (use Wolverhampton validated data for now)
    course_stats = {
        'avg_winner_odds': 4.75 if 'wolverhampton' in venue.lower() else 4.65,
        'optimal_range': (4.0, 6.0) if 'wolverhampton' in venue.lower() else (3.5, 7.0)
    }
    
    # Get comprehensive pick
    pick = get_comprehensive_pick({
        'course': venue,
        'race_time': race_time,
        'race_name': race_name,
        'runners': runners
    }, course_stats, meeting_context=meeting_context)
    
    if pick:
        # Validate for UI
        is_valid, score, reason = validate_pick_for_ui(pick)
        
        if is_valid:
            horse_name = pick['horse'].get('name', 'Unknown') if isinstance(pick['horse'], dict) else str(pick['horse'])
            horse_odds = pick['horse'].get('odds', 0) if isinstance(pick['horse'], dict) else 0
            print(f"\n[APPROVED] {horse_name} @ {horse_odds}")
            print(f"   Score: {score}/100")
            reasons = pick.get('reasons', [])
            if reasons:
                print(f"   Reasoning: {reasons[0][:100]}...")
            return pick
        else:
            horse_name = pick['horse'].get('name', 'Unknown') if isinstance(pick.get('horse'), dict) else str(pick.get('horse', 'Unknown'))
            print(f"\n[REJECTED] {horse_name}")
            print(f"   {reason}")
            return None
    else:
        print(f"\n[SKIPPED] No horses meet comprehensive criteria")
        return None

def build_meeting_context(races):
    """
    Pre-compute meeting-level signals for all races fetched today.
    Returns a dict consumed by analyze_horse_comprehensive (meeting_context param).

    Signals built:
      trainer_meetings : {trainer_name -> set of courses running at today}
      jockey_meetings  : {jockey_name  -> set of courses running at today}
      combo_meetings   : {"trainer|jockey" -> set of courses}
      new_trainer_horses: set of "horse_name|trainer" keys where the trainer
                          has never appeared for this horse in our DynamoDB history.
    """
    from collections import defaultdict
    trainer_meetings = defaultdict(set)
    jockey_meetings  = defaultdict(set)
    combo_meetings   = defaultdict(set)

    all_horse_names = []
    horse_trainer_map = {}  # horse_name -> current trainer

    for race in races:
        course = race.get('venue', race.get('course', ''))
        for runner in race.get('runners', []):
            t = str(runner.get('trainer', '')).strip()
            j = str(runner.get('jockey', '')).strip()
            h = str(runner.get('name', '')).strip()
            if t and course:
                trainer_meetings[t].add(course)
            if j and course:
                jockey_meetings[j].add(course)
            if t and j and course:
                combo_key = f"{t}|{j}"
                combo_meetings[combo_key].add(course)
            if h:
                all_horse_names.append(h)
                if h not in horse_trainer_map and t:
                    horse_trainer_map[h] = t

    # Build new_trainer_horses via DynamoDB scan (one-shot batch)
    new_trainer_horses = set()
    if all_horse_names:
        try:
            import boto3
            from boto3.dynamodb.conditions import Attr
            db = boto3.resource('dynamodb', region_name='eu-west-1')
            table = db.Table('SureBetBets')
            unique_names = list(set(all_horse_names))
            # Scan in chunks of 50 to avoid expression limits
            horse_trainers_seen = defaultdict(set)
            chunk_size = 50
            for i in range(0, len(unique_names), chunk_size):
                chunk = unique_names[i:i + chunk_size]
                if len(chunk) == 1:
                    fe = Attr('horse').eq(chunk[0])
                else:
                    fe = Attr('horse').eq(chunk[0])
                    for name_val in chunk[1:]:
                        fe = fe | Attr('horse').eq(name_val)
                resp = table.scan(FilterExpression=fe, ProjectionExpression='horse, trainer')
                for item in resp.get('Items', []):
                    h_name = str(item.get('horse', '')).strip()
                    h_trainer = str(item.get('trainer', '')).strip()
                    if h_name and h_trainer:
                        horse_trainers_seen[h_name].add(h_trainer)
            # A horse's current trainer is "new" if it has DB history but none with this trainer
            for horse_name, current_trainer in horse_trainer_map.items():
                if current_trainer and horse_name in horse_trainers_seen:
                    seen = horse_trainers_seen[horse_name]
                    if current_trainer not in seen:
                        new_trainer_horses.add(f"{horse_name}|{current_trainer}")
        except Exception as e:
            print(f"  [build_meeting_context] DB lookup failed: {e}")

    context = {
        'trainer_meetings': dict(trainer_meetings),
        'jockey_meetings':  dict(jockey_meetings),
        'combo_meetings':   dict(combo_meetings),
        'new_trainer_horses': new_trainer_horses,
    }

    # Summary
    sole_trainers = sum(1 for v in trainer_meetings.values() if len(v) == 1)
    sole_jockeys  = sum(1 for v in jockey_meetings.values()  if len(v) == 1)
    print(f"  Meeting context: {sole_trainers} trainer(s) and {sole_jockeys} jockey(s) focused on a single meeting today")
    if new_trainer_horses:
        print(f"  New trainer debuts detected: {len(new_trainer_horses)}")
    return context


def load_intraday_learnings():
    """Load insights from earlier races today"""
    try:
        with open('intraday_learnings.json', 'r') as f:
            learnings = json.load(f)
            print("✓ Loaded intraday learnings from earlier races")
            
            # Display key insights
            for learning in learnings.get('learnings', []):
                if learning['type'] == 'HOT_TRAINERS':
                    trainers = [t[0] for t in learning['data'][:3]]
                    print(f"  🔥 Hot trainers today: {', '.join(trainers)}")
                elif learning['type'] == 'WINNING_ODDS_RANGE':
                    category, stats = learning['data']
                    print(f"  💰 Best odds range: {category} ({stats['win_rate']*100:.0f}% win rate)")
            print()
            return learnings
    except FileNotFoundError:
        print("ℹ️  No intraday learnings available (run intraday_learning_system.py first)")
        print()
        return None

def run_comprehensive_workflow():
    """
    Main workflow: Fetch races, analyze comprehensively, add approved picks to UI
    """
    print("\n" + "="*80)
    print("COMPREHENSIVE BETTING WORKFLOW")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Analysis: 7-factor comprehensive (minimum 60/100)")
    print("="*80 + "\n")
    
    # Load intraday learnings from earlier races
    intraday_learnings = load_intraday_learnings()
    
    # Fetch upcoming races
    races = fetch_upcoming_races(hours_ahead=6)
    
    if not races:
        print("No upcoming races found in next 6 hours")
        return
    
    print(f"Found {len(races)} upcoming races\n")

    # Enrich runners with detailed last-6-race form from Racing Post (with disk cache)
    if FORM_ENRICHER_AVAILABLE:
        print("Fetching detailed form history from Racing Post (cached)...")
        races = enrich_runners(races, verbose=True)
        print()

    # Build meeting-level context for focus signals (sole trainer/jockey at a meeting)
    print("Building meeting context...")
    meeting_context = build_meeting_context(races)
    print()

    approved_picks = []
    rejected_count = 0
    skipped_too_close = 0
    
    # Process each race
    for race in races:
        pick = process_race_comprehensive(race, meeting_context=meeting_context)
        
        if pick:
            # Add to database
            race_data = {
                'course': race.get('venue'),
                'race_time': race.get('start_time'),
                'race_name': race.get('market_name', 'Unknown'),
                'market_id': race.get('market_id')  # For results fetching
            }
            
            success = add_pick_to_ui(pick, race_data)
            if success:
                approved_picks.append(pick)
        else:
            # Check if this was skipped due to multiple 85+ horses
            race_id = f"{race.get('venue')}_{race.get('start_time')}"
            if "RACE SKIPPED" in str(race):
                skipped_too_close += 1
            else:
                rejected_count += 1
    
    # Summary
    print("\n" + "="*80)
    print("WORKFLOW COMPLETE")
    print("="*80)
    print(f"Races analyzed: {len(races)}")
    print(f"Picks approved: {len(approved_picks)}")
    print(f"Picks rejected: {rejected_count}")
    if skipped_too_close > 0:
        print(f"Races skipped (too close to call): {skipped_too_close}")
    
    if approved_picks:
        print(f"\nAPPROVED PICKS (added to UI):")
        for pick in approved_picks:
            horse_name = pick['horse'].get('name', 'Unknown') if isinstance(pick['horse'], dict) else str(pick['horse'])
            horse_odds = pick['horse'].get('odds', 0) if isinstance(pick['horse'], dict) else 0
            score = pick.get('score', pick.get('comprehensive_score', 0))
            print(f"  + {horse_name} @ {horse_odds} - {score}/100")
    
    print("\n" + "="*80)
    print("+ All UI picks passed comprehensive analysis")
    print("+ No odds-only picks allowed")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_comprehensive_workflow()
