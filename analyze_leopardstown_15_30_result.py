import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Race result
race_result = {
    'venue': 'Leopardstown',
    'race_time': '15:30',
    'race_name': 'Irish Gold Cup Chase',
    'going': 'Soft',
    'runners': 12,
    'date': '2026-02-02',
    'finishers': [
        {'position': 1, 'horse': 'Fact To File', 'odds': '9/2', 'jockey': 'M. P. Walsh', 'trainer': 'W. P. Mullins'},
        {'position': 2, 'horse': 'Gaelic Warrior', 'odds': '4/1', 'jockey': 'Mr P. W. Mullins', 'trainer': 'W. P. Mullins'},
        {'position': 3, 'horse': 'Galopin Des Champs', 'odds': '15/8', 'jockey': 'P. Townend', 'trainer': 'W. P. Mullins'},
        {'position': 4, 'horse': 'Firefox', 'odds': '33/1', 'jockey': 'Sean Bowen', 'trainer': 'Gordon Elliott'},
        {'position': 5, 'horse': 'I Am Maximus', 'odds': '9/1', 'jockey': 'J. W. Kennedy', 'trainer': 'W. P. Mullins'},
    ]
}

# Query for our pre-race analyses
response = table.scan(
    FilterExpression='venue = :venue AND contains(race_time, :time) AND analysis_type = :atype',
    ExpressionAttributeValues={
        ':venue': 'Leopardstown',
        ':time': '15:30',
        ':atype': 'PRE_RACE_COMPLETE'
    }
)

analyses = response['Items']

print(f'\nLEOPARDSTOWN 15:30 - IRISH GOLD CUP CHASE RESULT ANALYSIS')
print('='*100)
print(f'Race: {race_result["race_name"]} (GRADE 1)')
print(f'Going: {race_result["going"]}')
print(f'Runners: {race_result["runners"]}')
print(f'Horses analyzed pre-race: {len(analyses)}\n')

# Analyze top finishers
print('TOP 5 FINISHERS - OUR PRE-RACE ANALYSIS:')
print('='*100)

winner_analysis = None
favorite_analysis = None

for result in race_result['finishers']:
    horse_name = result['horse']
    actual_odds = result['odds']
    position = result['position']
    
    # Find our pre-race analysis
    horse_analysis = None
    for analysis in analyses:
        analyzed_name = analysis.get('horse', '').strip().lower()
        result_name = horse_name.strip().lower()
        
        if analyzed_name == result_name or \
           analyzed_name.replace(' ', '') == result_name.replace(' ', '') or \
           analyzed_name in result_name or result_name in analyzed_name:
            horse_analysis = analysis
            break
    
    print(f'\n{position}. {horse_name} - SP: {actual_odds}')
    
    if horse_analysis:
        print(f'   ✓ WE ANALYZED THIS HORSE')
        print(f'   Pre-race odds: {horse_analysis.get("odds", "N/A")}')
        print(f'   Form: {horse_analysis.get("form", "N/A")}')
        print(f'   Trainer: {horse_analysis.get("trainer", "N/A")}')
        print(f'   Odds category: {horse_analysis.get("odds_category", "N/A")}')
        print(f'   LTO winner: {horse_analysis.get("lto_winner", False)}')
        print(f'   Win in last 3: {horse_analysis.get("win_in_last_3", False)}')
        print(f'   Recent wins: {horse_analysis.get("recent_wins", 0)}')
        
        if position == 1:
            winner_analysis = horse_analysis
        if position == 3:  # Galopin Des Champs was favorite
            favorite_analysis = horse_analysis
    else:
        print(f'   ✗ NOT IN OUR ANALYSIS')

# Key insights
print(f'\n\n{"="*100}')
print('KEY INSIGHTS:')
print('='*100)

if winner_analysis:
    winner_odds_str = str(winner_analysis.get('odds', 'Unknown'))
    winner_form = winner_analysis.get('form', 'Unknown')
    winner_category = winner_analysis.get('odds_category', 'Unknown')
    winner_lto = winner_analysis.get('lto_winner', False)
    winner_recent_wins = winner_analysis.get('recent_wins', 0)
    
    print(f'\n1. WINNER PROFILE: Fact To File @ 9/2')
    print(f'   Pre-race odds: {winner_odds_str}')
    print(f'   SP: 9/2 = 5.5 (SWEET SPOT!)')
    print(f'   Form: {winner_form}')
    print(f'   LTO winner: {winner_lto}')
    print(f'   Recent wins: {winner_recent_wins}')
    print(f'   Trainer: W. P. Mullins (CHAMPION TRAINER)')
    
    # Convert 9/2 to decimal
    odds_decimal = 1 + (9/2)  # = 5.5
    
    if 3.0 <= odds_decimal <= 9.0:
        print(f'   → IN SWEET SPOT (3-9) ✓')
    
    if winner_lto:
        print(f'   → LTO winner = followed up previous win ✓')

print(f'\n2. FAVORITE PERFORMANCE:')
print(f'   Galopin Des Champs (15/8 favorite) - Finished 3rd')
print(f'   → Favorite FAILED to win')
print(f'   → Market favorite at 1.88 (under 2.0)')

print(f'\n3. MULLINS DOMINANCE:')
print(f'   W. P. Mullins trained: 1st, 2nd, 3rd, 5th, 7th, 8th')
print(f'   → 6 of top 8 finishers!')
print(f'   → Trainer power in Grade 1 races')

print(f'\n4. RACE CHARACTERISTICS:')
print(f'   Grade 1 Chase (highest quality)')
print(f'   Soft going (not extreme but significant)')
print(f'   12 runners (good field size)')
print(f'   → Quality race with value opportunity')

