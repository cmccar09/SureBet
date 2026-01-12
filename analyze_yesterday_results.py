import boto3
from datetime import datetime, timedelta

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("\n" + "="*80)
print("YESTERDAY'S RESULTS SUMMARY (with EW logic)")
print("="*80 + "\n")

# Get yesterday's picks
yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

response = table.scan(
    FilterExpression='#dt = :date',
    ExpressionAttributeNames={'#dt': 'date'},
    ExpressionAttributeValues={':date': yesterday}
)

picks = response.get('Items', [])

if not picks:
    print(f"No picks found for {yesterday}")
    exit(0)

# Analyze results
wins = 0
losses = 0
non_runners = 0

total_stake = 0
total_return = 0

for pick in picks:
    result = pick.get('actual_result', 'PENDING')
    horse = pick.get('horse', 'Unknown')
    course = pick.get('course', 'Unknown')
    conf = pick.get('combined_confidence', 0)
    roi = pick.get('roi', 0)
    bet_type = pick.get('bet_type', 'WIN')
    race_type = pick.get('sport', 'horses')
    odds = pick.get('odds', 0)
    ew_fraction = pick.get('ew_fraction', 0.25)
    ew_places = pick.get('ew_places', 3)
    
    stake = 1  # Assume 1 unit per bet (0.5 win + 0.5 place for EW)
    total_stake += stake
    
    if result == 'WON':
        wins += 1
        if bet_type == 'EW':
            # EW bet returns: win part (0.5 * odds) + place part (0.5 * odds * fraction)
            # But if horse won, both parts pay
            win_return = 0.5 * float(odds)
            place_return = 0.5 * (float(odds) * float(ew_fraction))
            total_return += win_return + place_return
        else:  # WIN
            total_return += stake * float(odds)
        status = "WIN"
    elif result == 'LOST':
        losses += 1
        status = "LOST"
    elif result == 'NON_RUNNER':
        non_runners += 1
        total_stake -= stake  # Refund
        status = "NON-RUNNER"
    else:
        status = "PENDING"
    
    print(f"{status:12} | {horse:25} | {course:20} | {race_type:10} | {bet_type:5} | Conf: {conf:5.1f}% | ROI: {roi:6.1f}%")

print(f"\n{'='*80}")
print(f"PERFORMANCE:")
print(f"  Total bets: {len(picks)}")
print(f"  Wins: {wins}")
print(f"  Losses: {losses}")
print(f"  Non-runners: {non_runners}")

if wins + losses > 0:
    win_rate = (wins / (wins + losses)) * 100
    print(f"  Win rate: {win_rate:.1f}%")
    
    profit_loss = total_return - total_stake
    roi_actual = (profit_loss / total_stake) * 100 if total_stake > 0 else 0
    
    print(f"\n  Total stake: {total_stake:.2f} units")
    print(f"  Total return: {total_return:.2f} units")
    print(f"  Profit/Loss: {profit_loss:+.2f} units")
    print(f"  Actual ROI: {roi_actual:+.1f}%")

print(f"{'='*80}\n")
