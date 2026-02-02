import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Race result
race_result = {
    'venue': 'Kempton',
    'race_time': '14:35',
    'race_class': 'Class 4',
    'going': 'Good to Soft',
    'runners': 10,
    'date': '2026-02-02',
    'finishers': [
        {'position': 1, 'horse': 'Gooloogong', 'odds': '50/1', 'jockey': 'Tom Cannon', 'trainer': 'George Baker'},
        {'position': 2, 'horse': 'Sage Green', 'odds': '14/1', 'jockey': 'James Best', 'trainer': 'Syd Hosie'},
        {'position': 3, 'horse': 'Frontier Prince', 'odds': '3/1', 'jockey': 'Jonathan Burke', 'trainer': "Fergal O'Brien"},
        {'position': 4, 'horse': 'Wild Goose', 'odds': '11/2', 'jockey': 'Tom Bellamy', 'trainer': 'Kim Bailey & Mat Nicholls'},
        {'position': 5, 'horse': 'Swinging London', 'odds': '11/1', 'jockey': 'Ben Jones', 'trainer': 'John Mackie'},
        {'position': 6, 'horse': 'Graecia', 'odds': '6/1', 'jockey': 'Daire McConville', 'trainer': 'Charlie Longsdon'},
        {'position': 7, 'horse': 'Ice In The Veins', 'odds': '7/2', 'jockey': 'Harry Skelton', 'trainer': 'Dan Skelton'},
        {'position': 8, 'horse': 'Filibustering', 'odds': '9/2', 'jockey': "Paul O'Brien", 'trainer': 'Harry Derham'},
        {'position': 9, 'horse': 'Tyson', 'odds': '50/1', 'jockey': 'Liam Harrison', 'trainer': 'Dan Skelton'},
        {'position': 10, 'horse': "Soleil D'arizona", 'odds': 'Unknown', 'jockey': 'Tristan Durrell', 'trainer': 'Dan Skelton'},
    ]
}

# Query for our pre-race analyses
response = table.scan(
    FilterExpression='venue = :venue AND contains(race_time, :time) AND analysis_type = :atype',
    ExpressionAttributeValues={
        ':venue': 'Kempton',
        ':time': '14:3',  # Match 14:35
        ':atype': 'PRE_RACE_COMPLETE'
    }
)

analyses = response['Items']

print(f'\nKEMPTON 14:35 - CLASS 4 RACE RESULT ANALYSIS')
print('='*100)
print(f'Class: {race_result["race_class"]}')
print(f'Going: {race_result["going"]}')
print(f'Runners: {race_result["runners"]}')
print(f'Horses analyzed pre-race: {len(analyses)}\n')

# Analyze winner and placed horses
print('TOP 5 FINISHERS - OUR PRE-RACE ANALYSIS:')
print('='*100)

winner_analysis = None

for result in race_result['finishers'][:5]:
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
    winner_recent_wins = winner_analysis.get('recent_wins', 0)
    
    print(f'\n1. WINNER PROFILE: Gooloogong @ 50/1 (MASSIVE LONGSHOT)')
    print(f'   Pre-race odds: {winner_odds_str}')
    print(f'   Form: {winner_form}')
    print(f'   LTO winner: {winner_lto}')
    print(f'   Recent wins: {winner_recent_wins}')
    print(f'   Edge: {winner_edge}%')
    print(f'   Category: {winner_category}')
    print(f'   → SHOCK RESULT - 50/1 outsider won')
    
    if winner_lto:
        print(f'   → LTO winner backed up last win')
    
    if winner_edge > 0:
        print(f'   → Had positive edge pre-race')
    elif winner_edge < 0:
        print(f'   → Market correctly priced as longshot (negative edge)')

print(f'\n2. FAVORITE PERFORMANCE:')
print(f'   Frontier Prince (3/1 favorite) - Finished 3rd')
print(f'   Wild Goose (11/2 second favorite) - Finished 4th')
print(f'   Ice In The Veins (7/2) - Finished 7th')
print(f'   → TOP 3 FAVORITES ALL FAILED TO WIN')
print(f'   → Market completely wrong on winner')

print(f'\n3. RACE CHARACTERISTICS:')
print(f'   Class 4 (mid-level competitive race)')
print(f'   Good to Soft going (not extreme)')
print(f'   10 runners (good field size)')
print(f'   → Upset more likely in Class 4 vs Graded races')

# Check if we would have picked the winner
print(f'\n4. WOULD WE HAVE PICKED THE WINNER?')
if winner_analysis:
    odds_val = float(winner_analysis.get('odds', 0))
    edge = float(winner_analysis.get('edge_percentage', 0))
    form_str = winner_analysis.get('form', '')
    
    print(f'   Odds: {odds_val} (50/1 = 51.0)')
    print(f'   Edge: {edge}%')
    
    reasons_no = []
    if odds_val > 50:
        reasons_no.append(f'Odds too high ({odds_val} > 50 maximum)')
    if edge < 0:
        reasons_no.append(f'Negative edge ({edge}%)')
    if not winner_lto and not winner_analysis.get('win_in_last_3'):
        reasons_no.append('No recent win')
    
    if reasons_no:
        print(f'   → NO - Would NOT pick')
        print(f'   Reasons:')
        for reason in reasons_no:
            print(f'     - {reason}')
        print(f'   → CORRECT - 50/1 longshots are rarely value bets')
        print(f'   → This was a lucky upset, not predictable pattern')

