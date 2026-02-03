"""
Generate UI picks with comprehensive scoring
Includes weather-based going inference + horse going suitability
"""

import json
import boto3
from datetime import datetime
from decimal import Decimal
from weather_going_inference import check_all_tracks_going
from horse_going_performance import get_going_suitability_bonus

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

def score_horse(horse, race, going_adjustment=0, going_info=None):
    """Conservative scoring - max ~50 for exceptional horses + going adjustment + horse suitability
    
    Updated Feb 3: Added quality favorite exception based on Its Top/Dunsy Rock analysis
    """
    odds = horse.get('odds', 0)
    form = horse.get('form', '')
    
    score = 0
    reasons = []
    
    # Quality favorite exception (NEW - based on today's winners)
    # Favorites (1.5-3.0) with exceptional form can score
    is_quality_favorite = False
    if 1.5 <= odds < 3.0:
        # Check for quality indicators
        lto_winner = form and form[0] == '1'  # Last time out winner
        places_count = sum(1 for c in form[:6] if c.isdigit() and 1 <= int(c) <= 3)
        wins_count = form[:6].count('1')
        
        # Quality criteria: LTO winner OR (2+ wins AND 3+ places in last 6)
        if lto_winner or (wins_count >= 2 and places_count >= 3):
            is_quality_favorite = True
            score += 20  # Increased bonus for quality favorite (was 10)
            reasons.append(f"Quality favorite ({odds})")
            if lto_winner:
                reasons.append("LTO winner")
    
    # Sweet spot check (3-9 odds) OR quality favorite
    if not (3.0 <= odds <= 9.0 or is_quality_favorite):
        return 0, []
    
    # Base sweet spot points (only for 3-9 odds, favorites already scored)
    if 3.0 <= odds <= 9.0:
        score += 15
        reasons.append(f"Sweet spot odds ({odds})")
    
    # Form scoring
    if '1' in form[:2]:  # Win in last 2 races
        score += 12
        reasons.append("Recent win")
    elif '1' in form:  # Win anywhere
        score += 6
        reasons.append("Has won before")
    
    # Place scoring
    places = form.count('2') + form.count('3')
    if places >= 2:
        score += 8
        reasons.append(f"{places} place finishes")
    elif places == 1:
        score += 4
    
    # Consistency
    if len(form) >= 5 and form.count('0') == 0 and form.count('P') == 0:
        score += 5
        reasons.append("Consistent performer")
    
    # Optimal odds range
    if 4.0 <= odds <= 6.0:
        score += 10
        reasons.append("Optimal odds range")
    elif 3.0 <= odds <= 7.0:
        score += 5
    
    # WEATHER-BASED GOING ADJUSTMENT
    # Track going adjustment
    if going_adjustment != 0:
        score += going_adjustment
        if going_adjustment > 0:
            reasons.append(f"Good ground (+{going_adjustment})")
        else:
            reasons.append(f"Soft ground ({going_adjustment})")
    
    # Horse suitability to going conditions
    if going_info:
        suitability_adj, suitability_reason = get_going_suitability_bonus(horse, going_info)
        if suitability_adj != 0:
            score += suitability_adj
            reasons.append(suitability_reason)
    
    return score, reasons

def generate_ui_picks():
    """Generate picks that should appear on UI (score >= 45) with weather-based going adjustments"""
    
    try:
        with open('response_horses.json', 'r') as f:
            data = json.load(f)
    except:
        print("No race data found")
        return
    
    races = data.get('races', [])
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n{'='*100}")
    print(f"GENERATING UI PICKS - Comprehensive Scoring with Weather-Based Going")
    print(f"{'='*100}\n")
    
    # Fetch weather/going data once for all tracks
    print("Checking weather and ground conditions...")
    going_data = check_all_tracks_going()
    print()
    
    all_picks = []
    
    for race in races:
        venue = race.get('venue', race.get('course', 'Unknown'))
        race_time = race.get('start_time', 'Unknown')
        market_name = race.get('market_name', race.get('marketName', 'Unknown'))
        runners = race.get('runners', [])
        
        # Get going adjustment for this track
        track_going = going_data.get(venue, {})
        going_adjustment = track_going.get('adjustment', 0)
        going_description = track_going.get('going', 'Unknown')
        
        best_score = 0
        best_horse = None
        best_reasons = []
        
        for runner in runners:
            score, reasons = score_horse(runner, race, going_adjustment, track_going)
            
            if score > best_score:
                best_score = score
                best_horse = runner
                best_reasons = reasons
        
        if best_score >= 45:  # UI threshold - raised to limit to 7-10 picks per day
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
            print(f"  {venue} - {race_time} | Going: {going_description}")
            print(f"  {horse_name} @ {odds}")
            print(f"  Score: {best_score}/100 (adjustment: {going_adjustment:+d})")
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
