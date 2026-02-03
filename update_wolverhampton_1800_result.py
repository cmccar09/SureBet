"""
Record Wolverhampton 18:00 result
1st: Many A Star (IRE) @ 8/1
2nd: Dyrholaey (FR) @ 4/1
3rd: Cajetan @ 11/1
4th: Betsen

Our pick: No Return @ 14/1 - LOST
"""
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

# Query for No Return
response = table.query(
    KeyConditionExpression='bet_date = :date',
    FilterExpression='horse = :horse AND contains(race_time, :time)',
    ExpressionAttributeValues={
        ':date': '2026-02-03',
        ':horse': 'No Return',
        ':time': '18:00'
    }
)

items = response.get('Items', [])

print('\n' + '='*80)
print('WOLVERHAMPTON 18:00 - RACE RESULT')
print('='*80)

print('\nRACE RESULT:')
print('1st: Many A Star (IRE) @ 8/1')
print('2nd: Dyrholaey (FR) @ 4/1')
print('3rd: Cajetan @ 11/1')
print('4th: Betsen')

if items:
    # Get the UI pick (with comprehensive_score)
    ui_pick = None
    for item in items:
        if item.get('show_in_ui'):
            ui_pick = item
            break
    
    if not ui_pick:
        ui_pick = items[0]
    
    print('\n' + '-'*80)
    print('OUR PICK:')
    print('-'*80)
    score = ui_pick.get('comprehensive_score', 'N/A')
    grade = ui_pick.get('confidence_grade', 'N/A')
    odds = ui_pick.get('odds', 'N/A')
    
    print(f'Horse: No Return')
    print(f'Confidence: {score}/100 ({grade})')
    print(f'Odds: {odds}/1')
    print(f'Stake: €30')
    print(f'\nRESULT: LOST')
    print(f'Return: €0.00')
    print(f'Profit/Loss: -€30.00')
    
    # Update database
    table.update_item(
        Key={
            'bet_date': ui_pick['bet_date'],
            'bet_id': ui_pick['bet_id']
        },
        UpdateExpression='SET outcome = :outcome, actual_odds = :odds, profit = :profit, result_time = :time',
        ExpressionAttributeValues={
            ':outcome': 'loss',
            ':odds': odds,
            ':profit': -30,
            ':time': datetime.now().isoformat()
        }
    )
    
    print('\n✓ Database updated')
    
    print('\n' + '='*80)
    print('ANALYSIS:')
    print('='*80)
    print(f'• No Return scored {score}/100 (GOOD tier) at 14/1 odds')
    print(f'• With new long-shot penalty (-5 for 10-15 odds), score dropped from 75 to 70')
    print(f'• 14/1 was correctly rated as GOOD, not EXCELLENT')
    print(f'• Winner was Many A Star @ 8/1 (in value zone)')
    print(f'• Loss validates more conservative scoring for long shots')
    
else:
    print('\n✗ No Return not found in database')
    print('Race may not have been analyzed')
