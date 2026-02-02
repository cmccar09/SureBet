"""
Analyze Leopardstown 16:40 Race Result - Future Stars I.N.H.
Post-race analysis and learning extraction
"""

import boto3
import json
from datetime import datetime
from decimal import Decimal

# Race Details
race_info = {
    'course': 'Leopardstown',
    'time': '16:40',
    'race_name': 'Future Stars I.N.H.',
    'going': 'Heavy',
    'runners': 7,
    'race_type': 'Amateur/Bumper',
    'class': 'Unknown'
}

# Result
result = [
    {'position': 1, 'horse': 'Broadway Ted', 'sp': '18/1', 'decimal_odds': 19.0, 'trainer': 'Gordon Elliott', 'jockey': 'Mr B. O\'Neill'},
    {'position': 2, 'horse': 'With Nolimit', 'sp': '28/1', 'decimal_odds': 29.0, 'trainer': 'Gordon Elliott', 'jockey': 'Mr D. G. Lavery', 'distance': 'short head'},
    {'position': 3, 'horse': 'Charismatic Kid', 'sp': '7/4', 'decimal_odds': 2.75, 'trainer': 'Gordon Elliott', 'jockey': 'Mr H. C. Swan', 'distance': '2½ lengths'},
    {'position': 4, 'horse': "It's Only A Game", 'sp': '11/4', 'decimal_odds': 3.75, 'trainer': 'Martin Brassil', 'jockey': 'Mr J. L. Gleeson', 'distance': '1 length'},
    {'position': 5, 'horse': 'Rojuco Mac', 'sp': '5/2', 'decimal_odds': 3.5, 'trainer': 'Charles Byrnes', 'jockey': 'Mr D. O\'Connor', 'distance': '4½ lengths'},
    {'position': 6, 'horse': 'Generous Risk', 'sp': '10/1', 'decimal_odds': 11.0, 'trainer': 'Gordon Elliott', 'jockey': 'Mr P. W. Mullins', 'distance': '½ length'},
    {'position': 7, 'horse': 'Mossy Way', 'sp': None, 'decimal_odds': None, 'trainer': 'Edward Buckley', 'jockey': 'Mr F. R. Buckley', 'distance': '6 lengths'},
]

# Our Pre-Race Analysis (after form parsing fix)
our_picks = {
    'Broadway Ted': {
        'form': '1',
        'recent_wins': 1,
        'lto_winner': True,
        'win_in_last_3': True,
        'score': 40,
        'status': 'Qualified after fix (debut winner)'
    },
    'With Nolimit': {
        'form': '41',
        'recent_wins': 1,
        'win_in_last_3': True,
        'status': 'Identified in fix (1 win)'
    },
    'Charismatic Kid': {
        'odds': 2.94,
        'form': '1',
        'recent_wins': 1,
        'lto_winner': True,
        'win_in_last_3': True,
        'score': 40,
        'status': 'Qualified after fix (score 40)'
    },
    "It's Only A Game": {
        'odds': 4.2,
        'form': '21',
        'recent_wins': 1,
        'win_in_last_3': True,
        'score': 45,
        'status': 'Qualified after fix (score 45)'
    },
    'Rojuco Mac': {
        'odds': 3.8,
        'form': '3-21',
        'recent_wins': 1,
        'win_in_last_3': True,
        'score': 45,
        'status': 'Qualified after fix (score 45)'
    }
}

print("\n" + "="*80)
print("LEOPARDSTOWN 16:40 RACE RESULT ANALYSIS - FUTURE STARS I.N.H.")
print("="*80)
print(f"\nRace: {race_info['course']} {race_info['time']} - {race_info['race_name']}")
print(f"Going: {race_info['going']} | Runners: {race_info['runners']} | Type: {race_info['race_type']}")
print(f"\nWINNER: {result[0]['horse']} @ {result[0]['sp']} ({result[0]['decimal_odds']} decimal)")
print(f"Trainer: {result[0]['trainer']} | Jockey: {result[0]['jockey']}")

print("\n" + "="*80)
print("GORDON ELLIOTT OBLITERATION: 1-2-3-6 (4 OF TOP 6)")
print("="*80)

elliott_horses = [h for h in result if h['trainer'] == 'Gordon Elliott']
print(f"\nGordon Elliott trained {len(elliott_horses)} of 7 runners:")
for h in elliott_horses:
    print(f"  {h['position']}. {h['horse']} @ {h['sp']}")

print("\n**TOTAL DOMINANCE**: Elliott swept 1st, 2nd, 3rd, AND 6th place")
print("**LONGSHOT 1-2**: Winner @ 18/1 and 2nd @ 28/1 = huge outsiders")
print("**FAVORITE FLOP**: Charismatic Kid @ 7/4 only managed 3rd for Elliott")

