#!/usr/bin/env python3
"""Quick script to update Mask Of Zorro result"""

import boto3
from decimal import Decimal

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

# Find the pick
response = table.scan(
    FilterExpression='contains(selection_name, :name) AND #d = :today',
    ExpressionAttributeNames={'#d': 'date'},
    ExpressionAttributeValues={
        ':name': 'Mask Of Zorro',
        ':today': '2026-01-23'
    }
)

items = response.get('Items', [])
print(f'Found {len(items)} matching picks')

if items:
    for item in items:
        pick_id = item.get('pick_id')
        horse = item.get('selection_name')
        meeting = item.get('meeting')
        odds = float(item.get('odds', 0))
        stake = float(item.get('stake', 0))
        bet_type = item.get('bet_type', 'WIN')
        
        print(f'\nUpdating: {horse} @ {meeting}')
        print(f'  Odds: {odds}')
        print(f'  Stake: £{stake}')
        print(f'  Bet Type: {bet_type}')
        
        # Calculate profit for WIN bet
        profit = stake * (odds - 1)
        
        print(f'  Profit: £{profit:.2f}')
        
        # Update the record
        table.update_item(
            Key={'pick_id': pick_id},
            UpdateExpression='SET outcome = :outcome, profit = :profit, result_status = :status',
            ExpressionAttributeValues={
                ':outcome': 'WON',
                ':profit': Decimal(str(round(profit, 2))),
                ':status': 'settled'
            }
        )
        
        print(f'✅ Updated {horse} to WON with profit £{profit:.2f}')
else:
    print('No matching picks found!')
