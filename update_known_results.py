"""
Manually record known results and prepare to fetch others
Based on what we know and what's available
"""
import boto3
from decimal import Decimal
from datetime import datetime

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

print("="*80)
print("MANUAL RESULTS RECORDING")
print("="*80)

# Results we already know
known_results = [
    {
        'horse': 'Harbour Vision',
        'outcome': 'win',
        'winner': 'Harbour Vision',
        'odds': 8.6,
        'profit': (8.6 * 30) - 30  # €30 stake
    },
    {
        'horse': 'No Return',
        'outcome': 'loss',
        'winner': 'Unknown',
        'odds': 14.5,
        'profit': -30
    }
]

# Update known results
for result in known_results:
    response = table.query(
        KeyConditionExpression='bet_date = :date',
        FilterExpression='horse = :horse',
        ExpressionAttributeValues={
            ':date': '2026-02-03',
            ':horse': result['horse']
        }
    )
    
    items = [item for item in response['Items'] if item.get('show_in_ui')]
    
    if items:
        item = items[0]
        table.update_item(
            Key={
                'bet_date': '2026-02-03',
                'bet_id': item['bet_id']
            },
            UpdateExpression='SET outcome = :outcome, profit_loss = :pl, actual_winner = :winner, result_updated = :ts, show_in_ui = :ui',
            ExpressionAttributeValues={
                ':outcome': result['outcome'],
                ':pl': Decimal(str(result['profit'])),
                ':winner': result['winner'],
                ':ts': datetime.now().isoformat(),
                ':ui': True
            }
        )
        print(f"✓ Updated {result['horse']}: {result['outcome'].upper()}")

# Get remaining picks that need results
response = table.query(
    KeyConditionExpression='bet_date = :date',
    FilterExpression='show_in_ui = :ui AND (attribute_not_exists(outcome) OR outcome = :pending)',
    ExpressionAttributeValues={
        ':date': '2026-02-03',
        ':ui': True,
        ':pending': 'pending'
    }
)

print(f"\n{'='*80}")
print("PICKS STILL AWAITING RESULTS:")
print("="*80)

for item in sorted(response['Items'], key=lambda x: x.get('race_time', '')):
    horse = item.get('horse', '')
    course = item.get('course', '')
    race_time = item.get('race_time', '')[:16]
    odds = item.get('odds', 0)
    score = item.get('comprehensive_score') or item.get('combined_confidence', 0)
    
    print(f"{race_time} {course:15} {horse:25} {score}/100 @ {odds}")

print(f"\n{'='*80}")
print("NOTE: Use Racing Post or manual entry for remaining results")
print("="*80)
