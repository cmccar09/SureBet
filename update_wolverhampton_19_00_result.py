import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('BettingPicks')

# Update The Dark Baron with loss
print("\nUpdating Wolverhampton 19:00 result...")
print("Winner: Law Supreme @ 8.8")
print("Our pick: The Dark Baron @ 5.1 - LOSS\n")

response = table.update_item(
    Key={
        'bet_date': '2026-02-02',
        'bet_id': '2026-02-02T190000.000Z_Wolverhampton_The_Dark_Baron'
    },
    UpdateExpression='SET outcome = :outcome, actual_winner = :winner, actual_winner_odds = :winner_odds, result_updated = :updated',
    ExpressionAttributeValues={
        ':outcome': 'loss',
        ':winner': 'Law Supreme',
        ':winner_odds': Decimal('8.8'),
        ':updated': datetime.now().isoformat()
    },
    ReturnValues='ALL_NEW'
)

print("✓ The Dark Baron updated: LOSS")
print(f"  Analysis Score: {response['Attributes']['analysis_score']}")
print(f"  Our odds: {response['Attributes']['odds']}")
print(f"  Winner: {response['Attributes']['actual_winner']} @ {response['Attributes']['actual_winner_odds']}")

# Analyze what happened
print("\n" + "="*80)
print("COMPREHENSIVE ANALYSIS BREAKDOWN:")
print("="*80)

print("\nOur Rankings (from comprehensive analysis):")
print("  1. The Dark Baron @ 5.1 - 73pts (OUR PICK - LOST)")
print("  2. Stipulation @ 3.1 - 63pts")
print("  3. Magic Runner @ 8.8 - 52pts")
print("  4. Powerful Response @ 9.0 - 46pts")
print("  5. Law Supreme @ 8.8 - 45pts (ACTUAL WINNER)")

print("\nWHY LAW SUPREME WON BUT SCORED LOW:")
print("  - Odds: 8.8 (4.15 away from optimal 4.65) = 0pts optimal odds bonus")
print("  - Form: Outside our ideal consistency range")
print("  - The Dark Baron had better form (4 places) and optimal odds position")

print("\nKEY LEARNING:")
print("  - Comprehensive analysis gave The Dark Baron 28pts more (73 vs 45)")
print("  - Law Supreme was at edge of sweet spot (8.8, near 9.0 max)")
print("  - Shows sweet spot range is correct (Law Supreme WAS in 3-9)")
print("  - But comprehensive scoring favored consistency over higher odds")

print("\n" + "="*80)
print("WOLVERHAMPTON TODAY: 4 WINS, 1 LOSS")
print("="*80)
print("✓ Take The Boat @ 4.0 - WIN (pre-comprehensive)")
print("✓ Horace Wallace @ 4.0 - WIN (pre-comprehensive)")
print("✓ My Genghis @ 5.0 - WIN (pre-comprehensive)")
print("✓ Mr Nugget @ 6.0 - WIN (pre-comprehensive)")
print("✗ The Dark Baron @ 5.1 - LOSS (comprehensive analysis)")
print("\nSweet Spot: 10/11 = 90.9% (still excellent)")
print("Comprehensive: 0/1 = 0% (first test)")
print("="*80)
