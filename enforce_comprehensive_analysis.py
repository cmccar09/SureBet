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
    # Check if comprehensive score exists
    if 'comprehensive_score' not in pick_data:
        return False, 0, "Missing comprehensive score - REJECTED"
    
    score = pick_data['comprehensive_score']
    
    # Minimum threshold: 60/100
    if score < 60:
        return False, score, f"Score too low ({score}/100) - minimum 60 required"
    
    # Check required fields
    required = ['odds', 'form', 'reasoning', 'score_breakdown']
    missing = [f for f in required if f not in pick_data]
    if missing:
        return False, score, f"Missing fields: {missing}"
    
    return True, score, "APPROVED for UI"

def add_pick_to_ui(pick_data, race_data):
    """
    Add a pick to the UI ONLY if it passes comprehensive analysis
    """
    # Validate comprehensive analysis
    is_valid, score, reason = validate_pick_for_ui(pick_data)
    
    if not is_valid:
        print(f"❌ REJECTED: {pick_data.get('horse', 'Unknown')}")
        print(f"   Reason: {reason}")
        return False
    
    # Add to database with show_in_ui=True
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('SureBetBets')
    
    today = datetime.now().strftime('%Y-%m-%d')
    race_time = race_data['race_time']
    horse = pick_data['horse']
    
    bet_id = f"{race_time}_{race_data['course']}_{horse}"
    
    item = {
        'bet_date': today,
        'bet_id': bet_id,
        'race_time': race_time,
        'horse': horse,
        'course': race_data['course'],
        'odds': Decimal(str(pick_data['odds'])),
        'form': pick_data.get('form', ''),
        'trainer': pick_data.get('trainer', ''),
        'race_name': race_data.get('race_name', ''),
        'stake': Decimal('6.0'),
        'bet_type': 'WIN',
        'outcome': 'pending',
        'show_in_ui': True,
        
        # Comprehensive analysis data
        'comprehensive_score': Decimal(str(score)),
        'score_breakdown': pick_data['score_breakdown'],
        'reasoning': pick_data['reasoning'],
        'confidence': pick_data.get('confidence', 'MEDIUM'),
        
        'timestamp': datetime.now().isoformat()
    }
    
    table.put_item(Item=item)
    
    print(f"✅ APPROVED: {horse} @ {pick_data['odds']}")
    print(f"   Score: {score}/100 - {pick_data['confidence']}")
    print(f"   Reasoning: {pick_data['reasoning'][:80]}...")
    
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
        print(f"\n✓ Best pick: {pick['horse']} @ {pick['odds']}")
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
