"""
Update Carlisle 15:35 result - Smart Decision 4th (FAVORITE BEATEN)
"""
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("\n" + "="*80)
print("UPDATING CARLISLE 15:35 RESULT")
print("="*80)

# Result: Smart Decision 4th (13/8 FAV beaten)
# Winner: Haarar 9/2

date = '2026-02-03'
response = table.scan(
    FilterExpression='#dt = :date AND course = :course AND contains(race_time, :time)',
    ExpressionAttributeNames={'#dt': 'date'},
    ExpressionAttributeValues={
        ':date': date,
        ':course': 'Carlisle',
        ':time': '15:35'
    }
)

picks = response.get('Items', [])

results = {
    'Haarar': 'WON',
    'Kientzheim': 'PLACED',  # 2nd at 16/1
    'Medieval Gold': 'PLACED',  # 3rd at 11/4
    'Smart Decision': 'LOST'  # 4th at 13/8 FAV
}

print(f"\nFound {len(picks)} horses\n")

for pick in picks:
    horse = pick.get('horse', '')
    result = results.get(horse, 'UNKNOWN')
    bet_id = pick.get('bet_id', '')
    
    if not bet_id:
        print(f"  [SKIP] {horse} - no bet_id")
        continue
    
    try:
        table.update_item(
            Key={
                'bet_date': date,
                'bet_id': bet_id
            },
            UpdateExpression='SET #result = :result',
            ExpressionAttributeNames={'#result': 'result'},
            ExpressionAttributeValues={':result': result}
        )
        
        score = float(pick.get('combined_confidence', 0))
        grade = pick.get('confidence_grade', 'UNKNOWN')
        show_ui = pick.get('show_in_ui', False)
        odds = pick.get('odds', 0)
        
        marker = "[UI PICK]" if show_ui else ""
        print(f"  {marker:10} {horse:25} {score:5.1f}/100 {grade:10} Odds: {odds:6} → {result}")
        
    except Exception as e:
        print(f"  [ERROR] {horse}: {str(e)}")

print("\n" + "="*80)
print("RACE ANALYSIS")
print("="*80)
print("Winner: Haarar (9/2) - NOT IN OUR DATABASE")
print("2nd: Kientzheim (16/1) - NOT IN OUR DATABASE")
print("3rd: Medieval Gold (11/4) - NOT IN OUR DATABASE")
print("4th: Smart Decision (13/8 FAV) - OUR ONLY HORSE - LOST")
print("\nClass 4 | Good to Soft | 11 runners")
print("\nKEY LEARNING:")
print("- We only analyzed 1 of 11 horses (9% coverage - WAY below 75% threshold)")
print("- Our pick was the FAVORITE and finished 4th")
print("- Winner was 9/2 (we didn't analyze)")
print("- This race should NOT have been shown on UI (coverage too low)")
print("="*80)