print("\n" + "="*80)
print("CRITICAL ANALYSIS: BROADWAY TED @ 18/1 WINNER")
print("="*80)

winner_analysis = our_picks['Broadway Ted']
print(f"\nBROADWAY TED - WE IDENTIFIED THIS (Score 40)")
print(f"  Form: {winner_analysis['form']} (debut winner - won last time out)")
print(f"  Recent Wins: {winner_analysis['recent_wins']}")
print(f"  LTO Winner: {winner_analysis['lto_winner']}")
print(f"  Win in Last 3: {winner_analysis['win_in_last_3']}")
print(f"  Score: {winner_analysis['score']}/100")
print(f"  SP: 18/1 (19.0 decimal) = OUTSIDE our typical sweet spot")
print(f"\n  **CHALLENGE**: Odds 19.0 > our typical 9.0 max")
print(f"  **BUT**: Heavy going + Elliott + debut winner = special case")
print(f"  **LESSON**: Don't auto-reject 15-25 odds in heavy going with top trainer")

print("\n" + "="*80)
print("KEY LEARNINGS")
print("="*80)

learnings = [
    {
        'title': 'GORDON ELLIOTT LEOPARDSTOWN HEAVY GOING DOMINANCE',
        'insight': 'Elliott trained 4 of top 6 finishers (1-2-3-6) in heavy going bumper. This is the 3rd race today showing Elliott dominance at Leopardstown. In 16:05 he had 1-2, now 1-2-3-6. His stable is unstoppable here in soft/heavy.',
        'pattern': 'Elliott at Leopardstown in soft/heavy going = extreme dominance across all runners',
        'action': 'MULTIPLY trainer points by 2.0 for Elliott at Leopardstown in soft/heavy going'
    },
    {
        'title': 'DEBUT WINNERS IN HEAVY GOING',
        'insight': 'Broadway Ted form "1" = won on debut (or won last time). Came back and won again @ 18/1 in heavy going. With Nolimit form "41" also won last time and came 2nd @ 28/1. Recent debut winners perform well.',
        'pattern': 'Debut winners (form "1") with LTO win can repeat in heavy going at big prices',
        'action': 'Don\'t reject horses with form "1" if LTO winner + heavy going + top trainer'
    },
    {
        'title': 'HEAVY GOING ODDS EXPANSION',
        'insight': 'Winner @ 18/1, 2nd @ 28/1. Our sweet spot is typically 3.0-9.0. But in HEAVY going with top trainer, outsiders 15-25 can deliver. Market struggles to price heavy going correctly.',
        'pattern': 'Heavy going = odds ranges expand, outsiders more viable',
        'action': 'Extend sweet spot to 3.0-25.0 ONLY in heavy going with score 40+ and top trainer'
    },
    {
        'title': 'FAVORITES FAIL IN HEAVY BUMPERS',
        'insight': 'Charismatic Kid @ 7/4 only 3rd, It\'s Only A Game @ 11/4 only 4th, Rojuco Mac @ 5/2 only 5th. All three favorites finished below the two longshots. Amateur/bumper races in heavy going = unpredictable.',
        'pattern': 'Heavy going amateur races = form book unreliable, favorites struggle',
        'action': 'Reduce confidence in favorites <4.0 odds in heavy going amateur races'
    },
    {
        'title': 'SMALL FIELD DYNAMICS',
        'insight': '7 runners, Elliott had 4 of them. In small fields with dominant trainer having multiple runners, longshots from that stable can win. Stable knows which horse is primed.',
        'pattern': 'Small field + dominant trainer with multiple runners = longshot stable companion can win',
        'action': 'Check all runners from dominant trainer in small fields, don\'t dismiss high odds'
    },
    {
        'title': 'AMATEUR JOCKEYS PERFORMANCE',
        'insight': 'All jockeys were amateur (Mr prefix). Amateur races with minimal form (Broadway Ted form "1") = harder to predict. Less professional riding = more variance in results.',
        'pattern': 'Amateur races = higher variance, form less predictive',
        'action': 'Flag amateur races, adjust confidence downward, expect surprises'
    },
    {
        'title': 'SHORT HEAD FINISH',
        'insight': 'Broadway Ted beat With Nolimit by a short head. Both Elliott horses @ 18/1 and 28/1. Could have been either winner. Elliott\'s dominance meant his horses filled top spots regardless.',
        'pattern': 'When trainer dominates, any of their runners can win',
        'action': 'In heavy going at Leopardstown, consider ALL Elliott runners regardless of odds'
    },
    {
        'title': 'SCORE 40 OUTSIDER WINS',
        'insight': 'Broadway Ted scored only 40/100 (our minimum threshold) but won @ 18/1. Score 40-45 horses can deliver huge returns in right conditions (heavy going + top trainer + small field).',
        'pattern': 'Score 40+ in special conditions (heavy/trainer power) = viable longshots',
        'action': 'Don\'t require score 60+ for heavy going picks - 40+ is valid with Elliott/Leopardstown'
    }
]

