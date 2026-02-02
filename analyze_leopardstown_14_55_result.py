import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Race result
race_result = {
    'venue': 'Leopardstown',
    'race_time': '14:55',
    'race_name': 'Irish Arkle Chase',
    'going': 'Soft',
    'runners': 3,
    'date': '2026-02-02',
    'top_3': [
        {'position': 1, 'horse': 'Romeo Coolio', 'odds': '4/9', 'jockey': 'J. W. Kennedy', 'trainer': 'Gordon Elliott'},
        {'position': 2, 'horse': 'Kargese', 'odds': '2/1', 'jockey': 'P. Townend', 'trainer': 'W. P. Mullins'},
        {'position': 3, 'horse': 'Downmexicoway', 'odds': 'Unknown', 'jockey': "D. J. O'Keeffe", 'trainer': 'Henry de Bromhead'},
    ]
}

# Query for our pre-race analyses
response = table.scan(
    FilterExpression='venue = :venue AND contains(race_time, :time) AND analysis_type = :atype',
    ExpressionAttributeValues={
        ':venue': 'Leopardstown',
        ':time': '14:55',
        ':atype': 'PRE_RACE_COMPLETE'
    }
)

analyses = response['Items']

print(f'\nLEOPARDSTOWN 14:55 - IRISH ARKLE CHASE RESULT ANALYSIS')
print('='*100)
print(f'Race: {race_result["race_name"]}')
print(f'Going: {race_result["going"]}')
print(f'Runners: {race_result["runners"]} (SMALL FIELD)')
print(f'Horses analyzed pre-race: {len(analyses)}\n')

# Analyze each placed horse
print('FINISHING ORDER - OUR PRE-RACE ANALYSIS:')
print('='*100)

winner_analysis = None

for result in race_result['top_3']:
    horse_name = result['horse']
    actual_odds = result['odds']
    position = result['position']
    
    # Find our pre-race analysis
    horse_analysis = None
    for analysis in analyses:
        analyzed_name = analysis.get('horse', '').strip().lower()
        result_name = horse_name.strip().lower()
        
        # Handle name variations
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
    
    print(f'\n1. WINNER PROFILE: {race_result["top_3"][0]["horse"]}')
    print(f'   Odds: {winner_odds_str} ({winner_category})')
    print(f'   SP: {race_result["top_3"][0]["odds"]} = HEAVY FAVORITE')
    print(f'   Form: {winner_form}')
    print(f'   LTO winner: {winner_lto}')
    print(f'   Recent wins: {winner_recent_wins}')
    print(f'   Trainer: Gordon Elliott (TOP TRAINER)')
    
    # Convert 4/9 to decimal
    odds_decimal = 1 + (4/9)  # = 1.44
    
    if odds_decimal < 2.0:
        print(f'   → Heavy favorite (odds < 2.0) - VERY SHORT PRICE')
        print(f'   → Only 3 runners = limited competition')
    
    if winner_lto:
        print(f'   → LTO winner = followed up previous win')
    
    print(f'\n2. SMALL FIELD RACE (3 runners):')
    print(f'   → Favorite dominance expected')
    print(f'   → Less value opportunities')
    print(f'   → Quality over quantity')

# Check if we would have picked the winner
print(f'\n3. WOULD WE HAVE PICKED THE WINNER?')
if winner_analysis:
    odds_val = float(winner_analysis.get('odds', 0))
    form_str = winner_analysis.get('form', '')
    
    print(f'   Odds: {odds_val} (4/9 = 1.44)')
    
    if odds_val < 3.0:
        print(f'   → NO - Odds too short (below our 3.0 minimum)')
        print(f'   → Heavy favorites rarely offer value')
        print(f'   → Correct decision - even though it won')
    
    print(f'\n4. VALUE ASSESSMENT:')
    print(f'   If bet £10 on Romeo Coolio @ 4/9:')
    print(f'   → Win: £4.44 profit (44% ROI)')
    print(f'   → Risk: £10 for small return')
    print(f'   → Our strategy: Skip heavy favorites, seek value')

