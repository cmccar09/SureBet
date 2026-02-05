import boto3
from collections import defaultdict

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

response = table.scan()
items = response.get('Items', [])

# Get items from 2026-02-03 (bet_date) with race times from 2026-02-04
today_items = [item for item in items 
               if item.get('bet_date') == '2026-02-03' 
               and '2026-02-04' in item.get('race_time', '')]

print(f'Total horses from today (2026-02-04): {len(today_items)}')
print('='*80)

# Group by outcome
outcomes = defaultdict(list)
for item in today_items:
    outcome = item.get('outcome', 'PENDING')
    if not outcome:
        outcome = 'PENDING'
    outcomes[outcome].append(item)

print(f'\nOUTCOME SUMMARY:')
print(f'  WON: {len(outcomes["WON"])} horses')
print(f'  PLACED: {len(outcomes["PLACED"])} horses')
print(f'  LOST: {len(outcomes["LOST"])} horses')
print(f'  PENDING: {len(outcomes["PENDING"])} horses')
print()

# Show all winners
print(f'\n🏆 ALL WINNERS ({len(outcomes["WON"])} total):')
print('='*80)
for item in sorted(outcomes['WON'], key=lambda x: float(x.get('combined_confidence', 0)), reverse=True):
    horse = item.get('horse', 'Unknown')
    course = item.get('course', 'Unknown')
    time = item.get('race_time', '')[:16]
    score = float(item.get('combined_confidence', 0))
    odds = item.get('odds', 'N/A')
    ui_pick = '⭐ UI PICK' if item.get('show_in_ui') == True else ''
    learning = '📚 LEARNING' if item.get('is_learning_pick') == True else ''
    
    print(f'{score:5.1f}/100  {horse:<25} {course:<15} @{odds:<6} {ui_pick}{learning}')

# Show all placed
print(f'\n🥈 ALL PLACED ({len(outcomes["PLACED"])} total):')
print('='*80)
for item in sorted(outcomes['PLACED'], key=lambda x: float(x.get('combined_confidence', 0)), reverse=True)[:15]:
    horse = item.get('horse', 'Unknown')
    course = item.get('course', 'Unknown')
    score = float(item.get('combined_confidence', 0))
    odds = item.get('odds', 'N/A')
    position = item.get('actual_position', '?')
    ui_pick = '⭐ UI PICK' if item.get('show_in_ui') == True else ''
    
    print(f'{score:5.1f}/100  {horse:<25} {course:<15} @{odds:<6} Pos:{position} {ui_pick}')

# Show all losses
print(f'\n❌ ALL LOSSES ({len(outcomes["LOST"])} total):')
print('='*80)
for item in sorted(outcomes['LOST'], key=lambda x: float(x.get('combined_confidence', 0)), reverse=True)[:15]:
    horse = item.get('horse', 'Unknown')
    course = item.get('course', 'Unknown')
    score = float(item.get('combined_confidence', 0))
    odds = item.get('odds', 'N/A')
    position = item.get('actual_position', '?')
    
    print(f'{score:5.1f}/100  {horse:<25} {course:<15} @{odds:<6} Pos:{position}')

# Show learning races performance
learning_items = [item for item in today_items if item.get('is_learning_pick') == True]
print(f'\n📚 LEARNING RACES PERFORMANCE:')
print('='*80)
print(f'Total learning horses: {len(learning_items)}')
if learning_items:
    learning_outcomes = defaultdict(int)
    for item in learning_items:
        outcome = item.get('outcome', 'PENDING') or 'PENDING'
        learning_outcomes[outcome] += 1
    
    print(f'  Wins: {learning_outcomes["WON"]}')
    print(f'  Places: {learning_outcomes["PLACED"]}')
    print(f'  Losses: {learning_outcomes["LOST"]}')
    print(f'  Pending: {learning_outcomes["PENDING"]}')
    
    # Show learning winners
    learning_winners = [item for item in learning_items if item.get('outcome') == 'WON']
    if learning_winners:
        print(f'\n  Learning Winners:')
        for item in learning_winners:
            horse = item.get('horse', 'Unknown')
            course = item.get('course', 'Unknown')
            score = float(item.get('combined_confidence', 0))
            odds = item.get('odds', 'N/A')
            print(f'    {score:5.1f}/100  {horse:<25} {course:<15} @{odds}')

# Show UI picks performance
ui_picks = [item for item in today_items if item.get('show_in_ui') == True]
print(f'\n⭐ UI PICKS PERFORMANCE:')
print('='*80)
print(f'Total UI picks: {len(ui_picks)}')
if ui_picks:
    ui_outcomes = defaultdict(int)
    for item in ui_picks:
        outcome = item.get('outcome', 'PENDING') or 'PENDING'
        ui_outcomes[outcome] += 1
    
    print(f'  Wins: {ui_outcomes["WON"]}')
    print(f'  Places: {ui_outcomes["PLACED"]}')
    print(f'  Losses: {ui_outcomes["LOST"]}')
    print(f'  Pending: {ui_outcomes["PENDING"]}')
    
    completed = ui_outcomes["WON"] + ui_outcomes["PLACED"] + ui_outcomes["LOST"]
    if completed > 0:
        win_rate = (ui_outcomes["WON"] / completed) * 100
        place_rate = ((ui_outcomes["WON"] + ui_outcomes["PLACED"]) / completed) * 100
        print(f'\n  Win Rate: {win_rate:.1f}%')
        print(f'  Place Rate: {place_rate:.1f}%')

# Group by race to see coverage
print(f'\n📊 RACE COVERAGE:')
print('='*80)
races = defaultdict(list)
for item in today_items:
    race_key = f"{item.get('course', 'Unknown')} {item.get('race_time', '')[:16]}"
    races[race_key].append(item)

races_with_results = 0
total_races = 0
for race_key, horses in sorted(races.items()):
    total_races += 1
    has_results = any(h.get('outcome') not in [None, 'PENDING', ''] for h in horses)
    if has_results:
        races_with_results += 1
        outcomes_count = defaultdict(int)
        for h in horses:
            outcome = h.get('outcome', 'PENDING') or 'PENDING'
            outcomes_count[outcome] += 1
        
        print(f'{race_key}: {len(horses)} horses - W:{outcomes_count["WON"]} P:{outcomes_count["PLACED"]} L:{outcomes_count["LOST"]} Pending:{outcomes_count["PENDING"]}')

print(f'\nTotal races: {total_races}')
print(f'Races with results: {races_with_results}')
print(f'Races pending: {total_races - races_with_results}')
