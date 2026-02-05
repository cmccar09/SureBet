"""
Update 13:25 Kempton results
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Race results
results = {
    'Glistening': 1,
    "Naana's Crystal": 2,
    'Naanas Crystal': 2,  # Alternative spelling
    'Too Hot To Tango': 3,
    'Star Obsession': 4,
    'Darn Hot Dame': 5,
    # Others ran but didn't place in top 5
    'Nuptown Girl': 0,
    'Bronte Beach': 0,
    'Dubawi Phantom': 0,
    'Zain Nights': 0,
    'Twelfth Star': 0,
    'Makeen': 0,
    'Eeh Bah Gum': 0
}

response = table.scan()
items = response.get('Items', [])

updated = 0
for item in items:
    if 'Kempton' in item.get('course', '') and '13:25' in item.get('race_time', ''):
        horse_name = item.get('horse', '')
        
        if horse_name in results:
            position = results[horse_name]
            
            if position == 1:
                outcome = 'WON'
                actual_result = 'WIN'
            elif position in [2, 3]:
                outcome = 'PLACED'
                actual_result = f'PLACED_{position}'
            elif position > 3:
                outcome = 'LOST'
                actual_result = f'FINISHED_{position}'
            else:
                outcome = 'LOST'
                actual_result = 'RAN'
            
            try:
                table.update_item(
                    Key={
                        'bet_id': item['bet_id'],
                        'bet_date': item['bet_date']
                    },
                    UpdateExpression='SET outcome = :outcome, actual_result = :result, actual_position = :pos',
                    ExpressionAttributeValues={
                        ':outcome': outcome,
                        ':result': actual_result,
                        ':pos': position
                    }
                )
                
                score = float(item.get('combined_confidence', 0))
                print(f"Updated: {horse_name:<25} Position: {position:>2}  Score: {score:5.1f}/100  Outcome: {outcome}")
                updated += 1
                
            except Exception as e:
                print(f"Error updating {horse_name}: {e}")

print(f"\nUpdated {updated} horses")
