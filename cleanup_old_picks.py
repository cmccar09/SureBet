import boto3
from datetime import datetime, timezone

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

# Get all picks from today
response = table.scan(
    FilterExpression='#dt = :today OR bet_date = :today',
    ExpressionAttributeNames={'#dt': 'date'},
    ExpressionAttributeValues={':today': '2026-01-20'}
)

picks = response.get('Items', [])
now = datetime.now(timezone.utc)

print(f'\n=== Removing old/past picks from UI ===\n')

deleted_count = 0
for pick in picks:
    race_time_str = pick.get('race_time', '')
    horse = pick.get('horse', 'Unknown')
    course = pick.get('course', 'Unknown')
    
    if race_time_str:
        try:
            race_time = datetime.fromisoformat(race_time_str.replace('Z', '+00:00'))
            if race_time < now:
                print(f'DELETING (past): {race_time_str} - {horse} @ {course}')
                table.delete_item(
                    Key={
                        'bet_date': pick['bet_date'],
                        'bet_id': pick['bet_id']
                    }
                )
                deleted_count += 1
            else:
                print(f'KEEPING (future): {race_time_str} - {horse} @ {course}')
        except Exception as e:
            print(f'Error parsing time for {horse}: {e}')

print(f'\n✅ Deleted {deleted_count} old picks')
print('UI now showing only upcoming races')
