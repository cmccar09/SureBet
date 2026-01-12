#!/usr/bin/env python3
"""
Simple analysis: Why did high-confidence bets lose?
Look at what data we had when making the pick
"""
import boto3
import json
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("=" * 80)
print("HIGH CONFIDENCE LOSS ANALYSIS")
print("=" * 80)

# Get yesterday's bets
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

response = table.query(
    KeyConditionExpression='bet_date = :date',
    ExpressionAttributeValues={':date': yesterday}
)

bets = response.get('Items', [])

# Find high-confidence losses
high_conf_losses = []
for bet in bets:
    confidence = float(bet.get('confidence', 0))
    result = bet.get('actual_result')
    
    if confidence >= 70 and result == 'LOST':
        high_conf_losses.append(bet)

print(f"\nFound {len(high_conf_losses)} high-confidence losses (>=70% confidence)\n")

for i, bet in enumerate(high_conf_losses, 1):
    print(f"\n[{i}] {bet.get('horse', 'Unknown')}")
    print("-" * 80)
    print(f"Venue: {bet.get('course')}")
    print(f"Time: {bet.get('race_time', '')[:16]}")
    print(f"Confidence: {bet.get('confidence')}%")
    print(f"Predicted P(Win): {bet.get('p_win')}")
    print(f"Odds: {bet.get('odds')}")
    print(f"ROI: {bet.get('roi')}%")
    
    # Check if this was a greyhound with form data
    if bet.get('race_type') == 'greyhound':
        enriched = bet.get('enrichment_data', {})
        if enriched:
            print(f"\nGreyhound Form Data:")
            print(f"  - Form available: YES")
            form = enriched.get('form_data', {})
            if form:
                print(f"  - Win rate: {form.get('win_percentage', 'N/A')}")
                print(f"  - Place rate: {form.get('place_percentage', 'N/A')}")
                print(f"  - Recent form: {form.get('recent_form', 'N/A')}")
        else:
            print(f"\nGreyhound Form Data: NONE (picked without historical data)")
    
    # AI's reasoning
    why_now = bet.get('why_now', '')
    if why_now:
        print(f"\nAI Reasoning:")
        print(f"  {why_now[:300]}")
    
    # Decision breakdown
    breakdown = bet.get('confidence_breakdown', {})
    if breakdown:
        print(f"\nConfidence Breakdown:")
        print(f"  - Win component: {breakdown.get('win_component')}")
        print(f"  - Place component: {breakdown.get('place_component')}")
        print(f"  - Edge component: {breakdown.get('edge_component')}")
        print(f"  - Consistency: {breakdown.get('consistency_component')}")
    
    combined_conf = bet.get('combined_confidence')
    if combined_conf:
        print(f"\nCombined Confidence: {combined_conf}%")
        print(f"(Combined = AI prediction + external data validation)")

# Generate learnings
print("\n" + "=" * 80)
print("KEY LEARNINGS")
print("=" * 80)

if len(high_conf_losses) > 0:
    print(f"\n1. {len(high_conf_losses)} high-confidence bets lost yesterday")
    print(f"   - This indicates AI overconfidence")
    print(f"   - Recommendation: Reduce confidence scores by 20-30%")
    
    # Check if any had form data
    with_form = sum(1 for b in high_conf_losses if b.get('enrichment_data'))
    without_form = len(high_conf_losses) - with_form
    
    if without_form > 0:
        print(f"\n2. {without_form} high-confidence picks had NO external form data")
        print(f"   - Picking based on AI alone is too risky")
        print(f"   - Recommendation: Require external validation for high confidence")
    
    if with_form > 0:
        print(f"\n3. {with_form} high-confidence picks HAD form data but still lost")
        print(f"   - Form data not correlating with wins")
        print(f"   - Recommendation: Review form data weighting in AI model")

print("\n" + "=" * 80)
