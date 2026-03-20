import boto3
from datetime import date
from boto3.dynamodb.conditions import Attr

ddb = boto3.resource('dynamodb', region_name='eu-west-1')
table = ddb.Table('SureBetBets')
today = str(date.today())

# Scan for items saved today
resp = table.scan(FilterExpression=Attr('bet_date').eq(today))
items = resp.get('Items', [])
print(f'Items with bet_date={today}: {len(items)}')
for it in items[:5]:
    horse = it.get('horse', it.get('horse_name', '?'))
    score = it.get('score', '?')
    show = it.get('show_in_ui', '?')
    odds = it.get('odds', '?')
    print(f'  horse={horse} score={score} show_in_ui={show} odds={odds}')

# Also check with race_date field
resp2 = table.scan(FilterExpression=Attr('race_date').begins_with(today))
items2 = resp2.get('Items', [])
print(f'\nItems with race_date starting {today}: {len(items2)}')
for it in items2[:5]:
    horse = it.get('horse', it.get('horse_name', '?'))
    show = it.get('show_in_ui', '?')
    print(f'  horse={horse} show_in_ui={show}')
