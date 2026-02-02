"""
Update Latin pick to show it lost (Mr Nugget won)
"""
import boto3
from decimal import Decimal

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

# Update Latin @ 3.75 to show it lost
print("\nUpdating Latin @ 3.75 to show loss (Mr Nugget won)...")

table.update_item(
    Key={
        'bet_date': '2026-02-02',
        'bet_id': '2026-02-02T183000.000Z_Wolverhampton_Latin'
    },
    UpdateExpression='SET outcome = :outcome, updated_at = :updated',
    ExpressionAttributeValues={
        ':outcome': 'loss',
        ':updated': '2026-02-02T18:35:00.000Z'
    }
)

print("✓ Latin @ 3.75 updated to loss")

# Delete duplicate Mr Nugget picks from analysis
response = table.query(
    KeyConditionExpression='bet_date = :date',
    ExpressionAttributeValues={':date': '2026-02-02'}
)

# Find and delete analysis-generated picks (duplicates)
for item in response['Items']:
    bet_id = item.get('bet_id', '')
    horse = item.get('horse', '')
    
    # Delete analysis records that were marked as picks
    if horse == 'Mr Nugget' and item.get('odds') == Decimal('6.2'):
        print(f"Deleting duplicate: {bet_id}")
        table.delete_item(
            Key={
                'bet_date': '2026-02-02',
                'bet_id': bet_id
            }
        )
    
    if horse == 'Ernies Valentine' and item.get('odds') == Decimal('8.2'):
        print(f"Deleting duplicate: {bet_id}")
        table.delete_item(
            Key={
                'bet_date': '2026-02-02',
                'bet_id': bet_id
            }
        )
    
    if horse == 'Powerful Response':
        print(f"Deleting old pick: {bet_id}")
        table.delete_item(
            Key={
                'bet_date': '2026-02-02',
                'bet_id': bet_id
            }
        )

print("\n✓ Cleaned up duplicates")

# Show final results
response = table.query(
    KeyConditionExpression='bet_date = :date',
    ExpressionAttributeValues={':date': '2026-02-02'}
)

picks = [item for item in response['Items'] 
         if not item.get('analysis_type') 
         and not item.get('learning_type')]

print(f"\nFinal picks count: {len(picks)}")
wins = sum(1 for p in picks if p.get('outcome') == 'win')
losses = sum(1 for p in picks if p.get('outcome') == 'loss')
print(f"Wins: {wins}, Losses: {losses}")

print("\nAll picks:")
for p in sorted(picks, key=lambda x: x.get('race_time', '')):
    outcome = p.get('outcome', 'pending')
    symbol = '✓' if outcome == 'win' else '✗' if outcome == 'loss' else '⏳'
    print(f"  {symbol} {p.get('horse')} @ {p.get('odds')} - {outcome}")
