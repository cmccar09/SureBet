#!/usr/bin/env python3
"""Update In The Age result to 2nd place"""

import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Find In The Age pick
response = table.scan(
    FilterExpression='begins_with(bet_date, :d)',
    ExpressionAttributeValues={':d': '2026-01-24'}
)

items = [i for i in response['Items'] if i.get('horse') == 'In The Age']

if items:
    pick = items[0]
    print(f"Found: {pick.get('horse')} @ {pick.get('course')}")
    print(f"  bet_id: {pick.get('bet_id')}")
    print(f"  bet_date: {pick.get('bet_date')}")
    print(f"  bet_type: {pick.get('bet_type')}")
    print(f"  race_time: {pick.get('race_time')}")
    
    # Update to 2nd place (placed)
    table.update_item(
        Key={
            'bet_date': pick['bet_date'],
            'bet_id': pick['bet_id']
        },
        UpdateExpression='SET outcome = :outcome, actual_position = :pos, feedback_processed = :fp',
        ExpressionAttributeValues={
            ':outcome': 'placed',
            ':pos': Decimal('2'),
            ':fp': False
        }
    )
    
    print(f"\n✓ Updated: In The Age finished 2nd (PLACED)")
    print(f"  Outcome: placed")
    print(f"  Position: 2")
else:
    print("✗ No pick found for In The Age on 2026-01-24")
