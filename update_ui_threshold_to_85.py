"""
Update database to reflect new show_in_ui threshold (85+ only)
This fixes existing items that were set to show_in_ui=True under old 70+ threshold
"""
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

today = datetime.now().strftime('%Y-%m-%d')

# Get all today's items
resp = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('bet_date').eq(today)
)

items = resp.get('Items', [])

print(f"Updating UI threshold for {today}")
print(f"="*70)
print(f"\nFound {len(items)} items")

updated = 0
demoted = 0
promoted = 0

for item in items:
    score = float(item.get('comprehensive_score', 0))
    current_show = item.get('show_in_ui', False)
    new_show = (score >= 85)
    
    # Only update if there's a change
    if current_show != new_show:
        table.update_item(
            Key={
                'bet_date': item['bet_date'],
                'bet_id': item['bet_id']
            },
            UpdateExpression='SET show_in_ui = :show, recommended_bet = :rec',
            ExpressionAttributeValues={
                ':show': new_show,
                ':rec': (score >= 85)
            }
        )
        updated += 1
        
        if current_show and not new_show:
            # Was showing, now hidden
            demoted += 1
            print(f"  DEMOTED: {item.get('horse')[:30]:30} {score:3.0f}/100  (now learning data)")
        elif not current_show and new_show:
            # Was hidden, now showing
            promoted += 1
            print(f"  PROMOTED: {item.get('horse')[:30]:30} {score:3.0f}/100  (now UI pick)")

print(f"\n" + "="*70)
print(f"Update complete:")
print(f"  Items updated: {updated}")
print(f"  Demoted to learning (70-84): {demoted}")
print(f"  Promoted to UI (85+): {promoted}")

# Show final counts
resp2 = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('bet_date').eq(today)
)
items2 = resp2.get('Items', [])
ui_picks = [i for i in items2 if i.get('show_in_ui')]

print(f"\nFinal counts:")
print(f"  Total horses: {len(items2)}")
print(f"  UI picks (85+): {len(ui_picks)}")
print(f"  Learning data (60-84): {len([i for i in items2 if 60 <= float(i.get('comprehensive_score', 0)) < 85])}")
print(f"  Analysis only (<60): {len([i for i in items2 if float(i.get('comprehensive_score', 0)) < 60])}")

print(f"\n✓ Threshold updated: Only 85+ scores will show in results")
