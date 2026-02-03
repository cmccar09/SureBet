import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

response = table.query(
    KeyConditionExpression='bet_date = :date',
    FilterExpression='course = :course AND race_time = :time',
    ExpressionAttributeValues={
        ':date': '2026-02-03',
        ':course': 'Carlisle',
        ':time': '15:35'
    }
)

print(f"
{'='*80}")
print("CARLISLE 15:35 RESULT - HAARAR WON @ 9/2")
print(f"{'='*80}
")

for item in response['Items']:
    horse_name = item.get('horse_name', '')
    
    if 'Haarar' in horse_name:
        odds = 5.5
        stake = 30
        profit = (odds * stake) - stake
        
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
        print(f"WIN! Haarar @ 9/2 (€{stake} stake → €{profit:.2f} profit)")
        print(f"Score: {item.get('comprehensive_score', 0)}/100 {item.get('confidence_grade', '')}")
        
    elif 'Medieval Gold' in horse_name:
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
        print(f"LOSS: Medieval Gold finished 3rd @ 11/4 (-€{stake})")
        print(f"Score: {item.get('comprehensive_score', 0)}/100")

print(f"
{'='*80}")
print("Net result: +€105 (€135 win - €30 loss)")
print(f"{'='*80}
")
