import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

today = datetime.now().strftime('%Y-%m-%d')
race_time = "2026-02-02T19:30:00.000Z"
bet_id = f"{race_time}_Wolverhampton_Market House"

print(f"\n{'='*80}")
print("UPDATING MARKET HOUSE RESULT")
print(f"{'='*80}\n")

# Update Market House - 5th place (LOSS)
table.update_item(
    Key={
        'bet_date': today,
        'bet_id': bet_id
    },
    UpdateExpression='SET outcome = :outcome, finish_position = :position, winner = :winner, winner_odds = :winner_odds',
    ExpressionAttributeValues={
        ':outcome': 'loss',
        ':position': 5,
        ':winner': 'Francesco Baracca',
        ':winner_odds': Decimal('1.909')  # 10/11 in decimal
    }
)

print("✓ Market House @ 5.9 - LOSS (finished 5th)")
print("  Winner: Francesco Baracca @ 10/11 (1.909)")
print(f"\n{'='*80}")
print("TONIGHT'S WOLVERHAMPTON RESULTS SO FAR:")
print(f"{'='*80}")
print("❌ 19:00 The Dark Baron @ 5.1 - LOSS")
print("❌ 19:30 Market House @ 5.9 - LOSS (HIGH confidence)")
print("⏳ 20:00 Crimson Rambler @ 4.0 - PENDING (HIGH confidence)")
print(f"\n{'='*80}")
print("Current: 0/2 (0%)")
print("Sweet spot validation taking a hit tonight")
print(f"{'='*80}\n")