# Check if we would have picked the winner
print(f'\n5. WOULD WE HAVE PICKED THE WINNER?')
if winner_analysis:
    odds_val = float(winner_analysis.get('odds', 0))
    form_str = winner_analysis.get('form', '')
    
    print(f'   Odds: {odds_val} (9/2 = 5.5) - IN SWEET SPOT ✓')
    
    reasons_yes = []
    reasons_no = []
    
    if 3.0 <= odds_val <= 9.0:
        reasons_yes.append('Odds in sweet spot (3-9)')
    
    if winner_lto:
        reasons_yes.append('LTO winner')
    
    if winner_recent_wins > 0:
        reasons_yes.append(f'{winner_recent_wins} recent win(s)')
    
    if not winner_lto and not winner_analysis.get('win_in_last_3'):
        reasons_no.append('No recent win')
    
    if reasons_yes and not reasons_no:
        print(f'   → POSSIBLY YES')
        print(f'   Strong factors:')
        for reason in reasons_yes:
            print(f'     ✓ {reason}')
    elif reasons_no:
        print(f'   → LIKELY NO')
        print(f'   Missing factors:')
        for reason in reasons_no:
            print(f'     ✗ {reason}')

# All horses analyzed
print(f'\n\n{"="*100}')
print('ALL HORSES ANALYZED (showing top finishers):')
print('='*100)

for result in race_result['finishers']:
    horse_name = result['horse']
    position = result['position']
    sp = result['odds']
    
    # Find analysis
    horse_analysis = None
    for analysis in analyses:
        analyzed_name = analysis.get('horse', '').strip().lower()
        result_name = horse_name.strip().lower()
        
        if analyzed_name == result_name or analyzed_name in result_name or result_name in analyzed_name:
            horse_analysis = analysis
            break
    
    if horse_analysis:
        odds = horse_analysis.get('odds', 'N/A')
        form = horse_analysis.get('form', 'N/A')
        
        marker = ''
        if position == 1:
            marker = '*** WINNER (9/2) ***'
        elif position == 2:
            marker = '** 2ND (4/1) **'
        elif position == 3:
            marker = '** 3RD - FAVORITE (15/8) **'
        
        print(f'{position}. {horse_name:30} | SP: {sp:8} | Pre: {str(odds):6} | Form: {str(form):12} {marker}')

print('\n')

# Save learning to database
learning_entry = {
    'bet_id': f'LEARNING_2026-02-02_LEOPARDSTOWN_1530',
    'bet_date': '2026-02-02',
    'analysis_type': 'RACE_RESULT_LEARNING',
    'venue': 'Leopardstown',
    'race_time': '15:30',
    'race_name': 'Irish Gold Cup Chase',
    'race_type': 'GRADE_1_CHASE',
    'going': 'Soft',
    'runners': 12,
    'field_size': 'MEDIUM',
    'winner': race_result['finishers'][0]['horse'],
    'winner_odds': race_result['finishers'][0]['odds'],
    'winner_odds_decimal': Decimal('5.5'),
    'winner_category': 'SWEET_SPOT',
    'winner_lto': winner_analysis.get('lto_winner', False) if winner_analysis else False,
    'winner_form': winner_analysis.get('form', 'Unknown') if winner_analysis else 'Unknown',
    'second': race_result['finishers'][1]['horse'],
    'third': race_result['finishers'][2]['horse'],
    'favorite': 'Galopin Des Champs',
    'favorite_odds': '15/8',
    'favorite_finish': 3,
    'created_at': datetime.now().isoformat(),
    'horses_analyzed': len(analyses),
    'status': 'LEARNED',
    'key_insight': 'Sweet spot winner in Grade 1 - Mullins trained 6 of top 8',
    'learning_points': [
        'Sweet spot odds (9/2 = 5.5) delivered winner in Grade 1',
        'Favorite (15/8) finished 3rd - value in non-favorites',
        'W. P. Mullins dominance: 6 of top 8 finishers',
        'Soft going in Grade 1 = quality horses handle conditions',
        'Grade 1 chases have more predictable patterns than handicaps',
        'Trainer power is significant in top-level races'
    ]
}

try:
    table.put_item(Item=learning_entry)
    print(f'✓ Learning saved to database: LEARNING_2026-02-02_LEOPARDSTOWN_1530\n')
except Exception as e:
    print(f'✗ Error saving learning: {str(e)}\n')

# Pattern summary
print('='*100)
print('PATTERN COMPARISON: Today\'s Races')
print('='*100)

print('\n14:25 (Handicap Hurdle, Heavy, 21 runners):')
print('  Winner: Saint Le Fort @ 10/1 (outsider, no recent wins)')
print('  Pattern: Going ability > form in large handicap')

print('\n14:55 (Graded Chase, Soft, 3 runners):')
print('  Winner: Romeo Coolio @ 4/9 (heavy favorite)')
print('  Pattern: Favorite dominates small graded race')

print('\n15:30 (Grade 1 Chase, Soft, 12 runners):')
print('  Winner: Fact To File @ 9/2 (SWEET SPOT)')
print('  Pattern: Value in sweet spot, Mullins trainer power')
print('  → BEST VALUE OPPORTUNITY OF THE DAY')

print('\n**EMERGING PATTERN:**')
print('  - Handicaps on Heavy = unpredictable, outsider value')
print('  - Small graded races = favorites dominate (avoid)')
print('  - Grade 1 races = sweet spot odds offer value')
print('  - Trainer power (Mullins) = significant in top races')
print('='*100)
