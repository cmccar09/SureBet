"""
Analyze Taunton 13:40 Race Result - February 3, 2026

ACTUAL RESULT:
1st: Talk To The Man (IRE) @ 11/4 (3.75) - J: Harry Cobden, T: Paul Nicholls
2nd: Kings Champion (FR) @ 10/11 (1.91) - J: Sean Bowen, T: Olly Murphy (FAVORITE)
3rd: Marhaba Million (IRE) @ 150/1
4th: Crest Of Stars (IRE) - odds not shown, previously 5.4

Going: Heavy (Soft in places)
Class: 4
Runners: 9 declared, 8 ran

ANALYSIS FOCUS:
1. Did we pick Talk To The Man (winner at 3.75 odds)?
2. Would quality favorite logic help Kings Champion (2nd at 1.91)?
3. Why did Crest Of Stars (44/100) finish 4th despite high score?
4. Going prediction: We predicted Soft (-5), actual Heavy
"""

import boto3
from decimal import Decimal
import json

def get_taunton_13_40_horses():
    """Get all horses from Taunton 13:40 race"""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('SureBetBets')
    
    response = table.scan(
        FilterExpression='#dt = :date AND track = :track AND race_time = :time',
        ExpressionAttributeNames={'#dt': 'date'},
        ExpressionAttributeValues={
            ':date': '2026-02-03',
            ':track': 'Taunton',
            ':time': '13:40'
        }
    )
    
    return response.get('Items', [])

