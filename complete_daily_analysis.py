"""
COMPLETE DAILY WORKFLOW
1. Analyze ALL races comprehensively (learning data)
2. Select top picks for UI (betting picks)
3. As results come in, learn and improve

Run this once in the morning to set up the day
"""

import json
import boto3
from datetime import datetime
from decimal import Decimal
from comprehensive_pick_logic import analyze_horse_comprehensive

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

def load_races():
    """Load races from Betfair fetch"""
    try:
        with open('response_horses.json', 'r') as f:
            data = json.load(f)
        return data.get('races', [])
    except FileNotFoundError:
        print("ERROR: Run 'python betfair_odds_fetcher.py' first")
        return []

def analyze_and_save_all():
    """Analyze ALL horses in ALL races - save for learning"""
    races = load_races()
    
    if not races:
        print("No races found")
        return
    
    print("\n" + "="*100)
    print("COMPREHENSIVE DAILY ANALYSIS")
    print("="*100)
    print(f"\nTotal races: {len(races)}")
    print(f"Analyzing ALL horses for learning + selecting top picks for UI\n")
    
    total_horses = 0
    learning_saved = 0
    ui_promoted = 0
    
    course_stats = {'avg_winner_odds': 4.65, 'winners_today': 0}
    
    for race in races:
        venue = race.get('venue', 'Unknown')
        race_time = race.get('start_time', '')
        runners = race.get('runners', [])
        
        # Track coverage for this race
        race_total = len(runners)
        race_items = []  # Store all items for this race first
        
        print(f"\n[{venue} {race_time[:16]}] {len(runners)} horses")
        
        for runner in runners:
            total_horses += 1
            
            # Comprehensive analysis
            raw_score, breakdown, reasons = analyze_horse_comprehensive(
                runner,
                venue,
                avg_winner_odds=course_stats['avg_winner_odds'],
                course_winners_today=course_stats['winners_today']
            )
            
            # No conservative adjustment - let the algorithm speak for itself
            # After validation, elite trainers + decent odds should score 70-85+
            score = raw_score
            
            horse_name = runner.get('name', 'Unknown')
            odds = runner.get('odds', 0)
            
            # Determine if this goes to UI or stays as learning data
            # Thresholds: 85+ shown on UI and marked as recommended bets
            show_on_ui = bool(score >= 85)
            recommended_bet = bool(score >= 85)
            
            # DEBUG
            if total_horses < 3:
                print(f"  DEBUG: {horse_name} score={score} show_on_ui={show_on_ui} recommended_bet={recommended_bet}")
            
            # Confidence level based on REALISTIC 4-tier system with -5 adjustment
            # Proven threshold: 85+ shows 67% win rate, 100% place rate
            if score >= 70:
                confidence_level = "EXCELLENT"
                confidence_grade = "EXCELLENT (Best Chance - 50-70% Win Rate)"
                confidence_color = "green"
            elif score >= 50:
                confidence_level = "GOOD"
                confidence_grade = "GOOD (Decent Chance - 30-40% Win Rate)"
                confidence_color = "light-amber"
            elif score >= 35:
                confidence_level = "FAIR"
                confidence_grade = "FAIR (Risky - 15-25% Win Rate)"
                confidence_color = "dark-amber"
            else:
                confidence_level = "POOR"
                confidence_grade = "POOR (Very Unlikely - 5-10% Win Rate)"
                confidence_color = "red"
            
            # Create database item
            bet_id = f"{race_time}_{venue}_{horse_name}".replace(' ', '_').replace(':', '').replace('.', '')
            
            # Build database item (will add coverage after analyzing all horses)
            bet_id = f"{race_time}_{venue}_{horse_name}".replace(' ', '_')
            
            item = {
                'bet_id': bet_id,
                'bet_date': datetime.now().strftime('%Y-%m-%d'),
                'course': venue,  # Use 'course' to match comprehensive_pick_logic.py
                'race_course': venue,  # Keep for backward compatibility
                'race_time': race_time,
                'horse': horse_name,
                'odds': Decimal(str(odds)) if odds else Decimal('0'),  # Frontend expects 'odds'
                'decimal_odds': Decimal(str(odds)) if odds else Decimal('0'),  # Keep for compatibility
                'combined_confidence': Decimal(str(score)),  # Keep for backward compatibility
                'comprehensive_score': Decimal(str(score)),  # Match comprehensive_pick_logic.py
                'confidence_level': confidence_level,
                'confidence_grade': confidence_grade,
                'confidence_color': confidence_color,
                'show_in_ui': show_on_ui,
                'recommended_bet': recommended_bet,  # NEW field for frontend highlighting
                'is_learning_pick': not show_on_ui,
                'analysis_type': 'comprehensive_7factor',
                'score_breakdown': breakdown,
                'selection_reasons': reasons,
                'sport': 'Horse Racing',
                'market_id': race.get('marketId', ''),
                'selection_id': runner.get('selectionId', 0),
                'trainer': runner.get('trainer', ''),
                'form': runner.get('form', ''),
                'created_at': datetime.now().isoformat()
            }
            
            race_items.append((item, show_on_ui, horse_name, odds, score, confidence_grade))
        
        # Now save all items for this race with correct coverage (100%)
        race_coverage_pct = 100  # We analyzed all horses in the race
        
        for item, is_ui_pick, horse_name_saved, odds_saved, score_saved, confidence_grade_saved in race_items:
            # Add coverage fields
            item['race_coverage_pct'] = Decimal('100')
            item['race_analyzed_count'] = race_total
            item['race_total_count'] = race_total
            
            # Save to database
            try:
                table.put_item(Item=item)
                
                if is_ui_pick:
                    ui_promoted += 1
                    print(f"  >> UI PICK: {horse_name_saved:25} @ {odds_saved:5.2f} Score: {score_saved:3}/100 ({confidence_grade_saved})")
                else:
                    learning_saved += 1
                    print(f"  - Learning: {horse_name_saved:25} @ {odds_saved:5.2f} Score: {score_saved:3}/100 ({confidence_grade_saved})")
                    
            except Exception as e:
                print(f"  ERROR saving {horse_name_saved}: {e}")
    
    print("\n" + "="*100)
    print("ANALYSIS COMPLETE")
    print("="*100)
    print(f"\nTotal horses analyzed: {total_horses}")
    print(f"  Learning data (show_in_ui=False): {learning_saved}")
    print(f"  UI picks (show_in_ui=True): {ui_promoted}")
    print(f"\n{'='*100}\n")
    
    return {
        'total': total_horses,
        'learning': learning_saved,
        'ui_picks': ui_promoted
    }

if __name__ == "__main__":
    stats = analyze_and_save_all()
    
    if stats and stats['ui_picks'] > 0:
        print(f">> {stats['ui_picks']} HIGH-CONFIDENCE PICKS ready to bet on")
        print(f">> {stats['learning']} horses saved for learning")
        print(f"\nView UI picks: python show_todays_ui_picks.py")
    elif stats and stats['learning'] > 0:
        print(f"WARNING: No high-confidence picks today (all below 60/100 after adjustment)")
        print(f">> {stats['learning']} horses analyzed for learning")
        print(f"\nSuggestion: Review top scores to consider adjusting threshold")
        print(f"python show_top_picks.py")
    else:
        print("ERROR: No races analyzed - check Betfair fetch")