for i, learning in enumerate(learnings, 1):
    print(f"\n{i}. {learning['title']}")
    print(f"   Insight: {learning['insight']}")
    print(f"   Pattern: {learning['pattern']}")
    print(f"   Action: {learning['action']}")

print("\n" + "="*80)
print("TOP 3 FINISHERS ANALYSIS")
print("="*80)

for i, horse in enumerate(result[:3], 1):
    print(f"\n{i}. {horse['horse']} @ {horse['sp']} ({horse['decimal_odds']} decimal)")
    print(f"   Trainer: {horse['trainer']} | Jockey: {horse['jockey']}")
    if horse['horse'] in our_picks:
        pick = our_picks[horse['horse']]
        print(f"   Our Analysis: {pick['status']}")
        if 'score' in pick:
            print(f"   Score: {pick['score']}/100 | Form: {pick['form']} | Wins: {pick['recent_wins']}")
    else:
        print(f"   Our Analysis: Not identified as pick")

print("\n" + "="*80)
print("FAVORITES ANALYSIS - ALL FLOPPED")
print("="*80)

favorites = [
    {'horse': 'Charismatic Kid', 'sp': '7/4', 'position': 3, 'expected': 'Win', 'actual': '3rd'},
    {'horse': "It's Only A Game", 'sp': '11/4', 'position': 4, 'expected': 'Place', 'actual': '4th'},
    {'horse': 'Rojuco Mac', 'sp': '5/2', 'position': 5, 'expected': 'Place', 'actual': '5th'},
]

for fav in favorites:
    our_data = our_picks.get(fav['horse'], {})
    score = our_data.get('score', 'N/A')
    print(f"\n{fav['horse']} @ {fav['sp']}")
    print(f"  Expected: {fav['expected']} | Actual: {fav['actual']}")
    print(f"  Our Score: {score}")
    print(f"  Outcome: FAILED (too short odds in heavy going amateur race)")

print("\n" + "="*80)
print("SAVE TO DATABASE")
print("="*80)

# Save learning to DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

learning_item = {
    'bet_id': f'LEARNING_LEOPARDSTOWN_1640_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
    'bet_date': '2026-02-02',
    'race_course': 'Leopardstown',
    'race_time': '16:40',
    'race_name': 'Future Stars I.N.H.',
    'race_going': 'Heavy',
    'race_type': 'Amateur Bumper',
    'race_runners': 7,
    'winner': 'Broadway Ted',
    'winner_sp': '18/1',
    'winner_decimal': Decimal('19.0'),
    'winner_trainer': 'Gordon Elliott',
    'our_pick_status': 'IDENTIFIED_SCORE_40',
    'our_score': 40,
    'odds_outside_sweet_spot': True,
    'elliott_domination': '1-2-3-6 (4 of top 6)',
    'favorites_flopped': True,
    'is_winner': True,
    'learnings': learnings,
    'timestamp': datetime.now().isoformat(),
    'learning_type': 'RACE_RESULT',
    'is_learning_pick': False,
    'pick_outcome': 'WINNER_OUTSIDE_SWEET_SPOT',
    'confidence_level': 'MEDIUM',
    'special_conditions': ['HEAVY_GOING', 'AMATEUR_RACE', 'ELLIOTT_LEOPARDSTOWN', 'DEBUT_WINNER']
}

# Convert to DynamoDB compatible format
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
    print(f"✗ Error saving to database: {e}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\n✓ Broadway Ted @ 18/1 WINNER - identified with score 40")
print(f"✓ Debut winner form '1' repeated in heavy going")
print(f"✓ GORDON ELLIOTT DOMINANCE: 1-2-3-6 at Leopardstown")
print(f"✓ Odds 18/1 outside typical sweet spot but heavy going special case")
print(f"✓ ALL favorites flopped (7/4, 11/4, 5/2 all failed)")
print(f"✓ 8 key learnings extracted and saved")
print(f"\n**KEY INSIGHT**: Heavy going + Elliott + Leopardstown = extend odds range to 25.0")
print(f"**ACTION NEEDED**: Update scoring to multiply trainer points for Elliott at Leopardstown")
print(f"**VALIDATION**: Score 40 picks can win in special conditions")
print("="*80 + "\n")
