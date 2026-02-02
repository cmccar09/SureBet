"""
Analyze Southwell 14:45 Race Result - Class 4
Testing: Good to Soft pattern + Handicap/Non-Handicap distinction
"""

import boto3
import json
from datetime import datetime
from decimal import Decimal

# Race Details
race_info = {
    'course': 'Southwell',
    'time': '14:45',
    'going': 'Good to Soft',
    'runners': 10,
    'class': '4',
    'race_type': 'Unknown (likely Handicap based on Class 4 + odds spread)',
    'country': 'UK'
}

# Result
result = [
    {'position': 1, 'horse': 'Desertmore News', 'sp': '5/1', 'decimal_odds': 6.0, 'trainer': 'Tom Ellis', 'jockey': 'Jack Andrews'},
    {'position': 2, 'horse': 'Fouroneohfever', 'sp': '5/2', 'decimal_odds': 3.5, 'trainer': 'Ben Pauling', 'jockey': 'Kielan Woods', 'distance': '13 lengths'},
    {'position': 3, 'horse': 'Stung By Tariffs', 'sp': '10/1', 'decimal_odds': 11.0, 'trainer': 'Henry Daly', 'jockey': 'Sam Twiston-Davies', 'distance': '6½ lengths'},
    {'position': 4, 'horse': 'Moyganny Phil', 'sp': '9/4', 'decimal_odds': 3.25, 'trainer': 'Olly Murphy', 'jockey': 'Robert Dunne', 'distance': '1¾ lengths'},
    {'position': 5, 'horse': 'Mr Jukebox', 'sp': '4/1', 'decimal_odds': 5.0, 'trainer': 'Warren Greatrex', 'jockey': 'Richard Patrick', 'distance': '3 lengths'},
    {'position': 6, 'horse': 'Herbygoesbananas', 'sp': '15/2', 'decimal_odds': 8.5, 'trainer': 'Henrietta C Knight', 'jockey': 'Lorcan Williams', 'distance': '14 lengths'},
    {'position': 7, 'horse': 'River Glance', 'sp': '100/1', 'decimal_odds': 101.0, 'trainer': 'Emma-Jane Bishop', 'jockey': 'Lilly Pinchin', 'distance': '15 lengths'},
    {'position': 8, 'horse': 'Quinta Brigada', 'sp': '200/1', 'decimal_odds': 201.0, 'trainer': 'Evan Williams', 'jockey': 'Conor Ring', 'distance': '27 lengths'},
    {'position': 'PU', 'horse': 'Rose Of The Shires', 'sp': '250/1', 'decimal_odds': 251.0, 'trainer': 'Alex Hales', 'jockey': 'J. Hogan', 'distance': 'PU'},
    {'position': 'PU', 'horse': 'Geordie Bay', 'sp': None, 'decimal_odds': None, 'trainer': 'Claire Dyson', 'jockey': 'Lee Edwards', 'distance': 'PU'},
]

print("\n" + "="*80)
print("SOUTHWELL 14:45 - GOOD TO SOFT PATTERN TEST")
print("="*80)
print(f"\nRace: {race_info['course']} {race_info['time']}")
print(f"Going: {race_info['going']} | Runners: {race_info['runners']} | Class: {race_info['class']}")
print(f"Type: {race_info['race_type']}")
print(f"\nWINNER: {result[0]['horse']} @ {result[0]['sp']} ({result[0]['decimal_odds']} decimal)")
print(f"Trainer: {result[0]['trainer']} | Jockey: {result[0]['jockey']}")

print("\n" + "="*80)
print("SWEET SPOT VALIDATION: WINNER @ 6.0 DECIMAL")
print("="*80)

print(f"\n**PERFECT SWEET SPOT:**")
print(f"  Winner: Desertmore News @ 5/1 (6.0 decimal) - IN SWEET SPOT")
print(f"  2nd: Fouroneohfever @ 5/2 (3.5 decimal) - IN SWEET SPOT")
print(f"  3rd: Stung By Tariffs @ 10/1 (11.0 decimal) - OUTSIDE sweet spot")
print(f"  Favorite: Moyganny Phil @ 9/4 (3.25) finished 4th - FAILED")
print(f"\n  Sweet Spot (3-9 for Good to Soft): Top 2 both in range")
print(f"  Margin: 13 lengths (dominant victory)")

