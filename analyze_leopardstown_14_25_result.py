import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Race result
race_result = {
    'venue': 'Leopardstown',
    'race_time': '14:25',
    'going': 'Heavy',
    'runners': 21,
    'date': '2026-02-02',
    'top_5': [
        {'position': 1, 'horse': 'Saint Le Fort', 'odds': '10/1', 'jockey': 'Niall Moore', 'trainer': 'Philip Fenton'},
        {'position': 2, 'horse': 'Savante', 'odds': '18/1', 'jockey': 'C. M. Hogan', 'trainer': 'Colm A. Murphy'},
        {'position': 3, 'horse': "He Can't Dance", 'odds': '7/1', 'jockey': 'Danny Gilligan', 'trainer': 'Gordon Elliott'},
        {'position': 4, 'horse': 'Barra Rua', 'odds': '12/1', 'jockey': 'Sean Bowen', 'trainer': 'Emmet Mullins'},
        {'position': 5, 'horse': 'Dippedinmoonlight', 'odds': '15/2', 'jockey': 'M. J. Kenneally', 'trainer': 'Emmet Mullins'},
    ]
}

# Query for our pre-race analyses
response = table.scan(
    FilterExpression='venue = :venue AND contains(race_time, :time) AND analysis_type = :atype',
    ExpressionAttributeValues={
        ':venue': 'Leopardstown',
        ':time': '14:25',
        ':atype': 'PRE_RACE_COMPLETE'
    }
)

analyses = response['Items']

print(f'\nLEOPARDSTOWN 14:25 RACE RESULT ANALYSIS')
print('='*100)
print(f'Going: {race_result["going"]}')
print(f'Runners: {race_result["runners"]}')
print(f'Horses analyzed pre-race: {len(analyses)}\n')

# Analyze each placed horse
print('TOP 5 FINISHERS - OUR PRE-RACE ANALYSIS:')
print('='*100)

winner_analysis = None

for result in race_result['top_5']:
    horse_name = result['horse']
    actual_odds = result['odds']
    position = result['position']
    
    # Find our pre-race analysis
    horse_analysis = None
    for analysis in analyses:
        if analysis.get('horse', '').strip().lower() == horse_name.strip().lower():
            horse_analysis = analysis
            break
    
    print(f'\n{position}. {horse_name} - SP: {actual_odds}')
    
    if horse_analysis:
        print(f'   ✓ WE ANALYZED THIS HORSE')
        print(f'   Pre-race odds: {horse_analysis.get("odds", "N/A")}')
        print(f'   Form: {horse_analysis.get("form", "N/A")}')
        print(f'   Odds category: {horse_analysis.get("odds_category", "N/A")}')
        print(f'   LTO winner: {horse_analysis.get("lto_winner", False)}')
        print(f'   Win in last 3: {horse_analysis.get("win_in_last_3", False)}')
        print(f'   Recent wins: {horse_analysis.get("recent_wins", 0)}')
        print(f'   Edge %: {horse_analysis.get("edge_percentage", "N/A")}')
        
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
    winner_edge = float(winner_analysis.get('edge_percentage', 0))
    
    print(f'\n1. WINNER PROFILE: {race_result["top_5"][0]["horse"]}')
    print(f'   Odds: {winner_odds_str} ({winner_category})')
    print(f'   Form: {winner_form}')
    print(f'   LTO winner: {winner_lto}')
    print(f'   Edge: {winner_edge}%')
    
    if winner_category == 'SWEET_SPOT':
        print(f'   → Winner was in SWEET SPOT range (3-9)')
    elif winner_category == 'OUTSIDER':
        print(f'   → Winner was OUTSIDER (9-15)')
    elif winner_category == 'LONGSHOT':
        print(f'   → LONGSHOT winner (>15) - upset result')
    
    if winner_lto:
        print(f'   → LTO winner = backed up last win')
    
    if winner_edge > 0:
        print(f'   → Positive edge detected pre-race')

# Check if we would have picked the winner with current criteria
print(f'\n2. WOULD WE HAVE PICKED THE WINNER?')
if winner_analysis:
    # Simple evaluation
    edge = float(winner_analysis.get('edge_percentage', 0))
    odds_val = float(winner_analysis.get('odds', 0))
    form_str = winner_analysis.get('form', '')
    
    reasons_no = []
    if edge < 0:
        reasons_no.append(f'Negative edge ({edge}%)')
    if odds_val > 15:
        reasons_no.append(f'Odds too high ({odds_val})')
    if odds_val < 3:
        reasons_no.append(f'Odds too short ({odds_val})')
    if not form_str or form_str == 'Unknown':
        reasons_no.append('No form data')
    if not winner_analysis.get('lto_winner') and not winner_analysis.get('win_in_last_3'):
        reasons_no.append('No recent win')
    
    would_pick = len(reasons_no) == 0
    print(f'   Current criteria result: {"YES ✓" if would_pick else "NO ✗"}')
    
    if not would_pick:
        print(f'   Reasons for rejection:')
        for reason in reasons_no:
            print(f'     - {reason}')

# All horses sorted by odds
print(f'\n\n{"="*100}')
print('ALL HORSES ANALYZED (sorted by odds):')
print('='*100)

sorted_analyses = sorted(analyses, key=lambda x: float(x.get('odds', 999)))

for idx, analysis in enumerate(sorted_analyses[:20], 1):
    horse = analysis.get('horse', 'Unknown')
    odds = analysis.get('odds', 'N/A')
    form = analysis.get('form', 'N/A')
    category = analysis.get('odds_category', 'N/A')
    
    # Check if placed
    placed_pos = None
    for result in race_result['top_5']:
        if result['horse'].lower() == horse.lower():
            placed_pos = result['position']
            break
    
    placed_marker = ''
    if placed_pos == 1:
        placed_marker = '*** WINNER ***'
    elif placed_pos == 2:
        placed_marker = '** 2ND **'
    elif placed_pos == 3:
        placed_marker = '** 3RD **'
    elif placed_pos:
        placed_marker = f'** {placed_pos}TH **'
    
    print(f'{idx:2}. {horse:35} | Odds: {str(odds):8} | Form: {str(form):12} | {category:12} {placed_marker}')

print('\n')

# Save learning to database
learning_entry = {
    'bet_id': f'LEARNING_2026-02-02_LEOPARDSTOWN_1425',
    'bet_date': '2026-02-02',
    'analysis_type': 'RACE_RESULT_LEARNING',
    'venue': 'Leopardstown',
    'race_time': '14:25',
    'going': 'Heavy',
    'runners': 21,
    'winner': race_result['top_5'][0]['horse'],
    'winner_odds': race_result['top_5'][0]['odds'],
    'winner_category': winner_analysis.get('odds_category', 'Unknown') if winner_analysis else 'Unknown',
    'winner_lto': winner_analysis.get('lto_winner', False) if winner_analysis else False,
    'winner_form': winner_analysis.get('form', 'Unknown') if winner_analysis else 'Unknown',
    'second': race_result['top_5'][1]['horse'],
    'third': race_result['top_5'][2]['horse'],
    'created_at': datetime.now().isoformat(),
    'horses_analyzed': len(analyses),
    'status': 'LEARNED'
}

try:
    table.put_item(Item=learning_entry)
    print(f'✓ Learning saved to database: LEARNING_2026-02-02_LEOPARDSTOWN_1425\n')
except Exception as e:
    print(f'✗ Error saving learning: {str(e)}\n')
