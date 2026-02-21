"""
BETTING WORKFLOW - COMPREHENSIVE ANALYSIS REQUIRED
This script ensures ALL picks use comprehensive analysis before being added to UI

Rule: NO picks go to UI without comprehensive scoring (minimum 60/100)
"""

import json
import boto3
from datetime import datetime
from decimal import Decimal
from comprehensive_pick_logic import analyze_horse_comprehensive, get_comprehensive_pick

def validate_pick_for_ui(pick_data):
    """
    Validate that a pick meets comprehensive analysis standards
    Returns: (is_valid, score, reasoning)
    """
    # Check if comprehensive score exists (accept both 'score' and 'comprehensive_score')
    score = pick_data.get('comprehensive_score') or pick_data.get('score')
    if score is None:
        return False, 0, "Missing comprehensive score - REJECTED"
    
    # Minimum threshold: 60/100
    if score < 60:
        return False, score, f"Score too low ({score}/100) - minimum 60 required"
    
    # Check required fields (accept different naming conventions)
    horse_data = pick_data.get('horse', pick_data)
    if not horse_data.get('odds') and not horse_data.get('name'):
        return False, score, "Missing horse data"
    
    return True, score, "APPROVED for UI"

def add_pick_to_ui(pick_data, race_data):
    """
    Add a pick to the UI ONLY if it passes comprehensive analysis
    """
    # Validate comprehensive analysis
    is_valid, score, reason = validate_pick_for_ui(pick_data)
    
    if not is_valid:
        horse_name = pick_data.get('horse', {}).get('name', 'Unknown') if isinstance(pick_data.get('horse'), dict) else str(pick_data.get('horse', 'Unknown'))
        print(f"- REJECTED: {horse_name}")
        print(f"   Reason: {reason}")
        return False
    
    # Add to database with show_in_ui=True
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('SureBetBets')
    
    today = datetime.now().strftime('%Y-%m-%d')
    race_time = race_data['race_time']
    
    # Extract horse data
    horse_data = pick_data.get('horse', {})
    horse_name = horse_data.get('name', '') if isinstance(horse_data, dict) else str(horse_data)
    odds = horse_data.get('odds', 0) if isinstance(horse_data, dict) else pick_data.get('odds', 0)
    form = horse_data.get('form', '') if isinstance(horse_data, dict) else pick_data.get('form', '')
    trainer = horse_data.get('trainer', '') if isinstance(horse_data, dict) else pick_data.get('trainer', '')
    selection_id = horse_data.get('selectionId', '') if isinstance(horse_data, dict) else pick_data.get('selectionId', '')
    
    bet_id = f"{race_time}_{race_data['course']}_{horse_name}".replace(' ', '_')
    
    # Get reasoning
    reasons = pick_data.get('reasons', [])
    reasoning = ", ".join(reasons[:3]) if reasons else pick_data.get('reasoning', 'Comprehensive analysis')
    
    # Determine confidence
    if score >= 90:
        confidence = "VERY_HIGH"
    elif score >= 75:
        confidence = "HIGH"
    elif score >= 60:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    
    # Get coverage from pick data
    coverage = pick_data.get('coverage', 100)  # Default to 100% if not provided
    total_runners = pick_data.get('total_runners', 0)
    analyzed_runners = pick_data.get('analyzed_runners', 0)
    
    # Get market_id for results fetching
    market_id = race_data.get('market_id', '')
    
    item = {
        'bet_date': today,
        'bet_id': bet_id,
        'race_time': race_time,
        'horse': horse_name,
        'course': race_data['course'],
        'odds': Decimal(str(odds)),
        'form': form,
        'trainer': trainer,
        'selection_id': str(selection_id),
        'market_id': str(market_id),  # For Betfair results API
        'race_name': race_data.get('race_name', ''),
        'stake': Decimal('6.0'),
        'bet_type': 'WIN',
        'outcome': 'pending',
        'show_in_ui': (score >= 85),  # ONLY show recommended bets (85+) on UI
        'recommended_bet': (score >= 85),
        
        # Comprehensive analysis data
        'comprehensive_score': Decimal(str(score)),
        'combined_confidence': Decimal(str(score)),  # For UI compatibility
        'score_breakdown': pick_data.get('breakdown', {}),
        'reasoning': reasoning,
        'confidence': confidence,
        'analysis_method': 'COMPREHENSIVE',
        
        # Coverage metrics - MULTIPLE FIELD NAMES FOR UI COMPATIBILITY
        # Frontend may use any of these field names
        'coverage': Decimal(str(coverage)),
        'data_coverage': Decimal(str(coverage)),
        'race_coverage_pct': Decimal(str(coverage)),  # Legacy UI field name
        'total_runners': total_runners,
        'analyzed_runners': analyzed_runners,
        
        'timestamp': datetime.now().isoformat()
    }
    
    table.put_item(Item=item)
    
    print(f"+ APPROVED: {horse_name} @ {odds}")
    print(f"   Score: {score}/100 - {confidence}")
    print(f"   Reasoning: {reasoning[:80]}...")
    
    return True

def analyze_race_comprehensive(race_data):
    """
    Analyze a race using comprehensive logic
    Returns best pick or None if no suitable horses
    """
    course = race_data.get('course', 'Unknown')
    runners = race_data.get('runners', [])
    
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE ANALYSIS: {race_data.get('race_time')} - {race_data.get('race_name')}")
    print(f"Course: {course}")
    print(f"{'='*80}\n")
    
    # Get comprehensive pick
    pick = get_comprehensive_pick(race_data, course_stats={'avg_winner_odds': 4.75})
    
    if pick:
        print(f"\n+ Best pick: {pick['horse']} @ {pick['odds']}")
        print(f"  Score: {pick['comprehensive_score']}/100")
        print(f"  Confidence: {pick['confidence']}")
        return pick
    else:
        print("\n✗ No suitable picks (all scores below threshold)")
        return None

if __name__ == "__main__":
    print("\n" + "="*80)
    print("BETTING WORKFLOW - COMPREHENSIVE ANALYSIS ENFORCEMENT")
    print("="*80)
    print("\nRule: ALL UI picks must score 60+ using comprehensive analysis")
    print("Factors: Sweet spot + Odds + Form + Wins + Consistency + Course + History")
    print("\nThis prevents picks based on odds alone (tonight's 0/2 mistake)")
    print("="*80 + "\n")
