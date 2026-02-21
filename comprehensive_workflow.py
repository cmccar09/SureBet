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
from comprehensive_pick_logic import analyze_horse_comprehensive, get_comprehensive_pick
from enforce_comprehensive_analysis import validate_pick_for_ui, add_pick_to_ui

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

def process_race_comprehensive(race):
    """
    Process a single race using comprehensive analysis
    Returns pick dict if suitable horse found, None otherwise
    """
    venue = race.get('venue', 'Unknown')
    race_time = race.get('start_time', '')
    race_name = race.get('market_name', 'Unknown Race')
    runners = race.get('runners', [])
    
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
    }, course_stats)
    
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
    
    approved_picks = []
    rejected_count = 0
    skipped_too_close = 0
    
    # Process each race
    for race in races:
        pick = process_race_comprehensive(race)
        
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
