"""
Calculate confidence scores for all horses in database
This adds the missing scoring step to complete the analysis
"""
import boto3
from decimal import Decimal
from datetime import datetime
import json

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

def calculate_confidence_score(horse_data):
    """
    Calculate confidence score based on form, odds, and other factors
    More conservative scoring - 100/100 should be RARE
    """
    score = 30  # Start lower - must EARN confidence
    
    # Form scoring (most important)
    form = str(horse_data.get('form', ''))
    if form and form != 'Unknown':
        # Weight recent runs: Last 50%, 2nd-last 30%, older 20%
        cleaned_form = ''.join(c for c in form if c.isdigit())
        
        if cleaned_form:
            positions = [int(c) for c in cleaned_form[:5]]  # Last 5 runs
            
            # More balanced position scores
            position_scores = {1: 30, 2: 20, 3: 10, 4: 5, 5: 0, 6: -5, 7: -10, 8: -15, 9: -20, 0: -25}
            
            total_weighted = 0
            weights = [0.50, 0.30, 0.15, 0.03, 0.02]  # Heavy weighting on recent
            
            for idx, pos in enumerate(positions):
                if idx < len(weights):
                    pos_score = position_scores.get(pos, -20)
                    total_weighted += pos_score * weights[idx]
            
            score += total_weighted
    else:
        # No form = penalty
        score -= 10
    
    # Odds adjustment (value betting) - smaller impact
    try:
        odds = float(horse_data.get('odds', 0))
        if odds > 0:
            # Favor horses at 3-7 odds (value zone)
            if 3.0 <= odds <= 7.0:
                score += 8
            elif 2.0 <= odds < 3.0:
                score += 5
            elif odds < 2.0:
                score += 3  # Favorites can be over-bet
            elif odds > 15:
                score -= 8  # Long shots less reliable
    except:
        pass
    
    # LTO winner bonus - only if form is decent
    if form and len(form) > 0 and form[0] == '1':
        # Check 2nd last run - if also good, bigger bonus
        if len(cleaned_form) > 1 and cleaned_form[1] in '123':
            score += 12  # Consistent performer
        else:
            score += 8  # Won last time but inconsistent
    
    # Trainer bonus (Paul Nicholls, Willie Mullins, etc.)
    trainer = str(horse_data.get('trainer', '')).lower()
    if any(name in trainer for name in ['nicholls', 'mullins', 'elliott', 'henderson']):
        score += 3
    
    # Recent consistency bonus - check last 3 runs
    if cleaned_form and len(cleaned_form) >= 3:
        last_3 = [int(c) for c in cleaned_form[:3]]
        # All top-3 finishes
        if all(pos <= 3 for pos in last_3):
            score += 10
        # All top-5 finishes
        elif all(pos <= 5 for pos in last_3):
            score += 5
        # Any zeros/unplaced
        elif any(pos == 0 for pos in last_3):
            score -= 8
    
    return round(max(0, min(100, score)))

print("="*80)
print("CALCULATING CONFIDENCE SCORES FOR ALL HORSES")
print("="*80)

# Get all horses for today
bet_date = datetime.now().strftime('%Y-%m-%d')
response = table.query(
    KeyConditionExpression='bet_date = :date',
    ExpressionAttributeValues={':date': bet_date}
)

items = response.get('Items', [])

# Filter to only horses with analysis_type = PRE_RACE_COMPLETE (from comprehensive analyzer)
horses_to_score = [item for item in items if item.get('analysis_type') == 'PRE_RACE_COMPLETE']

print(f"\nFound {len(horses_to_score)} horses to score\n")

# Group by race
races = {}
for item in horses_to_score:
    race_key = f"{item.get('course')}_{item.get('race_time')}"
    if race_key not in races:
        races[race_key] = []
    races[race_key].append(item)

print(f"Across {len(races)} races\n")

scored_count = 0
error_count = 0

for race_key, horses in races.items():
    course, race_time = race_key.split('_', 1)
    
    print(f"{course} {race_time}")
    print(f"  {len(horses)} horses")
    
    for horse in horses:
        horse_name = horse.get('horse', '')
        bet_id = horse.get('bet_id', '')
        
        if not bet_id:
            print(f"    [SKIP] {horse_name} - no bet_id")
            error_count += 1
            continue
        
        # Calculate confidence
        confidence = calculate_confidence_score(horse)
        
        # Update database
        try:
            table.update_item(
                Key={
                    'bet_date': bet_date,
                    'bet_id': bet_id
                },
                UpdateExpression='SET confidence = :conf, combined_confidence = :conf, confidence_level = :level, confidence_grade = :grade, confidence_color = :color',
                ExpressionAttributeValues={
                    ':conf': Decimal(str(confidence)),
                    ':level': 'HIGH' if confidence >= 70 else 'MEDIUM' if confidence >= 55 else 'LOW',
                    ':grade': 'EXCELLENT' if confidence >= 70 else 'GOOD' if confidence >= 55 else 'FAIR' if confidence >= 40 else 'POOR',
                    ':color': 'green' if confidence >= 70 else '#FFB84D' if confidence >= 55 else '#FF8C00' if confidence >= 40 else 'red'
                }
            )
            
            form = horse.get('form', '')
            if confidence >= 45:
                print(f"    {horse_name:25} {confidence:3d}/100  Form: {form}")
            
            scored_count += 1
            
        except Exception as e:
            print(f"    [ERROR] {horse_name}: {str(e)}")
            error_count += 1
    
    print()

print("="*80)
print("SUMMARY")
print("="*80)
print(f"Horses scored: {scored_count}")
print(f"Errors: {error_count}")
print(f"\nAll horses now have confidence scores!")
print("Run set_ui_picks_from_validated.py to update UI with high-scoring horses")