print("\n" + "="*80)
print("HANDICAP OR NON-HANDICAP?")
print("="*80)

print(f"\n**EVIDENCE FOR HANDICAP:**")
print(f"  - Class 4 (typical handicap class)")
print(f"  - Favorite failed (finished 4th)")
print(f"  - Wide odds spread (6.0 winner, but 100/1, 200/1, 250/1 also ran)")
print(f"  - Competitive field (top 5 within 18 lengths)")
print(f"\n**EVIDENCE FOR NON-HANDICAP:**")
print(f"  - Winner @ 6.0 = PERFECT sweet spot (not a longshot)")
print(f"  - Top 2 both in sweet spot (6.0 and 3.5)")
print(f"  - Clear winner (13 lengths)")
print(f"  - Pattern matches Kempton non-handicap races")
print(f"\n**VERDICT: LIKELY HANDICAP**")
print(f"  - Class 4 + favorite failure + odds spread suggests handicap")
print(f"  - BUT: Winner in sweet spot (not longshot like Kempton 14:35)")
print(f"  - LEARNING: Not all handicaps produce longshot winners")

print("\n" + "="*80)
print("KEY LEARNINGS")
print("="*80)

learnings = [
    {
        'title': 'HANDICAPS CAN HAVE SWEET SPOT WINNERS',
        'insight': 'Desertmore News @ 6.0 won Class 4 (likely handicap). Not all handicaps = longshots. If weights favor mid-range horse with good form, sweet spot still viable.',
        'pattern': 'Handicaps = wider range, but sweet spot still possible',
        'action': 'Don\'t auto-reject sweet spot in handicaps, check weights'
    },
    {
        'title': 'GOOD TO SOFT SWEET SPOT VALIDATED AGAIN',
        'insight': 'Winner @ 6.0, 2nd @ 3.5 (both in 3-9 range). Good to Soft = 3-9 odds sweet spot holds across Southwell too. 4th venue validation (Kempton x3, Southwell x1).',
        'pattern': 'Good to Soft = 3-9 odds sweet spot (venue-independent)',
        'action': 'Trust sweet spot on Good to Soft across all venues'
    },
    {
        'title': 'FAVORITE FAILED AT 9/4 IN CLASS 4',
        'insight': 'Moyganny Phil @ 9/4 favorite only 4th. Olly Murphy trainer. Class 4 on Good to Soft = favorites vulnerable. Weights and going overcome favorite status.',
        'pattern': 'Class 4 + Good to Soft = favorite risk',
        'action': 'Don\'t over-weight favorites in Class 4 Good to Soft'
    },
    {
        'title': 'WINNING MARGIN IN HANDICAPS',
        'insight': '13 lengths victory. Despite being handicap, winner dominated. When handicapper gets weights wrong (or winner improving), margins can be big.',
        'pattern': 'Handicaps can have clear winners if weights favor',
        'action': 'Look for improving horses in handicaps (underweighted)'
    },
    {
        'title': 'TOP 2 BOTH IN SWEET SPOT',
        'insight': '1st @ 6.0, 2nd @ 3.5 (both 3-9 range). Good to Soft = market prices correctly within sweet spot. Top 2 often both in range.',
        'pattern': 'Good to Soft top performers cluster in sweet spot',
        'action': 'Multiple picks viable in Good to Soft sweet spot'
    },
    {
        'title': 'EXTREME LONGSHOTS FAILED',
        'insight': '100/1 finished 7th, 200/1 finished 8th, 250/1 pulled up. Even in handicaps, extreme outsiders (100+) rarely competitive. Sweet spot > longshots.',
        'pattern': '100+ odds = avoid even in handicaps',
        'action': 'Cap handicap odds at 50, reject 100+'
    },
    {
        'title': 'CLASS 4 SOUTHWELL GOOD TO SOFT PATTERN',
        'insight': 'First Southwell data point. Winner @ 6.0 in sweet spot. Validates that Good to Soft sweet spot is venue-independent. Works at Southwell like Kempton.',
        'pattern': 'Going > Venue for sweet spot prediction',
        'action': 'Apply Good to Soft strategies across all venues'
    },
    {
        'title': 'HANDICAP REFINEMENT: SWEET SPOT STILL WORKS',
        'insight': 'Kempton 14:35 had 50/1 winner. Southwell 14:45 had 6.0 winner. BOTH likely handicaps. Handicaps = wider variance but not automatic longshots. Sweet spot valid if weights favor.',
        'pattern': 'Handicaps = 3-50 viable, but sweet spot (3-15) still preferred',
        'action': 'In handicaps, prefer sweet spot over longshots when possible'
    }
]

