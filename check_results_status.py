"""Quick check of today's picks results status"""
import boto3

db = boto3.resource('dynamodb', region_name='us-east-1')
table = db.Table('SureBetBets')

# Scan for today's picks
resp = table.scan(
    FilterExpression='begins_with(bet_date, :d)',
    ExpressionAttributeValues={':d': '2026-01-10'}
)

items = resp.get('Items', [])
print(f"\n{'='*70}")
print(f"TODAY'S PICKS: {len(items)} total")
print(f"{'='*70}\n")

wins = [p for p in items if p.get('outcome') == 'WON']
losses = [p for p in items if p.get('outcome') in ['LOST', 'PLACED']]
pending = [p for p in items if p.get('outcome') is None]

print(f"Results Status:")
print(f"  WIN: {len(wins)}")
print(f"  LOSS: {len(losses)}")
print(f"  PENDING: {len(pending)}")
print()

if losses:
    print(f"\nResults:")
    for p in losses:
        outcome_display = "PLACED" if p['outcome'] == 'PLACED' else "LOST"
        pnl = p.get('profit_loss', 0)
        print(f"  • {p['horse']} @ {p['course']} - {outcome_display} ({float(pnl):+.2f} units)")

if pending:
    print(f"\nPending Results ({len(pending)} picks):")
    for p in pending[:5]:
        print(f"  • {p['horse']} @ {p['course']} - {p.get('race_time', 'Time unknown')}")
    if len(pending) > 5:
        print(f"  ... and {len(pending) - 5} more")

print(f"\n{'='*70}\n")
