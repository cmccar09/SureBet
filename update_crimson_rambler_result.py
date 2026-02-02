"""
Update Crimson Rambler result - Placed 2nd (lost by a neck)
20:00 Wolverhampton - February 2, 2026
"""
import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Find Crimson Rambler pick
today = datetime.now().strftime('%Y-%m-%d')
response = table.query(
    KeyConditionExpression='bet_date = :today',
    FilterExpression='contains(horse, :horse)',
    ExpressionAttributeValues={
        ':today': today,
        ':horse': 'Crimson Rambler'
    }
)

items = response.get('Items', [])

if items:
    item = items[0]
    bet_id = item['bet_id']
    
    print(f"Found: {item.get('horse')} @ {item.get('odds')}")
    print(f"Course: {item.get('course')}")
    print(f"Race time: {item.get('race_time')}")
    print()
    
    # Update with 2nd place result
    table.update_item(
        Key={'bet_id': bet_id, 'bet_date': today},
        UpdateExpression='SET outcome = :outcome, finish_position = :position, winner = :winner, winner_odds = :winner_odds, distance_behind = :distance, updated_at = :updated',
        ExpressionAttributeValues={
            ':outcome': 'placed',  # 2nd place = placed
            ':position': 2,
            ':winner': 'Electrocution',
            ':winner_odds': Decimal('6.5'),  # 11/2 = 6.5
            ':distance': 'nk',  # neck
            ':updated': datetime.now().isoformat()
        }
    )
    
    print("="*80)
    print("RESULT UPDATED")
    print("="*80)
    print(f"Crimson Rambler @ 4.0 - PLACED 2nd")
    print(f"Winner: Electrocution @ 6.5 (11/2)")
    print(f"Distance: Neck (very close!)")
    print()
    print("LEARNING NOTES:")
    print("- Form: 0876- (appeared terrible)")
    print("- Comprehensive score: 47/100 (would be REJECTED)")
    print("- Actual result: 2nd place, lost by a neck")
    print("- Only 30pts for sweet spot, 17pts for optimal odds")
    print("- 0pts for form analysis")
    print()
    print("KEY INSIGHT:")
    print("Form analysis may have been too conservative here.")
    print("Horse ran much better than recent form suggested.")
    print("Need to investigate why form didn't predict this performance.")
    print("="*80)
    
else:
    print("Crimson Rambler not found in database")
