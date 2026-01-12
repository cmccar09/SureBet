import boto3
from datetime import datetime, timedelta

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("\n" + "="*80)
print("TODAY'S RESULTS SUMMARY")
print("="*80 + "\n")

# Get today's picks
today = datetime.utcnow().strftime('%Y-%m-%d')

response = table.scan(
    FilterExpression='#dt = :date',
    ExpressionAttributeNames={'#dt': 'date'},
    ExpressionAttributeValues={':date': today}
)

picks = response.get('Items', [])

if not picks:
    print(f"No picks found for {today}")
    exit(0)

# Analyze results
wins = 0
losses = 0
non_runners = 0
pending = 0

total_stake = 0
total_return = 0

for pick in picks:
    result = pick.get('actual_result', 'PENDING')
    horse = pick.get('horse', 'Unknown')
    course = pick.get('course', 'Unknown')
    conf = pick.get('combined_confidence', 0)
    roi = pick.get('roi', 0)
    bet_type = pick.get('bet_type', 'WIN')
    odds = pick.get('odds', 0)
    
    stake = 1  # Assume 1 unit per bet
    total_stake += stake
    
    if result == 'WON':
        wins += 1
        if bet_type == 'WIN':
            total_return += stake * float(odds)
        else:  # EW
            total_return += stake * float(odds)  # Simplified
        status = "WIN"
    elif result == 'LOST':
        losses += 1
        status = "LOST"
    elif result == 'NON_RUNNER':
        non_runners += 1
        total_stake -= stake  # Refund
        status = "NON-RUNNER"
    else:
        pending += 1
        status = "PENDING"
    
    print(f"{status:12} | {horse:25} | {course:20} | Conf: {conf:5.1f}% | ROI: {roi:6.1f}% | {bet_type}")

print(f"\n{'='*80}")
print(f"PERFORMANCE:")
print(f"  Total bets: {len(picks)}")
print(f"  Wins: {wins}")
print(f"  Losses: {losses}")
print(f"  Non-runners: {non_runners}")
print(f"  Pending: {pending}")

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

# Get last 7 days stats
print("="*80)
print("LAST 7 DAYS PERFORMANCE")
print("="*80 + "\n")

seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')

response = table.scan(
    FilterExpression='#dt >= :start_date',
    ExpressionAttributeNames={'#dt': 'date'},
    ExpressionAttributeValues={':start_date': seven_days_ago}
)

all_picks = response.get('Items', [])

total_wins = 0
total_losses = 0
total_conf = 0
win_conf_total = 0
loss_conf_total = 0

for pick in all_picks:
    result = pick.get('actual_result', 'PENDING')
    conf = float(pick.get('combined_confidence', 0))
    
    if result == 'WON':
        total_wins += 1
        win_conf_total += conf
    elif result == 'LOST':
        total_losses += 1
        loss_conf_total += conf

if total_wins + total_losses > 0:
    overall_win_rate = (total_wins / (total_wins + total_losses)) * 100
    avg_win_conf = win_conf_total / total_wins if total_wins > 0 else 0
    avg_loss_conf = loss_conf_total / total_losses if total_losses > 0 else 0
    
    print(f"Total bets (7 days): {total_wins + total_losses}")
    print(f"Wins: {total_wins} | Losses: {total_losses}")
    print(f"Win rate: {overall_win_rate:.1f}%")
    print(f"\nAverage confidence:")
    print(f"  Winners: {avg_win_conf:.1f}%")
    print(f"  Losers: {avg_loss_conf:.1f}%")
    print(f"  Confidence gap: {avg_loss_conf - avg_win_conf:+.1f}% (AI overconfidence)")

print(f"\n{'='*80}\n")