def analyze_winner_logic():
    """Analyze why Talk To The Man won and if we would have picked it"""
    horses = get_taunton_13_40_horses()
    
    print("\n" + "="*80)
    print("TAUNTON 13:40 RACE ANALYSIS")
    print("="*80)
    
    # Find key horses
    winner = None
    second = None
    crest = None
    
    for horse in horses:
        name = horse.get('horse_name', '')
        if 'Talk To The Man' in name:
            winner = horse
        elif 'Kings Champion' in name:
            second = horse
        elif 'Crest Of Stars' in name:
            crest = horse
    
    print("\n1. WINNER ANALYSIS: Talk To The Man")
    print("-" * 80)
    if winner:
        score = winner.get('confidence_score', 0)
        odds = float(winner.get('odds', 0))
        form = winner.get('form', '')
        jockey = winner.get('jockey', '')
        trainer = winner.get('trainer', '')
        
        print(f"Horse: {winner.get('horse_name')}")
        print(f"Odds: {odds:.2f} (Starting Price: 11/4 = 3.75)")
        print(f"Form: {form}")
        print(f"Jockey: {jockey}")
        print(f"Trainer: {trainer}")
        print(f"Confidence Score: {score}/100")
        print(f"UI Threshold: 45+")
        print(f"Result: {'PICKED ✅' if score >= 45 else 'NOT PICKED ❌'}")
        
        # Check quality favorite logic
        if 1.5 <= odds < 3.0:
            print(f"\n⚠️ FAVORITE RANGE CHECK (1.5-3.0): {odds:.2f} is NOT in range")
        elif 3.0 <= odds < 4.5:
            print(f"\n✓ SWEET SPOT RANGE (3.0-4.5): {odds:.2f} ✅")
        
        # Analyze why score was low
        if score < 45:
            print(f"\nWHY NOT PICKED:")
            print(f"- Score: {score}/100 (need 45+)")
            print(f"- Gap: {45 - score} points short")
            print(f"- Form analysis needed...")
    else:
        print("❌ Talk To The Man NOT FOUND in database!")
    
    print("\n2. SECOND PLACE ANALYSIS: Kings Champion (FAVORITE)")
    print("-" * 80)
    if second:
        score = second.get('confidence_score', 0)
        odds = float(second.get('odds', 0))
        form = second.get('form', '')
        
        print(f"Horse: {second.get('horse_name')}")
        print(f"Odds: {odds:.2f} (Starting Price: 10/11 = 1.91)")
        print(f"Form: {form}")
        print(f"Confidence Score: {score}/100")
        print(f"Result: {'PICKED ✅' if score >= 45 else 'NOT PICKED ❌'}")
        
        # Check quality favorite logic
        if 1.5 <= odds < 3.0:
            lto_winner = form and form[0] == '1'
            places_count = sum(1 for c in form[:6] if c.isdigit() and 1 <= int(c) <= 3)
            wins_count = form[:6].count('1')
            
            print(f"\n✓ FAVORITE RANGE (1.5-3.0): {odds:.2f}")
            print(f"Quality Favorite Check:")
            print(f"  - LTO Winner: {'YES ✅' if lto_winner else 'NO ❌'} (form: {form[:1]})")
            print(f"  - Wins in last 6: {wins_count}")
            print(f"  - Places in last 6: {places_count}")
            
            if lto_winner or (wins_count >= 2 and places_count >= 3):
                print(f"  - Quality Favorite: YES ✅ (+20 bonus)")
                print(f"  - Adjusted Score: {score + 20}/100")
                print(f"  - Would be picked: {'YES ✅' if score + 20 >= 45 else 'NO ❌'}")
            else:
                print(f"  - Quality Favorite: NO ❌")
    else:
        print("❌ Kings Champion NOT FOUND in database!")
    
    print("\n3. CREST OF STARS ANALYSIS (Finished 4th)")
    print("-" * 80)
    if crest:
        score = crest.get('confidence_score', 0)
        odds = float(crest.get('odds', 0))
        form = crest.get('form', '')
        
        print(f"Horse: {crest.get('horse_name')}")
        print(f"Odds: {odds:.2f}")
        print(f"Form: {form}")
        print(f"Confidence Score: {score}/100")
        print(f"Result: Finished 4th despite high score (1 point below threshold)")
        
        if score >= 44:
            print(f"\n⚠️ HIGH SCORE BUT FAILED TO WIN:")
            print(f"- Just {45 - score} point(s) below UI threshold")
            print(f"- Demonstrates not all high-scoring horses win")
            print(f"- Heavy going may have impacted performance")
    else:
        print("❌ Crest Of Stars NOT FOUND in database!")
    
    print("\n4. GOING PREDICTION ACCURACY")
    print("-" * 80)
    print("Predicted: Soft (-5 adjustment)")
    print("Actual: Heavy (Soft in places)")
    print("Rainfall: 16.6mm over 3 days")
    print("\nAssessment:")
    print("- Under-predicted by one category (Soft → Heavy)")
    print("- 16.6mm is borderline for Heavy threshold")
    print("- Consider adjusting Heavy threshold to 15mm+ instead of 20mm+")
    print("- OR acceptable margin given 'Soft in places' description")
    
    print("\n5. OVERALL RACE SUMMARY")
    print("-" * 80)
    all_horses = sorted(horses, key=lambda x: x.get('confidence_score', 0), reverse=True)
    
    print(f"\nAll {len(all_horses)} horses by confidence score:")
    for i, h in enumerate(all_horses, 1):
        name = h.get('horse_name', 'Unknown')
        score = h.get('confidence_score', 0)
        odds = float(h.get('odds', 0))
        result = '🏆 WINNER' if 'Talk To The Man' in name else ('🥈 2nd' if 'Kings Champion' in name else ('🥉 3rd' if 'Marhaba' in name else ''))
        ui_pick = '✅ UI' if score >= 45 else ''
        
        print(f"{i}. {name:30s} Score: {score:3}/100  Odds: {odds:5.1f}  {result} {ui_pick}")
    
    print("\n" + "="*80)
    print("KEY FINDINGS:")
    print("="*80)
    print("1. Winner (Talk To The Man) scored below threshold - need form analysis")
    print("2. Favorite (Kings Champion) finished 2nd - check quality favorite logic")
    print("3. High scorer (Crest Of Stars) finished 4th - shows score ≠ guarantee")
    print("4. Going prediction slightly under - consider threshold adjustment")
    print("5. Database completeness: Need to verify all 8 runners captured")

if __name__ == '__main__':
    analyze_winner_logic()
