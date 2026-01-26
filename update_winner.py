#!/usr/bin/env python3
"""Update a winning bet"""

import boto3
from decimal import Decimal
import sys

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

# Get all today's picks
response = table.scan(
    FilterExpression='#d = :today',
    ExpressionAttributeNames={'#d': 'date'},
    ExpressionAttributeValues={':today': '2026-01-23'}
)

items = response.get('Items', [])
print(f'\nToday\'s picks ({len(items)}):')
print('='*60)

mask_pick = None
for i, item in enumerate(items, 1):
    name = item.get('selection_name', 'Unknown')
    meeting = item.get('meeting', 'Unknown')
    print(f'{i}. {name} @ {meeting}')
    
    if 'Mask' in name or 'Zorro' in name:
        mask_pick = item

print('='*60)

if mask_pick:
    pick_id = mask_pick.get('pick_id')
    horse = mask_pick.get('selection_name')
    meeting = mask_pick.get('meeting')
    odds = float(mask_pick.get('odds', 3.3))
    stake = float(mask_pick.get('stake', 20))
    bet_type = mask_pick.get('bet_type', 'WIN')
    
    print(f'\n🏆 WINNER FOUND!')
    print(f'  Horse: {horse}')
    print(f'  Meeting: {meeting}')
    print(f'  Odds: {odds}')
    print(f'  Stake: £{stake}')
    print(f'  Bet Type: {bet_type}')
    
    # Calculate profit for WIN bet
    profit = stake * (odds - 1)
    
    print(f'  💰 Profit: £{profit:.2f}')
    
    # Update the record
    try:
        table.update_item(
            Key={'pick_id': pick_id},
            UpdateExpression='SET outcome = :outcome, profit = :profit, result_status = :status',
            ExpressionAttributeValues={
                ':outcome': 'WON',
                ':profit': Decimal(str(round(profit, 2))),
                ':status': 'settled'
            }
        )
        
        print(f'\n✅ SUCCESS! Updated {horse} to WON with profit £{profit:.2f}')
    except Exception as e:
        print(f'\n❌ Error updating: {e}')
else:
    print('\n❌ Could not find Mask Of Zorro in today\'s picks')
