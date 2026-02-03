"""
Update Fairyhouse 16:40 result - Outofafrika WON
"""
import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("\n" + "="*80)
print("UPDATING FAIRYHOUSE 16:40 RESULT")
print("="*80)

# Get the race
date = '2026-02-03'
response = table.scan(
    FilterExpression='#dt = :date AND course = :course AND contains(race_time, :time)',
    ExpressionAttributeNames={'#dt': 'date'},
    ExpressionAttributeValues={
        ':date': date,
        ':course': 'Fairyhouse',
        ':time': '16:40'
    }
)

picks = response.get('Items', [])

print(f"\nFound {len(picks)} horses in this race\n")

# Result: Outofafrika WON at 5/1
results = {
    'Outofafrika': 'WON',
    'Green Hint': 'PLACED',  # 2nd at 4/7F
    'Lemmy Caution': 'PLACED',  # 3rd at 6/1
    # Others LOST
}

for pick in picks:
    horse = pick.get('horse', '')
    result = results.get(horse, 'LOST')
    bet_id = pick.get('bet_id', '')
    
    if not bet_id:
        print(f"  [SKIP] {horse} - no bet_id")
        continue
    
    # Update result
    try:
        table.update_item(
            Key={
                'date': date,
                'bet_id': bet_id
            },
            UpdateExpression='SET #result = :result',
            ExpressionAttributeNames={'#result': 'result'},
            ExpressionAttributeValues={':result': result}
        )
        
        score = float(pick.get('combined_confidence', 0))
        grade = pick.get('confidence_grade', 'UNKNOWN')
        show_ui = pick.get('show_in_ui', False)
        
        marker = "[UI PICK]" if show_ui else ""
        print(f"  {marker:10} {horse:25} {score:5.1f}/100 {grade:10} → {result}")
        
    except Exception as e:
        print(f"  [ERROR] {horse}: {str(e)}")

print("\n" + "="*80)
print("RACE RESULT")
print("="*80)
print("Winner: Outofafrika (5/1)")
print("2nd: Green Hint (4/7 FAV)")
print("3rd: Lemmy Caution (6/1)")
print("\nSoft ground | 7 runners")
print("="*80)
