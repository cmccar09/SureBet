import boto3
db = boto3.resource('dynamodb', region_name='eu-west-1')
t = db.Table('CheltenhamPicks')
r = t.scan(FilterExpression='pick_date = :d', ExpressionAttributeValues={':d': '2026-03-08'})
items = sorted(r['Items'], key=lambda x: (x.get('day', ''), x.get('race_time', '')))
print(f"{'Race':<45} {'Horse':<25} {'Odds'}")
print("-" * 80)
for i in items:
    race = i.get('race_name', '')[:44]
    horse = i.get('horse', '')[:24]
    odds = i.get('odds', '?')
    print(f"{race:<45} {horse:<25} {odds}")
print(f"\nTotal: {len(items)} races saved for 2026-03-08")
