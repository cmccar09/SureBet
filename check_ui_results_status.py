import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

items = table.scan().get('Items', [])

# Get UI picks
ui_picks = [i for i in items if i.get('show_in_ui') == True and '2026-02-04' in i.get('race_time', '')]

print(f"\n{'='*70}")
print(f"UI PICKS STATUS IN DATABASE")
print(f"{'='*70}\n")

print(f"Total UI picks today: {len(ui_picks)}\n")

completed = []
pending = []

for pick in sorted(ui_picks, key=lambda x: x.get('race_time', '')):
    outcome = pick.get('outcome')
    horse = pick.get('horse', 'Unknown')
    race_time = pick.get('race_time', '').split('T')[1][:5] if 'T' in pick.get('race_time', '') else 'Unknown'
    course = pick.get('course', 'Unknown')
    score = pick.get('combined_confidence', 0)
    
    if outcome in ['WON', 'PLACED', 'LOST']:
        completed.append({
            'time': race_time,
            'course': course,
            'horse': horse,
            'outcome': outcome,
            'score': score
        })
    else:
        pending.append({
            'time': race_time,
            'course': course,
            'horse': horse,
            'score': score
        })

print(f"Completed races: {len(completed)}")
print(f"Pending races: {len(pending)}\n")

print(f"{'='*70}")
print(f"COMPLETED UI PICKS:")
print(f"{'='*70}\n")

for pick in completed:
    icon = '🏆' if pick['outcome'] == 'WON' else '✓' if pick['outcome'] == 'PLACED' else '✗'
    print(f"{icon} {pick['time']} {pick['course']:<15} {pick['horse']:<30} {pick['outcome']} ({pick['score']}/100)")

print(f"\n{'='*70}")
print(f"PENDING UI PICKS:")
print(f"{'='*70}\n")

for pick in pending:
    print(f"⏳ {pick['time']} {pick['course']:<15} {pick['horse']:<30} PENDING ({pick['score']}/100)")

print(f"\n{'='*70}")
print(f"CHECKING API ENDPOINT RESPONSE")
print(f"{'='*70}\n")

# Check what the API would return
print("Checking if API server is running...")
import subprocess
import time

# Try to check if API is running
try:
    result = subprocess.run(['curl', '-s', 'http://localhost:5001/api/results/today'], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0 and result.stdout:
        print("✓ API server is running")
        print("\nAPI Response:")
        print(result.stdout[:500])
    else:
        print("⚠️ API server may not be running or not responding")
        print(f"Return code: {result.returncode}")
except Exception as e:
    print(f"⚠️ Could not check API: {e}")

print(f"\n{'='*70}\n")
