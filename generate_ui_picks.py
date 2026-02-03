"""
Generate UI picks with comprehensive scoring
Simple, direct approach - no complex workflows
"""

import json
import boto3
from datetime import datetime
from decimal import Decimal

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

def score_horse(horse, race):
    """Simple but effective scoring"""
    odds = horse.get('odds', 0)
    form = horse.get('form', '')
    
    # Sweet spot check (3-9 odds)
    if not (3.0 <= odds <= 9.0):
        return 0, []
    
    score = 0
    reasons = []
    
    # Base sweet spot points
    score += 30
    reasons.append(f"Sweet spot odds ({odds})")
    
    # Form scoring
    if '1' in form[:2]:  # Win in last 2 races
        score += 25
        reasons.append("Recent win")
    elif '1' in form:  # Win anywhere
        score += 15
        reasons.append("Has won before")
    
    # Place scoring
    places = form.count('2') + form.count('3')
    if places >= 2:
        score += 15
        reasons.append(f"{places} place finishes")
    elif places == 1:
        score += 8
    
    # Consistency
    if len(form) >= 5 and form.count('0') == 0 and form.count('P') == 0:
        score += 10
        reasons.append("Consistent performer")
    
    # Optimal odds range
    if 4.0 <= odds <= 6.0:
        score += 15
        reasons.append("Optimal odds range")
    elif 3.0 <= odds <= 7.0:
        score += 10
    
    return score, reasons

def generate_ui_picks():
    """Generate picks that should appear on UI (score >= 75)"""
    
    try:
        with open('response_horses.json', 'r') as f:
            data = json.load(f)
    except:
        print("No race data found")
        return
    
    races = data.get('races', [])
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n{'='*100}")
    print(f"GENERATING UI PICKS - Comprehensive Scoring")
    print(f"{'='*100}\n")
    
    all_picks = []
    
    for race in races:
        venue = race.get('venue', race.get('course', 'Unknown'))
        race_time = race.get('start_time', 'Unknown')
        market_name = race.get('market_name', race.get('marketName', 'Unknown'))
        runners = race.get('runners', [])
        
        best_score = 0
        best_horse = None
        best_reasons = []
        
        for runner in runners:
            score, reasons = score_horse(runner, race)
            
            if score > best_score:
                best_score = score
                best_horse = runner
                best_reasons = reasons
        
        if best_score >= 75:  # UI threshold
            horse_name = best_horse.get('name', best_horse.get('runnerName', 'Unknown'))
            odds = best_horse.get('odds', 0)
            form = best_horse.get('form', '')
            
            # Create pick for database
            bet_id = f"{race_time}_{venue}_{horse_name}".replace(' ', '_').replace(':', '')
            
            # Calculate UI fields
            # ROI estimation: (implied_prob - market_prob) * potential_return
            market_prob = 1 / odds if odds > 0 else 0
            implied_prob = best_score / 100.0  # Our confidence as probability
            edge = max(0, implied_prob - market_prob)
            expected_roi = edge * (odds - 1) if edge > 0 else 0.05
            
            pick = {
                'bet_id': bet_id,
                'bet_date': today,
                'horse': horse_name,
                'course': venue,
                'race_time': race_time,
                'odds': Decimal(str(odds)),
                'form': form,
                'sport': 'Horse Racing',
                'race_type': market_name,
                
                # Scoring - UI expects combined_confidence
                'confidence': Decimal(str(best_score)),
                'combined_confidence': Decimal(str(best_score)),  # UI reads this field
                'confidence_level': 'VERY_HIGH' if best_score >= 90 else 'HIGH',
                'comprehensive_score': Decimal(str(best_score)),
                'analysis_method': 'COMPREHENSIVE',
                
                # ROI fields for UI
                'roi': Decimal(str(round(expected_roi, 4))),  # UI reads this for ROI %
                'expected_roi': Decimal(str(round(expected_roi, 4))),
                'edge_percentage': Decimal(str(round(edge * 100, 2))),
                
                # UI flag
                'show_in_ui': True,
                
                # Details
                'reasoning': f"Score: {best_score}/100 - " + ", ".join(best_reasons[:3]),
                'why_selected': best_reasons,
                'trainer': best_horse.get('trainer', 'Unknown'),
                'selection_id': str(best_horse.get('selectionId', '')),
                
                'created_at': datetime.now().isoformat(),
                'source': 'comprehensive_scoring'
            }
            
            all_picks.append(pick)
            
            print(f"\n✓ HIGH CONFIDENCE PICK")
            print(f"  {venue} - {race_time}")
            print(f"  {horse_name} @ {odds}")
            print(f"  Score: {best_score}/100")
            print(f"  Form: {form}")
            print(f"  ROI: {expected_roi*100:.1f}% | Edge: {edge*100:.1f}%")
            print(f"  Reasons: {', '.join(best_reasons)}")
    
    # Save to database
    if all_picks:
        print(f"\n{'='*100}")
        print(f"SAVING {len(all_picks)} PICKS TO DATABASE")
        print(f"{'='*100}\n")
        
        for pick in all_picks:
            table.put_item(Item=pick)
            print(f"  ✓ Saved: {pick['horse']} @ {pick['course']}")
        
        print(f"\n✓ All picks saved with show_in_ui=TRUE")
        print(f"✓ These will now appear on the UI")
    else:
        print(f"\n❌ No horses scored >= 75")
        print("   No UI picks generated")
    
    print(f"\n{'='*100}\n")
    return all_picks

if __name__ == "__main__":
    generate_ui_picks()