# All horses analyzed
print(f'\n\n{"="*100}')
print('ALL HORSES ANALYZED (sorted by actual finish):')
print('='*100)

# Sort by finish position
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
        category = horse_analysis.get('odds_category', 'N/A')
        
        marker = ''
        if position == 1:
            marker = '*** WINNER (50/1) ***'
        elif position == 2:
            marker = '** 2ND (14/1) **'
        elif position == 3:
            marker = '** 3RD (3/1 FAV) **'
        
        print(f'{position:2}. {horse_name:25} | SP: {sp:8} | Pre-odds: {str(odds):6} | Form: {str(form):12} | {category:12} {marker}')

print('\n')

# Save learning to database
learning_entry = {
    'bet_id': f'LEARNING_2026-02-02_KEMPTON_1435',
    'bet_date': '2026-02-02',
    'analysis_type': 'RACE_RESULT_LEARNING',
    'venue': 'Kempton',
    'race_time': '14:35',
    'race_class': 'Class 4',
    'going': 'Good to Soft',
    'runners': 10,
    'field_size': 'MEDIUM',
    'winner': race_result['finishers'][0]['horse'],
    'winner_odds': race_result['finishers'][0]['odds'],
    'winner_odds_decimal': Decimal('51.0'),
    'winner_category': 'LONGSHOT',
    'winner_type': 'MASSIVE_UPSET',
    'winner_lto': winner_analysis.get('lto_winner', False) if winner_analysis else False,
    'winner_form': winner_analysis.get('form', 'Unknown') if winner_analysis else 'Unknown',
    'second': race_result['finishers'][1]['horse'],
    'third': race_result['finishers'][2]['horse'],
    'favorite': 'Frontier Prince',
    'favorite_odds': '3/1',
    'favorite_finish': 3,
    'created_at': datetime.now().isoformat(),
    'horses_analyzed': len(analyses),
    'status': 'LEARNED',
    'key_insight': '50/1 longshot won - unpredictable upset, correct to avoid',
    'learning_points': [
        'Class 4 races more unpredictable than Graded races',
        'Top 3 favorites all failed (3/1, 11/2, 7/2)',
        'Market completely mispriced winner (50/1)',
        'Longshot upsets happen but are not predictable patterns',
        'Correct strategy: avoid extreme longshots (>50 odds)',
        'Good to Soft going did not produce obvious form pattern'
    ]
}

try:
    table.put_item(Item=learning_entry)
    print(f'✓ Learning saved to database: LEARNING_2026-02-02_KEMPTON_1435\n')
except Exception as e:
    print(f'✗ Error saving learning: {str(e)}\n')

# Summary of all races today
print('='*100)
print('SUMMARY: ALL RACES ANALYZED TODAY')
print('='*100)
print('\n1. Kempton 13:27 (Class 4, Good):')
print('   Winner: Aviation @ 5/1')
print('   Pattern: Value edge + course form + class context')
print('   Our pick: Hawaii Du Mestivel (LOST)')
print('   Learning: Prioritize value edge, course form, class')

print('\n2. Leopardstown 14:25 (Handicap Hurdle, Heavy, 21 runners):')
print('   Winner: Saint Le Fort @ 10/1')
print('   Pattern: Going ability > recent form')
print('   Our pick: Would NOT pick (no recent wins)')
print('   Learning: Heavy going changes everything')

print('\n3. Leopardstown 14:55 (Graded Chase, Soft, 3 runners):')
print('   Winner: Romeo Coolio @ 4/9')
print('   Pattern: Favorite dominates small graded race')
print('   Our pick: Would NOT pick (odds too short)')
print('   Learning: Correct to skip heavy favorites (no value)')

print('\n4. Kempton 14:35 (Class 4, Good to Soft, 10 runners):')
print('   Winner: Gooloogong @ 50/1 (MASSIVE UPSET)')
print('   Pattern: Unpredictable longshot upset')
print('   Our pick: Would NOT pick (extreme longshot)')
print('   Learning: Correct to avoid 50/1 shots (not predictable)')

print('\n**PATTERN SUMMARY:**')
print('  - 0/4 winners predicted correctly')
print('  - 2/4 correctly avoided (Romeo Coolio, Gooloogong)')
print('  - 2/4 missed opportunities (Aviation, Saint Le Fort)')
print('  - Key issue: Heavy going criteria, class context')
print('  - Strengths: Value discipline, avoiding extreme odds')
print('='*100)
