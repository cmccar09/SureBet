"""
Generate UI picks from validated database entries
Uses race_analysis_validator to ensure only complete races appear on UI
"""
import boto3
from decimal import Decimal
from datetime import datetime
from race_analysis_validator import get_validated_picks, validate_race_analysis
from weighted_form_analyzer import get_form_adjustment_for_confidence

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("="*80)
print("GENERATING UI PICKS FROM VALIDATED RACES")
print("="*80)

# Get all validated picks
bet_date = '2026-02-03'
validated_picks, validation_report = get_validated_picks(bet_date, min_confidence=0)

print(f"\nFound {len(validated_picks)} horses in validated races")

# Group by race
races = {}
for pick in validated_picks:
    race_key = f"{pick.get('course')}_{pick.get('race_time')}"
    if race_key not in races:
        races[race_key] = []
    races[race_key].append(pick)

print(f"Across {len(races)} races\n")

ui_picks_set = 0
total_processed = 0

for race_key, picks in races.items():
    if not picks:
        continue
    
    sample = picks[0]
    course = sample.get('course', '')
    race_time = sample.get('race_time', '')
    
    # Extract time for validation
    if 'T' in race_time:
        time_str = race_time.split('T')[1].split(':')[0:2]
        time_str = ':'.join(time_str)
    else:
        time_str = race_time
    
    # Validate race
    is_valid, num_analyzed, total_horses, issues = validate_race_analysis(
        course, time_str, bet_date
    )
    
    if not is_valid:
        print(f"[SKIP] {course} {time_str} - Validation failed")
        continue
    
    # Get number of runners for threshold
    num_runners = total_horses
    threshold = 55 if num_runners < 6 else 45
    
    # Find best horse in this race
    best_pick = None
    best_score = 0
    
    for pick in picks:
        try:
            base_conf = float(pick.get('confidence', 0))
        except:
            base_conf = 0
        
        # Apply weighted form adjustment
        form = pick.get('form', '')
        if form:
            form_adj, _ = get_form_adjustment_for_confidence(form)
        else:
            form_adj = 0
        
        adjusted_score = base_conf + form_adj
        
        if adjusted_score > best_score:
            best_score = adjusted_score
            best_pick = pick
            best_pick['adjusted_confidence'] = adjusted_score
            best_pick['form_adjustment'] = form_adj
    
    # Only add to UI if meets threshold
    if best_pick and best_score >= threshold:
        horse = best_pick['data'].get('horse', '')
        bet_id = best_pick['data'].get('bet_id', '')
        
        # Skip if no bet_id (corrupted data)
        if not bet_id or bet_id == '':
            print(f"[SKIP] {course} {time_str} - {horse} has no bet_id")
            continue
        
        # Update to show on UI
        try:
            table.update_item(
                Key={
                    'bet_date': bet_date,
                    'bet_id': bet_id
                },
                UpdateExpression='SET show_in_ui = :true, combined_confidence = :conf, confidence_level = :level, confidence_grade = :grade, confidence_color = :color',
                ExpressionAttributeValues={
                    ':true': True,
                    ':conf': Decimal(str(best_score)),
                    ':level': 'HIGH' if best_score >= 75 else 'MEDIUM' if best_score >= 60 else 'LOW',
                    ':grade': 'EXCELLENT' if best_score >= 75 else 'GOOD' if best_score >= 60 else 'FAIR' if best_score >= 45 else 'POOR',
                    ':color': 'green' if best_score >= 75 else '#FFB84D' if best_score >= 60 else '#FF8C00' if best_score >= 45 else 'red'
                }
            )
            
            print(f"[UI PICK] {course} {time_str}")
            print(f"  {horse}")
            print(f"  Score: {best_score:.0f}/100 (base: {best_pick['data'].get('confidence', 0)}, form adj: {best_pick.get('form_adjustment', 0):+d})")
            print(f"  Threshold: {threshold}/100 ({'small field' if num_runners < 6 else 'normal'})")
            print(f"  Form: {best_pick['data'].get('form', '')}")
            print(f"  Analysis: {num_analyzed}/{num_runners} horses ({num_analyzed/num_runners*100:.0f}%)")
            print()
            
            ui_picks_set += 1
        except Exception as e:
            print(f"  ERROR updating {horse}: {str(e)}")
    else:
        if best_pick:
            print(f"[SKIP] {course} {time_str} - Best score {best_score:.0f} below threshold {threshold}")
    
    total_processed += 1

print("="*80)
print("SUMMARY")
print("="*80)
print(f"Races processed: {total_processed}")
print(f"UI picks set: {ui_picks_set}")
print(f"\nPicks now visible on UI!")
