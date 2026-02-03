"""
Update 17:30 Wolverhampton result - WINNER!
"""
import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("=" * 80)
print("17:30 WOLVERHAMPTON RESULT - WIN!")
print("=" * 80)

# Race details
race_time_iso = "2026-02-03T17:30:00.000Z"
race_date = "2026-02-03"
winner = "Harbour Vision"
odds = 6.0
stake = 30  # From UI calculation

# Find our pick - search by date and horse name
response = table.query(
    KeyConditionExpression='bet_date = :date',
    FilterExpression='horse = :h',
    ExpressionAttributeValues={
        ':date': race_date,
        ':h': winner
    }
)

items = response.get('Items', [])

if items:
    pick = items[0]
    print(f"\nOur Pick: {winner}")
    print(f"Confidence: {pick.get('combined_confidence', 'N/A')}/100 (FAIR)")
    print(f"Odds: {odds}/1")
    print(f"Stake: €{stake}")
    print(f"Form: {pick.get('form', 'N/A')}")
    
    # Calculate profit
    profit = (stake * odds) - stake
    print(f"\n{'=' * 80}")
    print(f"RESULT: WIN!")
    print(f"Return: €{stake * odds:.2f}")
    print(f"Profit: €{profit:.2f}")
    print(f"{'=' * 80}")
    
    # Update database
    table.update_item(
        Key={
            'bet_date': pick['bet_date'],
            'bet_id': pick['bet_id']
        },
        UpdateExpression='SET outcome = :outcome, actual_odds = :odds, profit = :profit, result_time = :time',
        ExpressionAttributeValues={
            ':outcome': 'win',
            ':odds': Decimal(str(odds)),
            ':profit': Decimal(str(profit)),
            ':time': datetime.now().isoformat()
        }
    )
    
    print("\n✓ Database updated")
    
else:
    print(f"\n⚠️ Pick not found in database")
    print(f"But the winner was: {winner} at {odds}/1")

print(f"\n{'=' * 80}")
print("RACE ANALYSIS")
print(f"{'=' * 80}")
print("\nFull Result:")
print("1st: Harbour Vision (6/1) - OUR PICK ✓")
print("2nd: Bomb Squad (9/2)")
print("3rd: How's The Guvnor (4/5 FAV) - Favorite beaten!")
print("4th: Secret Road (5/1)")

print(f"\n{'=' * 80}")
print("LEARNING POINTS")
print(f"{'=' * 80}")
print("✓ System correctly identified value despite FAIR (56/100) confidence")
print("✓ Favorite (How's The Guvnor 4/5) finished 3rd - good value spot")
print("✓ 6/1 winner from 9-runner field")
print("✓ Class 6, Standard going")
print(f"{'=' * 80}\n")
