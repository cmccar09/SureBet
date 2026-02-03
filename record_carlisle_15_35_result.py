import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Result: 1st Haarar @ 9/2, 2nd Kientzheim @ 16/1, 3rd Medieval Gold @ 11/4, 4th Smart Decision
# Our picks: Haarar (74/100 GOOD), Medieval Gold (70/100 GOOD)

response = table.query(
    KeyConditionExpression='bet_date = :date',
    FilterExpression='course = :course AND race_time = :time',
    ExpressionAttributeValues={
        ':date': '2026-02-03',
        ':course': 'Carlisle',
        ':time': '15:35'
    }
)

print(f"\n{'='*80}")
print("CARLISLE 15:35 RESULT - HAARAR WON @ 9/2")
print(f"{'='*80}\n")

haarar_found = False
medieval_found = False

for item in response['Items']:
    horse_name = item.get('horse_name', '')
    
    if 'Haarar' in horse_name:
        haarar_found = True
        odds = 5.5  # 9/2 decimal
        stake = 30
        profit = (odds * stake) - stake  # €135 profit
        
        table.update_item(
            Key={
                'bet_date': '2026-02-03',
                'bet_id': item['bet_id']
            },
            UpdateExpression='SET outcome = :outcome, profit_loss = :profit, actual_winner = :winner, result_updated = :updated',
            ExpressionAttributeValues={
                ':outcome': 'win',
                ':profit': Decimal(str(profit)),
                ':winner': 'Haarar',
                ':updated': 'yes'
            }
        )
        print(f"✓ WINNER! Haarar @ 9/2 (€{stake} stake → €{profit:.2f} profit)")
        print(f"  Score: {item.get('comprehensive_score', 0)}/100 {item.get('confidence_grade', '')}")
        print(f"  Form: {item.get('recent_form', 'N/A')}")
        
    elif 'Medieval Gold' in horse_name:
        medieval_found = True
        stake = 30
        loss = -stake
        
        table.update_item(
            Key={
                'bet_date': '2026-02-03',
                'bet_id': item['bet_id']
            },
            UpdateExpression='SET outcome = :outcome, profit_loss = :profit, actual_winner = :winner, result_updated = :updated',
            ExpressionAttributeValues={
                ':outcome': 'loss',
                ':profit': Decimal(str(loss)),
                ':winner': 'Haarar',
                ':updated': 'yes'
            }
        )
        print(f"✗ Medieval Gold finished 3rd @ 11/4 (-€{stake})")
        print(f"  Score: {item.get('comprehensive_score', 0)}/100 {item.get('confidence_grade', '')}")
        print(f"  Form: {item.get('recent_form', 'N/A')}")

print(f"\n{'='*80}")
print("RACE SUMMARY")
print(f"{'='*80}")
print(f"Winner: Haarar @ 9/2 (5.5 decimal)")
print(f"Our picks: Haarar (WON ✓), Medieval Gold (3rd ✗)")
print(f"Net result: +€105 (€135 win - €30 loss)")
print(f"\nHaarar found in DB: {haarar_found}")
print(f"Medieval Gold found in DB: {medieval_found}")
print(f"{'='*80}\n")
