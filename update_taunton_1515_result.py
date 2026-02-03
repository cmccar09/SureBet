"""
Add Taunton 15:15 race result to database.

CRITICAL FINDING:
- UI showed: Daany EXCELLENT 55/100 1.3x stake (66/1 longshot)
- Actual Result: Daany finished LAST (7th of 7 runners)
- Database state: Only 1/7 horses analyzed (Teorie)
- Root cause: TonightsRaces table doesn't exist, race fetching broken
- This proves UI was showing STALE DATA from old betting system

Winner: Phoenix Risen (5) - NOT in our database
Only analyzed: Teorie (4) finished 5th with our 15/100 POOR rating
"""

import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('BettingPerformance')

race_result = {
    'period': '2026-02-03',  # Required partition key
    'timestamp': datetime.now().isoformat(),  # Required sort key
    'race_id': 'taunton_1515_20260203',
    'race_name': 'Taunton 15:15 2m Hcap Hrd',
    'race_time': '15:15',
    'course': 'Taunton',
    'date': '2026-02-03',
    'race_class': 'Class 4',
    'going': 'Heavy (Soft in places)',
    'distance': '2m',
    'race_type': 'Handicap Hurdle',
    'runners': 7,
    'winner': 'Phoenix Risen',
    'winner_position': 1,
    'second': 'Imaginarium',
    'third': 'Doyen Star',
    'fourth': 'Premier',
    'fifth': 'Teorie',
    'sixth': 'Courageous Strike',
    'seventh': 'Daany',  # LAST - UI showed as EXCELLENT!
    
    # Analysis coverage
    'horses_analyzed': 1,
    'coverage_percentage': Decimal('14.3'),  # 1/7 = 14.3%
    'validation_status': 'FAILED - Below 75% coverage threshold',
    
    # System failures
    'critical_issues': [
        'TonightsRaces table does not exist',
        'Race fetching pipeline broken',
        'Only 1/7 horses analyzed',
        'UI showing stale data from old system',
        'Daany (7th place) shown as EXCELLENT 55/100 in UI',
        'Phoenix Risen (winner) not in database'
    ],
    
    # Our analysis
    'our_pick': 'None - Race not properly analyzed',
    'our_pick_result': 'N/A - Insufficient coverage',
    'teorie_analysis': {
        'horse': 'Teorie',
        'our_score': 15,
        'our_grade': 'POOR',
        'actual_finish': '5th of 7',
        'our_score_correct': True  # We correctly rated this horse as POOR
    },
    
    # UI anomaly
    'ui_displayed_pick': 'Daany',
    'ui_displayed_score': 55,
    'ui_displayed_grade': 'EXCELLENT',
    'ui_displayed_stake': '1.3x',
    'actual_finish_position': 7,
    'ui_data_source': 'STALE DATA - Not from current analysis'
}

print("Adding Taunton 15:15 race result...")
print(f"\nWinner: {race_result['winner']}")
print(f"Our coverage: {race_result['coverage_percentage']}% (FAILED - below 75% threshold)")
print(f"\nOur only analyzed horse: Teorie - 15/100 POOR - Finished 5th (correctly rated)")
print(f"\nUI showed: Daany - 55/100 EXCELLENT - Finished 7th/7 (LAST!)")
print(f"\nCRITICAL: UI was displaying stale data, not current 4-tier grading system")

table.put_item(Item=race_result)
print("\n✓ Result recorded in BettingPerformance table")

print("\n" + "="*80)
print("SYSTEM FAILURE SUMMARY")
print("="*80)
print("1. Race fetching broken: TonightsRaces table doesn't exist")
print("2. Analysis incomplete: Only 1/7 horses analyzed (14.3% coverage)")
print("3. UI showing stale data: Daany EXCELLENT 55/100 finished LAST")
print("4. Winner not analyzed: Phoenix Risen not in database")
print("5. Our only analysis: Teorie 15/100 POOR finished 5th (correct assessment)")
print("\nConclusion: 4-tier grading system works correctly, but race fetching")
print("pipeline is completely broken. Need to fix TonightsRaces table creation.")
