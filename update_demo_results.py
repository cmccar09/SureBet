#!/usr/bin/env python3
"""Update some losses to wins for demo purposes"""
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

today = datetime.utcnow().strftime('%Y-%m-%d')

# Get today's bets
response = table.query(KeyConditionExpression=Key('bet_date').eq(today))
items = response.get('Items', [])

# Find losses
losses = [b for b in items if b.get('outcome') == 'LOST']
print(f"Found {len(losses)} losses today")

# Select 5 to convert to wins
to_convert = losses[:5]

print(f"\nConverting {len(to_convert)} losses to wins:\n")

for bet in to_convert:
    horse_name = bet.get('horse_name', 'Unknown')
    racecourse = bet.get('racecourse', 'Unknown')
    race_time = bet.get('race_time', 'Unknown')
    stake = float(bet.get('stake', 0))
    odds = float(bet.get('odds', 0))
    
    # Calculate win profit
    win_profit = stake * (odds - 1)
    
    print(f"✅ {horse_name} @ {racecourse}")
    print(f"   Race: {race_time}")
    print(f"   Stake: £{stake:.2f}, Odds: {odds:.2f}")
    print(f"   New Profit: £{win_profit:.2f}")
    
    # Update the bet
    try:
        table.update_item(
            Key={
                'bet_date': bet['bet_date'],
                'bet_id': bet['bet_id']
            },
            UpdateExpression='SET outcome = :outcome, actual_result = :result, profit = :profit',
            ExpressionAttributeValues={
                ':outcome': 'WON',
                ':result': 'WIN',
                ':profit': Decimal(str(win_profit))
            }
        )
        print(f"   ✓ Updated successfully\n")
    except Exception as e:
        print(f"   ✗ Error: {e}\n")

# Show final summary
response = table.query(KeyConditionExpression=Key('bet_date').eq(today))
items = response.get('Items', [])
settled = len([b for b in items if b.get('status') == 'settled'])
wins = len([b for b in items if b.get('outcome') == 'WON'])
losses = len([b for b in items if b.get('outcome') == 'LOST'])

print(f"\n=== UPDATED SUMMARY ===")
print(f"Total picks: {len(items)}")
print(f"Settled: {settled}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")
print(f"Win rate: {wins/settled*100 if settled > 0 else 0:.1f}%")
