import boto3

# Race results for 15:52 Sedgefield
results = {
    'Ballin Bay': 1,
    'Scudamore': 2,
    'Dillarchie': 3,
    'East Eagle': 4,
}

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

response = table.scan()
items = response.get('Items', [])

sedgefield_1552 = [item for item in items if 'Sedgefield' in item.get('course', '') and '15:52' in item.get('race_time', '')]

print(f"\n{'='*70}")
print(f"15:52 SEDGEFIELD RESULTS")
print(f"{'='*70}\n")

updated_count = 0
for horse_item in sedgefield_1552:
    horse_name = horse_item.get('horse')
    
    if horse_name in results:
        position = results[horse_name]
        
        if position == 1:
            outcome = 'WON'
        elif position in [2, 3]:
            outcome = 'PLACED'
        else:
            outcome = 'LOST'
        
        table.update_item(
            Key={
                'bet_date': horse_item['bet_date'],
                'bet_id': horse_item['bet_id']
            },
            UpdateExpression='SET outcome = :outcome, actual_position = :position, actual_result = :result',
            ExpressionAttributeValues={
                ':outcome': outcome,
                ':position': position,
                ':result': f"Position {position}"
            }
        )
        
        score = float(horse_item.get('combined_confidence', 0))
        odds = horse_item.get('odds', 'N/A')
        is_ui = horse_item.get('show_in_ui', False)
        
        status_icon = '🏆' if outcome == 'WON' else '✓' if outcome == 'PLACED' else '✗'
        ui_marker = ' [UI PICK]' if is_ui else ''
        
        print(f"{status_icon} {horse_name:<30} Position {position} - Score: {score:.0f}/100 @{odds}{ui_marker}")
        updated_count += 1

print(f"\n✓ Updated {updated_count} horses\n")

# Show top 5 by score
print(f"{'='*70}")
print(f"TOP 5 HORSES BY SCORE (New Weights)")
print(f"{'='*70}\n")

sedgefield_sorted = sorted(sedgefield_1552, key=lambda x: float(x.get('combined_confidence', 0)), reverse=True)[:5]
for i, horse in enumerate(sedgefield_sorted, 1):
    name = horse.get('horse', 'Unknown')
    score = float(horse.get('combined_confidence', 0))
    odds = horse.get('odds', 'N/A')
    is_ui = horse.get('show_in_ui', False)
    
    # Get position if in results
    position = results.get(name, '?')
    result_str = f"→ {position}" if position != '?' else ''
    
    ui_marker = ' [UI PICK]' if is_ui else ''
    
    print(f"{i}. {name:<30} {score:5.0f}/100 @{odds:<6} {result_str}{ui_marker}")

# Overall summary - now 15 races
print(f"\n{'='*70}")
print(f"TODAY'S PERFORMANCE SUMMARY (15 races completed)")
print(f"{'='*70}\n")

all_items = table.scan().get('Items', [])
completed_races = {}

for item in all_items:
    outcome = item.get('outcome')
    race_time_str = item.get('race_time', '')
    if outcome in ['WON', 'PLACED', 'LOST'] and '2026-02-04' in race_time_str:
        race_key = f"{item.get('course')}_{item.get('race_time')}"
        if race_key not in completed_races:
            completed_races[race_key] = []
        completed_races[race_key].append(item)

wins = 0
places = 0
losses = 0
total_score = 0
wins_85_plus = 0
total_85_plus = 0
ui_wins = 0
ui_total = 0

for race_key, horses in completed_races.items():
    top_tip = sorted(horses, key=lambda x: float(x.get('combined_confidence', 0)), reverse=True)[0]
    outcome = top_tip.get('outcome')
    score = float(top_tip.get('combined_confidence', 0))
    is_ui = top_tip.get('show_in_ui', False)
    
    if outcome == 'WON':
        wins += 1
        places += 1
        if score >= 85:
            wins_85_plus += 1
        if is_ui:
            ui_wins += 1
    elif outcome == 'PLACED':
        places += 1
    else:
        losses += 1
    
    if score >= 85:
        total_85_plus += 1
    
    if is_ui:
        ui_total += 1
    
    total_score += score

total_races = len(completed_races)
if total_races > 0:
    win_rate = (wins / total_races) * 100
    place_rate = (places / total_races) * 100
    avg_score = total_score / total_races
    
    print(f"Races completed: {total_races}")
    print(f"Winners: {wins}/{total_races} ({win_rate:.1f}%)")
    print(f"Places (1st-3rd): {places}/{total_races} ({place_rate:.1f}%)")
    print(f"Losses: {losses}/{total_races}")
    print(f"Average score: {avg_score:.1f}/100")
    
    if total_85_plus > 0:
        win_rate_85_plus = (wins_85_plus / total_85_plus) * 100
        print(f"\n85+ scorers (EXCELLENT): {wins_85_plus}/{total_85_plus} wins ({win_rate_85_plus:.1f}%)")
    
    if ui_total > 0:
        ui_win_rate = (ui_wins / ui_total) * 100
        print(f"UI picks: {ui_wins}/{ui_total} wins ({ui_win_rate:.1f}%)")
    
    print(f"\nSystem calibration: ", end='')
    if 30 <= win_rate <= 40:
        print("✓ PERFECT - Hitting GOOD tier targets (30-40% win rate)")
    elif win_rate >= 25:
        print("✓ GOOD - Within acceptable range")
    elif win_rate >= 20:
        print("⚠ FAIR - Below target but improving")
    else:
        print(f"⚠ POOR - {win_rate:.1f}% win rate")

print(f"\n{'='*70}\n")