# All horses analyzed
print(f'\n\n{"="*100}')
print('ALL HORSES ANALYZED:')
print('='*100)

if analyses:
    for idx, analysis in enumerate(analyses, 1):
        horse = analysis.get('horse', 'Unknown')
        odds = analysis.get('odds', 'N/A')
        form = analysis.get('form', 'N/A')
        category = analysis.get('odds_category', 'N/A')
        
        # Check if placed
        placed_pos = None
        for result in race_result['top_3']:
            result_name = result['horse'].lower()
            analyzed_name = horse.lower()
            if result_name == analyzed_name or result_name in analyzed_name or analyzed_name in result_name:
                placed_pos = result['position']
                break
        
        placed_marker = ''
        if placed_pos == 1:
            placed_marker = '*** WINNER ***'
        elif placed_pos == 2:
            placed_marker = '** 2ND **'
        elif placed_pos == 3:
            placed_marker = '** 3RD **'
        
        print(f'{idx}. {horse:35} | Odds: {str(odds):8} | Form: {str(form):12} | {category:12} {placed_marker}')

print('\n')

# Save learning to database
learning_entry = {
    'bet_id': f'LEARNING_2026-02-02_LEOPARDSTOWN_1455',
    'bet_date': '2026-02-02',
    'analysis_type': 'RACE_RESULT_LEARNING',
    'venue': 'Leopardstown',
    'race_time': '14:55',
    'race_name': 'Irish Arkle Chase',
    'race_type': 'CHASE',
    'going': 'Soft',
    'runners': 3,
    'field_size': 'SMALL',
    'winner': race_result['top_3'][0]['horse'],
    'winner_odds': race_result['top_3'][0]['odds'],
    'winner_odds_decimal': Decimal('1.44'),
    'winner_category': 'FAVORITE',
    'winner_type': 'HEAVY_FAVORITE',
    'winner_lto': winner_analysis.get('lto_winner', False) if winner_analysis else False,
    'winner_form': winner_analysis.get('form', 'Unknown') if winner_analysis else 'Unknown',
    'second': race_result['top_3'][1]['horse'],
    'third': race_result['top_3'][2]['horse'],
    'created_at': datetime.now().isoformat(),
    'horses_analyzed': len(analyses),
    'status': 'LEARNED',
    'key_insight': 'Heavy favorite won small field race - correct to skip (no value)',
    'learning_points': [
        'Small fields (3 runners) = favorites dominate',
        'Heavy favorites (<2.0 odds) win often but offer poor value',
        'Soft going on Chase = quality/class matters most',
        'Gordon Elliott trainer advantage validated'
    ]
}

try:
    table.put_item(Item=learning_entry)
    print(f'✓ Learning saved to database: LEARNING_2026-02-02_LEOPARDSTOWN_1455\n')
except Exception as e:
    print(f'✗ Error saving learning: {str(e)}\n')

# Summary comparison to 14:25
print('='*100)
print('COMPARISON: Leopardstown 14:25 vs 14:55')
print('='*100)
print('\n14:25 (Handicap Hurdle, 21 runners, Heavy):')
print('  Winner: Saint Le Fort @ 10/1 (outsider)')
print('  Pattern: Going ability > Recent form')
print('  Our pick: Would NOT pick (no recent wins)')
print('  Learning: Heavy going = different criteria needed')

print('\n14:55 (Graded Chase, 3 runners, Soft):')
print('  Winner: Romeo Coolio @ 4/9 (heavy favorite)')
print('  Pattern: Favorite dominates small field')
print('  Our pick: Would NOT pick (odds too short)')
print('  Learning: Correct to skip - no value even though won')

print('\n**KEY PATTERN: Different race types need different approaches**')
print('  - Large handicaps on Heavy = outsider value')
print('  - Small graded races on Soft = favorite dominance')
print('='*100)
