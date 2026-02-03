"""
Analyze Fairyhouse 14:25 result - Feb 3, 2026
"""
import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("="*80)
print("FAIRYHOUSE 14:25 RESULT ANALYSIS")
print("="*80)

# Get all horses from this race
response = table.query(
    KeyConditionExpression='bet_date = :date',
    FilterExpression='course = :course',
    ExpressionAttributeValues={
        ':date': '2026-02-03',
        ':course': 'Fairyhouse'
    }
)

items = response.get('Items', [])
race_horses = [item for item in items if '14:25' in item.get('race_time', '') or 'T14:25' in item.get('race_time', '')]

print(f"\nFound {len(race_horses)} horses in database for this race")

# Actual result
result = {
    '1st': ('Oldschool Outlaw', '1/2'),
    '2nd': ('Place De La Nation', '13/8'),
    '3rd': ('Carry On Heidi', '25/1'),
    '4th': ('Early Bird', '66/1')
}

print("\nACTUAL RESULT:")
for pos, (horse, odds) in result.items():
    print(f"  {pos}: {horse} @ {odds}")

print("\nOUR ANALYSIS:")
if race_horses:
    # Group by horse (deduplicate)
    horses_dict = {}
    for item in race_horses:
        horse_name = item.get('horse', '')
        if horse_name not in horses_dict:
            horses_dict[horse_name] = item
        else:
            # Keep highest confidence
            try:
                existing_conf = float(horses_dict[horse_name].get('confidence', 0))
                new_conf = float(item.get('confidence', 0))
                if new_conf > existing_conf:
                    horses_dict[horse_name] = item
            except:
                pass
    
    # Sort by confidence
    sorted_horses = sorted(horses_dict.values(), 
                          key=lambda x: float(x.get('confidence', 0)) if str(x.get('confidence', '0')).replace('.','').isdigit() else 0, 
                          reverse=True)
    
    print(f"\n  Total horses analyzed: {len(sorted_horses)}/6 ({len(sorted_horses)/6*100:.0f}%)")
    
    for item in sorted_horses:
        horse = item.get('horse', '')
        try:
            conf = float(item.get('confidence', 0))
        except:
            conf = 0
        form = item.get('form', '')
        odds = item.get('odds', 0)
        show_ui = item.get('show_in_ui', False)
        
        # Check if this horse placed
        placed = ""
        for pos, (result_horse, result_odds) in result.items():
            if horse.lower() in result_horse.lower() or result_horse.lower() in horse.lower():
                placed = f" [{pos}]"
                break
        
        print(f"  {horse:30} {conf:5.0f}/100  Form: {form:10}  Odds: {odds}  UI: {show_ui}{placed}")
    
    # Check if winner was analyzed
    winner_analyzed = False
    winner_conf = 0
    for item in sorted_horses:
        if 'Oldschool Outlaw' in item.get('horse', ''):
            winner_analyzed = True
            try:
                winner_conf = float(item.get('confidence', 0))
            except:
                winner_conf = 0
            break
    
    print("\nKEY FINDINGS:")
    if winner_analyzed:
        print(f"  [+] Winner (Oldschool Outlaw) WAS analyzed: {winner_conf}/100")
        if winner_conf > 0:
            print(f"      System gave it a score - good!")
        else:
            print(f"      System gave it 0/100 - missed it!")
    else:
        print(f"  [-] Winner (Oldschool Outlaw) NOT analyzed")
    
    # Check Place De La Nation (2nd, favorite)
    pdn_analyzed = False
    pdn_conf = 0
    for item in sorted_horses:
        if 'Place De La Nation' in item.get('horse', ''):
            pdn_analyzed = True
            try:
                pdn_conf = float(item.get('confidence', 0))
            except:
                pdn_conf = 0
            break
    
    if pdn_analyzed:
        print(f"  Place De La Nation (2nd): {pdn_conf}/100")
    
    # Check validation
    analyzed_pct = len(sorted_horses) / 6 * 100
    if analyzed_pct < 75:
        print(f"\n  [VALIDATION] WOULD FAIL: Only {analyzed_pct:.0f}% analyzed (need >=75%)")
        print(f"  [ACTION] No bet would be placed (race incomplete)")
    else:
        print(f"\n  [VALIDATION] WOULD PASS: {analyzed_pct:.0f}% analyzed")
        
else:
    print("  No horses found in database")

print("="*80)
