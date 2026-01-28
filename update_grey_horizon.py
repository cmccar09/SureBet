import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Get Grey Horizon bet
response = table.query(KeyConditionExpression=Key('bet_date').eq('2026-01-26'))
grey = [i for i in response['Items'] if i.get('horse') == 'Grey Horizon'][0]

print(f"\nGrey Horizon details:")
print(f"  Bet type: {grey['bet_type']}")
print(f"  Stake: €{grey['stake']}")
print(f"  Odds: {grey['odds']}")

# Grey Horizon was EW bet and WON
# EW bet = half stake on win, half stake on place
# Win pays full odds, place pays 1/5 odds (0.2 fraction)
if grey['bet_type'] == 'EW':
    half_stake = float(grey['stake']) / 2
    odds = float(grey['odds'])
    ew_frac = float(grey.get('ew_fraction', 0.2))
    win_return = half_stake * odds
    place_return = half_stake * (1 + (odds - 1) * ew_frac)
    total_return = win_return + place_return
    profit = total_return - float(grey['stake'])
    print(f"\n✅ EW WIN calculation:")
    print(f"  Win part (€{half_stake:.2f} @ {odds}): €{win_return:.2f}")
    print(f"  Place part (€{half_stake:.2f} @ {1 + (odds-1)*ew_frac:.2f}): €{place_return:.2f}")
    print(f"  Total return: €{total_return:.2f}")
    print(f"  Profit: €{profit:.2f}")
else:
    win_return = float(grey['stake']) * float(grey['odds'])
    profit = win_return - float(grey['stake'])
    print(f"\n✅ WIN calculation:")
    print(f"  Return: €{win_return:.2f}")
    print(f"  Profit: €{profit:.2f}")

# Update in DynamoDB
table.update_item(
    Key={'bet_date': '2026-01-26', 'bet_id': grey['bet_id']},
    UpdateExpression='SET outcome = :outcome, profit = :profit, updated_at = :timestamp',
    ExpressionAttributeValues={
        ':outcome': 'win',
        ':profit': Decimal(str(round(profit, 2))),
        ':timestamp': datetime.utcnow().isoformat()
    }
)

print(f"\n✅ Updated Grey Horizon as WIN with profit €{profit:.2f}")
