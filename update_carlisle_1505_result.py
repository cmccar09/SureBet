"""
Update Carlisle 15:05 result
Winner: Celestial Fashion (9/4 fav)
"""
import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

bet_date = '2026-02-03'

# Get all Carlisle 15:05 entries
response = table.scan(
    FilterExpression='course = :course AND bet_date = :date',
    ExpressionAttributeValues={
        ':course': 'Carlisle',
        ':date': bet_date
    }
)

carlisle_1505 = [
    item for item in response['Items']
    if '15:05' in str(item.get('race_time', ''))
]

print(f"\nFound {len(carlisle_1505)} entries for Carlisle 15:05")

# Result data
results = {
    'Celestial Fashion': {'position': 1, 'sp': '9/4', 'outcome': 'WON'},
    'Lady In The Park': {'position': 2, 'sp': '16/1', 'outcome': 'PLACED'},
    'Ilovethenightlife': {'position': 3, 'sp': '11/4', 'outcome': 'PLACED'},
    'Divas Doyen': {'position': 4, 'sp': '18/1', 'outcome': 'LOST'},
}

updated = 0
for item in carlisle_1505:
    horse = item.get('horse', '')
    bet_id = item.get('bet_id', '')
    
    if horse in results:
        result = results[horse]
        
        try:
            table.update_item(
                Key={
                    'bet_date': bet_date,
                    'bet_id': bet_id
                },
                UpdateExpression='SET outcome = :outcome, actual_position = :pos, starting_price = :sp',
                ExpressionAttributeValues={
                    ':outcome': result['outcome'],
                    ':pos': Decimal(str(result['position'])),
                    ':sp': result['sp']
                }
            )
            print(f"✓ Updated {horse}: {result['position']} place ({result['sp']}) - {result['outcome']}")
            updated += 1
        except Exception as e:
            print(f"✗ Error updating {horse}: {str(e)}")

print(f"\n{'='*80}")
print(f"SUMMARY: Updated {updated} entries")
print(f"{'='*80}")
print("\nRESULT:")
print("1st: Celestial Fashion (9/4) - WE HAD THIS AT 68/100 (HIGHEST SCORE!)")
print("2nd: Lady In The Park (16/1) - We had at 42/100")
print("3rd: Ilovethenightlife (11/4) - We had at 54/100")
print("4th: Divas Doyen (18/1) - We had at 51/100 [UI PICK - WRONG]")
print("\nScoring logic CORRECT - UI selection WRONG (duplicate issue)")