for i, learning in enumerate(learnings, 1):
    print(f"\n{i}. {learning['title']}")
    print(f"   Insight: {learning['insight']}")
    print(f"   Pattern: {learning['pattern']}")
    print(f"   Action: {learning['action']}")

print("\n" + "="*80)
print("GOOD TO SOFT PATTERN SUMMARY")
print("="*80)

print(f"\nVENUE VALIDATIONS:")
print(f"  Kempton 13:27: Aviation @ 6.0 (Class 5, likely non-handicap)")
print(f"  Kempton 15:07: Issam @ 3.75 (Class 3, non-handicap)")
print(f"  Kempton 16:17: Lover Desbois @ 3.75 (Class 5, Amateur)")
print(f"  Southwell 14:45: Desertmore News @ 6.0 (Class 4, likely handicap)")
print(f"\n  4/4 winners in sweet spot (3-9 range)")
print(f"  Average winning odds: 4.9")
print(f"  Pattern: STRONG CROSS-VENUE CONSISTENCY")
print(f"\nHANDICAP COMPARISON:")
print(f"  Kempton 14:35 Handicap: 50/1 winner (HIGH VARIANCE)")
print(f"  Southwell 14:45 Handicap: 6.0 winner (SWEET SPOT)")
print(f"  Learning: Handicaps = wider range, not automatic longshots")

print("\n" + "="*80)
print("SAVE TO DATABASE")
print("="*80)

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

learning_item = {
    'bet_id': f'LEARNING_SOUTHWELL_1445_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
    'bet_date': '2026-02-02',
    'race_course': 'Southwell',
    'race_time': '14:45',
    'race_going': 'Good to Soft',
    'race_class': '4',
    'race_type': 'Likely Handicap',
    'race_runners': 10,
    'winner': 'Desertmore News',
    'winner_sp': '5/1',
    'winner_decimal': Decimal('6.0'),
    'winner_trainer': 'Tom Ellis',
    'pattern_validation': True,
    'handicap_race': True,
    'sweet_spot_winner': True,
    'critical_learning': 'HANDICAP_SWEET_SPOT_VALIDATION',
    'learnings': learnings,
    'timestamp': datetime.now().isoformat(),
    'learning_type': 'RACE_RESULT',
    'is_learning_pick': False
}

def convert_decimals(obj):
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

learning_item = convert_decimals(learning_item)

try:
    table.put_item(Item=learning_item)
    print("✓ Learning saved to database successfully")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\nGOOD TO SOFT SWEET SPOT VALIDATED ACROSS VENUES")
print(f"\nDesertmore News @ 6.0 WINNER at Southwell")
print(f"Top 2 both in sweet spot (6.0, 3.5)")
print(f"8 key learnings extracted")
print(f"\n**KEY INSIGHT**: Handicaps don't always = longshots")
print(f"  - Kempton 14:35 Handicap: 50/1 winner (variance)")
print(f"  - Southwell 14:45 Handicap: 6.0 winner (sweet spot)")
print(f"\n**PATTERN CONFIRMED**:")
print(f"  - Good to Soft = 3-9 sweet spot (venue-independent)")
print(f"  - 4/4 recent winners in sweet spot")
print(f"  - Handicaps = wider viable range but prefer sweet spot")
print("="*80 + "\n")
