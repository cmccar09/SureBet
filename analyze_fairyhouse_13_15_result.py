"""
Analyze Fairyhouse 13:15 Result - February 3, 2026
Check our predictions vs actual result
"""
import boto3
from decimal import Decimal

db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

# Get all picks for today
response = table.query(
    KeyConditionExpression='bet_date = :date',
    ExpressionAttributeValues={':date': '2026-02-03'}
)

# Filter for Fairyhouse around 13:15
fairyhouse_picks = [
    p for p in response['Items'] 
    if 'Fairyhouse' in p.get('course', '') and '13:' in p.get('race_time', '')
]

print(f"\n{'='*80}")
print(f"FAIRYHOUSE 13:15 RESULT ANALYSIS")
print(f"Going: SOFT (as predicted: -5 adjustment + February bias)")
print(f"{'='*80}\n")

print("ACTUAL RESULT:")
print("1st: Dunsy Rock (IRE) @ 9/4")
print("2nd: Likealightswitch (IRE) @ 11/4")
print("3rd: Alliteration (IRE) @ 10/3")
print("4th: Louie's Folly @ 14/1")

print(f"\n{'='*80}")
print(f"OUR PREDICTIONS FOR THIS RACE:")
print(f"{'='*80}\n")

if fairyhouse_picks:
    for pick in sorted(fairyhouse_picks, key=lambda x: float(x.get('confidence', 0)), reverse=True):
        horse = pick['horse']
        odds = float(pick['odds'])
        score = float(pick.get('confidence', 0))
        ui_pick = pick.get('show_in_ui', False)
        
        # Check if winner
        if 'Dunsy Rock' in horse:
            result = "✅ WINNER!"
        elif 'Likealightswitch' in horse:
            result = "✅ 2nd PLACE"
        elif 'Alliteration' in horse:
            result = "✅ 3rd PLACE"
        elif "Louie's Folly" in horse or 'Louie' in horse:
            result = "⚠️ 4th"
        else:
            result = "❌ Did not place"
        
        ui_status = "[UI PICK]" if ui_pick else "[Learning]"
        print(f"{ui_status} {horse} @ {odds:.1f}")
        print(f"         Score: {score:.0f}/100 → {result}")
        print()
else:
    print("❌ NO PICKS FOUND FOR THIS RACE")
    print("\nPossible reasons:")
    print("- Race not analyzed (time/data issues)")
    print("- All horses scored below threshold")
    print("- Race time mismatch in database")

# Check response_horses.json for this race
print(f"\n{'='*80}")
print("Checking race data file...")
print(f"{'='*80}\n")

try:
    import json
    with open('response_horses.json', 'r') as f:
        data = json.load(f)
    
    fairyhouse_races = [
        r for r in data.get('races', [])
        if 'Fairyhouse' in r.get('venue', '') and '13:' in r.get('start_time', '')
    ]
    
    if fairyhouse_races:
        race = fairyhouse_races[0]
        print(f"✓ Found race: {race.get('venue')} {race.get('start_time')}")
        print(f"  Market: {race.get('market_name')}")
        print(f"  Runners: {len(race.get('runners', []))}")
        
        # Check if winner was in our data
        runners = race.get('runners', [])
        winner_data = None
        for runner in runners:
            if 'Dunsy Rock' in runner.get('name', ''):
                winner_data = runner
                break
        
        if winner_data:
            print(f"\n✓ Winner was in our data:")
            print(f"  Name: {winner_data.get('name')}")
            print(f"  Odds: {winner_data.get('odds')}")
            print(f"  Form: {winner_data.get('form')}")
            print(f"  Trainer: {winner_data.get('trainer')}")
            
            # Check why it wasn't picked (if it wasn't)
            if not fairyhouse_picks or not any('Dunsy Rock' in p['horse'] for p in fairyhouse_picks):
                print(f"\n⚠️ LEARNING OPPORTUNITY: Winner not picked")
                print(f"  Form: {winner_data.get('form')} - Analyze this pattern")
                print(f"  Odds: {winner_data.get('odds')} - Was it in sweet spot?")
        else:
            print(f"\n❌ Winner NOT in our race data (data quality issue)")
    else:
        print("❌ Race not found in response_horses.json")
        
except Exception as e:
    print(f"❌ Error reading race data: {e}")

print(f"\n{'='*80}")
print("WEATHER/GOING ANALYSIS:")
print(f"{'='*80}\n")
print("Official Going: SOFT")
print("Our Prediction: SOFT (-5 adjustment)")
print("  - Rainfall: 15.0mm (3 days)")
print("  - Seasonal: February (-5 bias)")
print("  - Final: -5 (Soft)")
print("\n✓ GOING PREDICTION ACCURATE")
print("\nWinner Analysis:")
print("- Dunsy Rock won on SOFT going @ 9/4 (2.25 decimal)")
print("- Odds suggest stamina/form suited conditions")
print("- Form analysis needed to determine soft ground suitability")
