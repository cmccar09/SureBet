"""
Carlisle 14:00 Result Analysis - Feb 3, 2026
Winner: First Confession (we had 0/100 - NOT ANALYZED)
Our Pick: Thank You Maam (49/100) - came 3RD
"""
import boto3
import json

# Always use eu-west-1
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("="*100)
print("CARLISLE 14:00 - RESULT ANALYSIS")
print("="*100)

print("\nACTUAL RESULT:")
print("  1st: First Confession (J: Brendan Powell, T: Joe Tizzard)")
print("       Form: 1P-335F")
print("  2nd: Della Casa Lunga (J: Richard Patrick)")
print("       Form: 157-734")
print("  3rd: Thank You Maam (J: Finn Lambert, T: Georgina Nicholls) ** OUR PICK **")
print("       Form: 21312-7")
print("  4th: Scarlet Jet (J: Bruce Lynn)")
print("       Form: 6431-48")

print("\nRace Details:")
print("  Distance: 2m5f Beginners Chase")
print("  Class: 3")
print("  Going: Good to Soft (Good in places)")
print("  Runners: 4")

# Get all horses from database
response = table.query(
    KeyConditionExpression='bet_date = :date',
    FilterExpression='course = :course',
    ExpressionAttributeValues={
        ':date': '2026-02-03',
        ':course': 'Carlisle'
    }
)

carlisle_1400 = [item for item in response['Items'] if '14:00' in item.get('race_time', '')]

print("\n" + "="*100)
print("OUR ANALYSIS")
print("="*100)

if carlisle_1400:
    print(f"\nHorses in database: {len(carlisle_1400)}")
    
    # Find each horse
    first_confession = None
    della_casa = None
    thank_you_maam = None
    scarlet_jet = None
    
    for item in carlisle_1400:
        horse = item.get('horse', '')
        if 'First Confession' in horse:
            first_confession = item
        elif 'Della Casa Lunga' in horse:
            della_casa = item
        elif 'Thank You Maam' in horse:
            thank_you_maam = item
        elif 'Scarlet Jet' in horse:
            scarlet_jet = item
    
    # Analyze winner
    print("\n" + "-"*100)
    print("1. FIRST CONFESSION (WINNER)")
    print("-"*100)
    
    if first_confession:
        conf = float(first_confession.get('confidence', 0))
        odds = float(first_confession.get('odds', 0))
        tags = first_confession.get('tags', [])
        
        print(f"\nOur confidence: {conf}/100")
        print(f"Our odds: {odds}")
        print(f"Form: 1P-335F")
        print(f"Tags: {tags}")
        
        if conf == 0:
            print("\n[ISSUE] This horse was NOT ANALYZED (0/100 confidence)")
            print("Even though it was in the database, no confidence score was calculated")
            
            # Check why
            print("\nChecking database record...")
            print(f"  Has odds: {odds > 0}")
            print(f"  Has form: {first_confession.get('form', 'N/A')}")
            print(f"  Has trainer: {first_confession.get('trainer', 'N/A')}")
            print(f"  Analyzed at: {first_confession.get('analyzed_at', 'N/A')}")
            
            # Form analysis
            form = "1P-335F"
            print(f"\nForm analysis for {form}:")
            print("  1 = Last time out WINNER")
            print("  P = Pulled up previously")
            print("  F = Fell in last chase")
            print("  LTO winner should trigger quality analysis")
        else:
            print(f"\nConfidence: {conf}/100")
            if conf >= 45:
                print("[YES] Would have been picked")
            else:
                print(f"[NO] Below threshold ({conf} < 45)")
    else:
        print("\n[ERROR] First Confession NOT FOUND in database")
    
    # Analyze 2nd place
    print("\n" + "-"*100)
    print("2. DELLA CASA LUNGA (2ND)")
    print("-"*100)
    
    if della_casa:
        conf = float(della_casa.get('confidence', 0))
        odds = float(della_casa.get('odds', 0))
        print(f"\nOur confidence: {conf}/100")
        print(f"Our odds: {odds} (actual: 3.05 from earlier check)")
        print(f"Form: 157-734")
        
        if conf == 0:
            print("[NOT ANALYZED] 0/100 confidence")
    else:
        print("\n[ERROR] Della Casa Lunga NOT FOUND in database")
    
    # Analyze our pick (3rd place)
    print("\n" + "-"*100)
    print("3. THANK YOU MAAM (3RD - OUR PICK)")
    print("-"*100)
    
    if thank_you_maam:
        conf = float(thank_you_maam.get('confidence', 0))
        odds = float(thank_you_maam.get('odds', 0))
        tags = thank_you_maam.get('tags', [])
        
        print(f"\nOur confidence: {conf}/100 [WE PICKED THIS]")
        print(f"Our odds: {odds}")
        print(f"Form: 21312-7")
        print(f"Tags: {tags}")
        
        # Get detailed analysis
        all_horses = thank_you_maam.get('all_horses_analyzed', {})
        if all_horses:
            value_analysis = all_horses.get('value_analysis', [])
            for runner in value_analysis:
                if 'Thank You Maam' in runner.get('runner_name', ''):
                    print(f"\nValue Analysis:")
                    print(f"  Value Score: {runner.get('value_score')}/10")
                    print(f"  Edge: {runner.get('edge_percentage')}%")
                    print(f"  True Probability: {runner.get('true_probability')}")
                    print(f"  Implied Probability: {runner.get('implied_probability')}")
                    print(f"  Reasoning: {runner.get('reasoning')}")
        
        print(f"\nWhy Now: {thank_you_maam.get('why_now', 'N/A')}")
        print(f"Decision Rating: {thank_you_maam.get('decision_rating', 'N/A')}")
        
        print("\n[RESULT] Came 3RD - Lost bet")
        print("Form 21312-7 shows:")
        print("  Recent: 2nd, 1st, 3rd, 1st, 2nd = very consistent")
        print("  But last run was 7th (poor)")
        print("  May have been outclassed or off form")
    else:
        print("\n[ERROR] Thank You Maam NOT FOUND in database")
    
    # Compare all horses
    print("\n" + "="*100)
    print("RACE COMPARISON")
    print("="*100)
    
    print(f"\n{'Finish':<8} {'Horse':<25} {'Confidence':<12} {'Odds':<10} {'Form':<15}")
    print("-"*100)
    
    horses = [
        ('1st', 'First Confession', first_confession),
        ('2nd', 'Della Casa Lunga', della_casa),
        ('3rd', 'Thank You Maam', thank_you_maam),
        ('4th', 'Scarlet Jet', scarlet_jet)
    ]
    
    for finish, name, item in horses:
        if item:
            conf = float(item.get('confidence', 0))
            odds = float(item.get('odds', 0))
            form = item.get('form', 'N/A')[:15]
            
            marker = " **PICK**" if conf >= 45 else ""
            print(f"{finish:<8} {name:<25} {conf:>5.1f}/100   {odds:>7.2f}  {form:<15}{marker}")
        else:
            print(f"{finish:<8} {name:<25} NOT IN DATABASE")

