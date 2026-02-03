"""
COMPREHENSIVE BETTING WORKFLOW
Replaces odds-only analysis with full 7-factor comprehensive analysis

This script:
1. Fetches races from Betfair
2. Analyzes each race using comprehensive_pick_logic.py
3. Only adds picks with score >= 60/100 to database
4. All picks shown on UI must pass comprehensive validation
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
            print(f"\n[APPROVED] {pick['horse']} @ {pick['odds']}")
            print(f"   Score: {score}/100")
            print(f"   Confidence: {pick['confidence']}")
            print(f"   Reasoning: {pick['reasoning'][:100]}...")
            return pick
        else:
            print(f"\n[REJECTED] {pick.get('horse', 'Unknown')}")
            print(f"   {reason}")
            return None
    else:
        print(f"\n[SKIPPED] No horses meet comprehensive criteria")
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
    
    # Fetch upcoming races
    races = fetch_upcoming_races(hours_ahead=6)
    
    if not races:
        print("No upcoming races found in next 6 hours")
        return
    
    print(f"Found {len(races)} upcoming races\n")
    
    approved_picks = []
    rejected_count = 0
    
    # Process each race
    for race in races:
        pick = process_race_comprehensive(race)
        
        if pick:
            # Add to database
            race_data = {
                'course': race.get('venue'),
                'race_time': race.get('start_time'),
                'race_name': race.get('market_name', 'Unknown')
            }
            
            success = add_pick_to_ui(pick, race_data)
            if success:
                approved_picks.append(pick)
        else:
            rejected_count += 1
    
    # Summary
    print("\n" + "="*80)
    print("WORKFLOW COMPLETE")
    print("="*80)
    print(f"Races analyzed: {len(races)}")
    print(f"Picks approved: {len(approved_picks)}")
    print(f"Picks rejected: {rejected_count}")
    
    if approved_picks:
        print(f"\nAPPROVED PICKS (added to UI):")
        for pick in approved_picks:
            print(f"  ✓ {pick['horse']} @ {pick['odds']} - {pick['comprehensive_score']}/100")
    
    print("\n" + "="*80)
    print("✓ All UI picks passed comprehensive analysis")
    print("✓ No odds-only picks allowed")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_comprehensive_workflow()
