import boto3
import json

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

response = table.query(
    KeyConditionExpression='bet_date = :d',
    ExpressionAttributeValues={':d': '2026-01-18'}
)

items = response['Items']
print(f"Total bets: {len(items)}\n")

for item in items:
    horse = item.get('horse_name', item.get('horse', 'Unknown'))
    venue = item.get('course', 'Unknown')
    actual_result = item.get('actual_result', 'PENDING')
    status = item.get('status', 'pending')
    
    print(f"{horse:25} @ {venue:20} - status: {status:10} actual_result: {actual_result}")
