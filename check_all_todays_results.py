"""
Comprehensive result checker and learning updater
Check all UI picks for today and record outcomes
"""
import boto3
from datetime import datetime

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

print('\n' + '='*80)
print('CHECKING ALL UI PICKS FOR TODAY')
print('='*80)

response = table.query(
    KeyConditionExpression='bet_date = :date',
    FilterExpression='show_in_ui = :true',
    ExpressionAttributeValues={
        ':date': '2026-02-03',
        ':true': True
    }
)

picks = response['Items']
print(f'\nTotal UI picks: {len(picks)}')

# Group by status
pending = []
completed = []

for pick in sorted(picks, key=lambda x: x.get('race_time', '')):
    horse = pick.get('horse', 'Unknown')
    course = pick.get('course', 'Unknown')
    time = pick.get('race_time', '')
    outcome = pick.get('outcome')
    score = pick.get('comprehensive_score') or pick.get('combined_confidence', 0)
    
    # Extract just time
    if 'T' in time:
        time_str = time.split('T')[1].split('.')[0][:5]
    else:
        time_str = time
    
    if outcome and outcome != 'pending':
        completed.append({
            'time': time_str,
            'course': course,
            'horse': horse,
            'outcome': outcome,
            'score': score
        })
    else:
        pending.append({
            'time': time_str,
            'course': course,
            'horse': horse,
            'score': score
        })

print(f'\n{"="*80}')
print('COMPLETED RACES:')
print('='*80)

if completed:
    for p in completed:
        status = '✓ WIN' if p['outcome'] == 'win' else '✗ LOSS' if p['outcome'] == 'loss' else '≈ PLACE'
        print(f"{p['time']} {p['course']:20} {p['horse']:25} {p['score']:3}/100 {status}")
else:
    print('No results recorded yet')

print(f'\n{"="*80}')
print('PENDING RACES (still to run):')
print('='*80)

for p in pending:
    print(f"{p['time']} {p['course']:20} {p['horse']:25} {p['score']:3}/100")

print(f'\n{"="*80}')
print('SUMMARY')
print('='*80)
print(f'Total picks: {len(picks)}')
print(f'Completed: {len(completed)}')
print(f'Pending: {len(pending)}')

if completed:
    wins = sum(1 for p in completed if p['outcome'] == 'win')
    losses = sum(1 for p in completed if p['outcome'] == 'loss')
    print(f'Wins: {wins}')
    print(f'Losses: {losses}')
    print(f'Win rate: {wins/len(completed)*100:.1f}%')

print('\n' + '='*80)
print('NEXT STEPS:')
print('='*80)
print('1. Record remaining results as they finish')
print('2. Run: python auto_adjust_weights.py (learns from completed picks)')
print('3. Run: python complete_race_learning.py learn (learns from ALL race winners)')
