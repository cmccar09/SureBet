"""
Manually update race results
For 12:50 Kempton
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Race results
results = {
    'Port Noir': 1,
    'Age Of Time': 2,
    'Galaxy Wonder': 3,
    'Masqool': 4,
    'Johnjay': 5,
    'Mbappe': 0,  # Ran but didn't place
    'Berning Hot': 0,
    'Brinton': 0,
    'Our Dagger': 0,
    'Marchetti': 0  # Non-runner
}

# Update each horse
response = table.scan()
items = response.get('Items', [])

updated = 0
for item in items:
    if 'Kempton' in item.get('course', '') and '12:50' in item.get('race_time', ''):
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
            
            # Update in database
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
                print(f"Updated: {horse_name:<20} Position: {position:>2}  Score: {score:5.1f}/100  Outcome: {outcome}")
                updated += 1
                
            except Exception as e:
                print(f"Error updating {horse_name}: {e}")

print(f"\nUpdated {updated} horses")