else:
    print("\n[ERROR] No Carlisle 14:00 horses found in database")

print("\n" + "="*100)
print("LESSONS LEARNED")
print("="*100)

print("""
1. [CRITICAL ISSUE] WINNER NOT ANALYZED
   - First Confession was in database but had 0/100 confidence
   - LTO winner (form shows '1' at start) should have been flagged
   - Form: 1P-335F = Last run WON, before that pulled up/fell
   - This is a HIGH PRIORITY horse that was missed

2. [ANALYSIS INCOMPLETE] Only 1 of 4 horses analyzed
   - Thank You Maam: 49/100 (analyzed)
   - First Confession: 0/100 (not analyzed) - WON
   - Della Casa Lunga: 0/100 (not analyzed) - 2nd
   - Scarlet Jet: 0/100 (not analyzed) - 4th
   - 75% of race not analyzed before race time

3. [PICK PERFORMANCE] Thank You Maam came 3rd
   - Good recent form (21312) but last run was 7th
   - May have flagged the poor last run (7)
   - Confidence 49/100 was marginal
   - Small field (4 runners) = higher variance

4. [FORM ANALYSIS FAILURE]
   - First Confession: '1' at start of form = LTO WINNER
   - Should have triggered quality analysis
   - May be in database but form parsing didn't work
   - Need to verify form data capture for all horses

5. [WORKFLOW TIMING]
   - Race at 14:00
   - Only 1 of 4 horses analyzed
   - Suggests workflow is too slow or analysis incomplete
   - Need faster processing for small fields

RECOMMENDATIONS:

A. IMMEDIATE:
   - Investigate why First Confession wasn't analyzed
   - Check form parsing for '1P-335F' pattern
   - Verify all horses have form data in database

B. SYSTEM FIXES:
   - Prioritize LTO winners in analysis
   - Flag races with <50% horses analyzed
   - Ensure small fields (4 runners) get full analysis
   - Add pre-race validation check

C. FUTURE:
   - Consider avoiding 4-runner fields (high variance)
   - Weight recent form more heavily (7th last run = red flag)
   - Add "last run" specific analysis
""")

print("="*100)
