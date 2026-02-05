"""
Update 13:13 Ludlow results
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

results = {
    'King Al': 1,
    'Talakan': 2,
    'Wolf Rayet': 3,
    'Gallivanted': 4,
    'Down To Business': 5,
    'Notnow Goldielocks': 0,
    'Vics Bandit': 0,
    'Beechyhill': 0
}

response = table.scan()
items = response.get('Items', [])

updated = 0
for item in items:
    if 'Ludlow' in item.get('course', '') and '13:13' in item.get('race_time', ''):
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
