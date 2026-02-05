import boto3

# Race results for 14:35 Kempton
results = {
    'U S S Constitution': 1,
    'Bullington Bry': 2,
    'Sanditon': 3,
    'Reddeef': 4,
}

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

response = table.scan()
items = response.get('Items', [])

kempton_1435 = [item for item in items if 'Kempton' in item.get('course', '') and '14:35' in item.get('race_time', '')]

print(f"\n{'='*70}")
print(f"14:35 KEMPTON RESULTS UPDATE")
print(f"{'='*70}\n")

updated_count = 0
for horse_item in kempton_1435:
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
        
        status_icon = '🏆' if outcome == 'WON' else '✓' if outcome == 'PLACED' else '✗'
        print(f"{status_icon} {horse_name:<25} Position {position} - Score: {score:.0f}/100 @{odds}")
        updated_count += 1

print(f"\n✓ Updated {updated_count} horses\n")

print(f"{'='*70}")
print(f"MY TIP ANALYSIS")
print(f"{'='*70}\n")

my_tip = sorted(kempton_1435, key=lambda x: float(x.get('combined_confidence', 0)), reverse=True)[0]
tip_name = my_tip.get('horse')
tip_score = float(my_tip.get('combined_confidence', 0))

if tip_name in results:
    tip_position = results[tip_name]
    if tip_position == 1:
        print(f"🎉 MY TIP WON! {tip_name} ({tip_score:.0f}/100)")
    elif tip_position in [2, 3]:
        print(f"✓ MY TIP PLACED: {tip_name} ({tip_score:.0f}/100) came {tip_position}")
        print(f"   Winner: U S S Constitution @ 5/2")
    else:
        print(f"✗ MY TIP LOST: {tip_name} ({tip_score:.0f}/100) came {tip_position}th")
else:
    print(f"✗ MY TIP LOST: {tip_name} ({tip_score:.0f}/100) - not in top 4")
    print(f"   Winner: U S S Constitution @ 5/2 (NOT in my analysis)")
    print(f"   Bullington Bry (my #2 pick) came 2nd ✓")

# Overall summary - now 10 races
print(f"\n{'='*70}")
print(f"TODAY'S PERFORMANCE SUMMARY (10 races completed)")
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
high_score_wins = 0
high_score_total = 0

for race_key, horses in completed_races.items():
    top_tip = sorted(horses, key=lambda x: float(x.get('combined_confidence', 0)), reverse=True)[0]
    outcome = top_tip.get('outcome')
    score = float(top_tip.get('combined_confidence', 0))
    
    if score >= 60:
        high_score_total += 1
        if outcome == 'WON':
            high_score_wins += 1
    
    if outcome == 'WON':
        wins += 1
        places += 1
    elif outcome == 'PLACED':
        places += 1
    else:
        losses += 1
    
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
    
    print(f"\n60+ SCORE PERFORMANCE:")
    if high_score_total > 0:
        print(f"  60+ scorers: {high_score_total} races")
        print(f"  60+ wins: {high_score_wins}/{high_score_total} ({(high_score_wins/high_score_total)*100:.1f}%)")
    
    print(f"\nSystem calibration: ", end='')
    if 30 <= win_rate <= 40:
        print("✓ PERFECT - Hitting GOOD tier targets (30-40% win rate)")
    elif win_rate >= 25:
        print("✓ GOOD - Within acceptable range")
    elif win_rate >= 20:
        print("⚠ FAIR - Below target")
    else:
        print(f"⚠ POOR - {win_rate:.1f}% win rate")

print(f"\n{'='*70}\n")
