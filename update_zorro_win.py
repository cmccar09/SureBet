#!/usr/bin/env python3
"""Update Mask Of Zorro to WON - using correct composite key"""

import boto3
from decimal import Decimal

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

# Find Mask Of Zorro
response = table.scan(
    FilterExpression='horse = :horse AND #d = :date',
    ExpressionAttributeNames={'#d': 'date'},
    ExpressionAttributeValues={
        ':horse': 'Mask Of Zorro',
        ':date': '2026-01-23'
    }
)

if response['Items']:
    item = response['Items'][0]
    
    bet_date = item.get('bet_date')
    bet_id = item.get('bet_id')
    horse = item.get('horse')
    course = item.get('course')
    odds = float(item.get('odds', 3.3))
    stake = float(item.get('stake', 20))
    
    print(f'\n🏆 Updating: {horse} @ {course}')
    print(f'   Odds: {odds}')
    print(f'   Stake: £{stake}')
    
    # Calculate profit
    profit = stake * (odds - 1)
    print(f'   💰 Profit: £{profit:.2f}')
    
    # Update with correct composite key
    table.update_item(
        Key={
            'bet_date': bet_date,
            'bet_id': bet_id
        },
        UpdateExpression='SET outcome = :outcome, profit = :profit',
        ExpressionAttributeValues={
            ':outcome': 'won',
            ':profit': Decimal(str(round(profit, 2)))
        }
    )
    
    print(f'\n✅ SUCCESS! {horse} marked as WON with £{profit:.2f} profit!')
else:
    print('❌ Mask Of Zorro not found')
