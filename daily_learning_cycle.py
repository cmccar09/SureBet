#!/usr/bin/env python3
"""
Daily learning cycle - run this each morning to update the AI with learnings
This updates prompt.txt with insights from yesterday's performance
"""

import os
import sys
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import boto3
from decimal import Decimal

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from learning_engine import (
    analyze_performance_patterns,
    generate_learning_insights,
    update_prompt_with_learnings
)

def load_results_from_dynamodb(days_back=30):
    """Load bet results from DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('SureBetBets')
    
    cutoff = datetime.now() - timedelta(days=days_back)
    
    try:
        response = table.scan(
            FilterExpression='#ts > :threshold AND attribute_exists(#result)',
            ExpressionAttributeNames={
                '#ts': 'timestamp',
                '#result': 'result'
            },
            ExpressionAttributeValues={
                ':threshold': cutoff.isoformat()
            }
        )
        
        items = response.get('Items', [])
        
        # Convert DynamoDB format to expected format
        results = []
        for item in items:
            result_entry = {
                'date': item.get('date', ''),
                'selection': {
                    'selection_id': item.get('selection_id', ''),
                    'runner_name': item.get('horse', ''),
                    'venue': item.get('course', ''),
                    'odds': float(item.get('odds', 0)),
                    'bet_type': item.get('bet_type', 'WIN'),
                    'confidence': float(item.get('confidence', 0)),
                    'tags': item.get('tags', ''),
                    'why_now': item.get('why_now', ''),
                    'stake': float(item.get('stake', 0))
                },
                'result': {
                    'selection_id': item.get('selection_id', ''),
                    'is_winner': item.get('result') == 'won',
                    'is_placed': item.get('result') in ['won', 'placed'],
                    'final_odds': float(item.get('odds', 0))
                }
            }
            results.append(result_entry)
        
        print(f"Loaded {len(results)} completed bets from DynamoDB")
        return results
        
    except Exception as e:
        print(f"Error loading from DynamoDB: {e}")
        return []

def update_bankroll_env_var(new_bankroll):
    """Update the BANKROLL environment variable in Lambda"""
    
    client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Get current function configuration
        response = client.get_function_configuration(
            FunctionName='BettingWorkflowScheduled'
        )
        
        # Update environment variables
        env_vars = response.get('Environment', {}).get('Variables', {})
        env_vars['BANKROLL'] = str(new_bankroll)
        
        # Update function
        client.update_function_configuration(
            FunctionName='BettingWorkflowScheduled',
            Environment={'Variables': env_vars}
        )
        
        print(f"✓ Updated Lambda BANKROLL to €{new_bankroll:.2f}")
        
    except Exception as e:
        print(f"Error updating Lambda env var: {e}")

def calculate_current_bankroll(results, initial=1000.0):
    """Calculate current bankroll from bet history"""
    
    bankroll = initial
    
    for record in results:
        selection = record['selection']
        result = record['result']
        
        stake = selection.get('stake', 0)
        odds = selection.get('odds', 0)
        bet_type = selection.get('bet_type', 'WIN')
        
        # Subtract stake
        bankroll -= stake
        
        # Add returns if won
        if result.get('is_winner'):
            if bet_type == 'WIN':
                bankroll += stake * odds
            elif bet_type == 'EW':
                # Won, so both win and place parts pay
                bankroll += stake * odds  # Win part
                # Place part would also pay but we already got the win
        elif result.get('is_placed') and bet_type == 'EW':
            # Placed but didn't win (EW place only)
            # Typically 1/4 or 1/5 odds for place
            place_fraction = 0.2  # 1/5 typical
            place_odds = 1 + (odds - 1) * place_fraction
            bankroll += stake * place_odds
    
    return bankroll

def main():
    """Run daily learning cycle"""
    
    print("="*70)
    print(" "*15 + "DAILY LEARNING CYCLE")
    print(" "*10 + datetime.now().strftime("%A, %d %B %Y %H:%M"))
    print("="*70)
    
    # Load results from DynamoDB
    print("\n[1/5] Loading historical results from DynamoDB...")
    results = load_results_from_dynamodb(days_back=30)
    
    if len(results) < 10:
        print(f"\n⚠️  Only {len(results)} completed bets found")
        print("Need at least 10 results for meaningful analysis")
        print("Skipping learning cycle for now")
        return
    
    # Calculate current bankroll
    print("\n[2/5] Calculating current bankroll...")
    current_bankroll = calculate_current_bankroll(results, initial=1000.0)
    profit = current_bankroll - 1000.0
    roi_pct = (profit / 1000.0) * 100
    
    print(f"  Starting bankroll: €1000.00")
    print(f"  Current bankroll:  €{current_bankroll:.2f}")
    print(f"  Profit/Loss:       €{profit:+.2f}")
    print(f"  ROI:               {roi_pct:+.1f}%")
    
    # Update Lambda env var with new bankroll
    print("\n[3/5] Updating Lambda bankroll...")
    update_bankroll_env_var(current_bankroll)
    
    # Analyze performance
    print("\n[4/5] Analyzing performance patterns...")
    analysis = analyze_performance_patterns(results)
    
    # Generate insights
    print("\n[5/5] Generating and applying insights...")
    insights = generate_learning_insights(analysis)
    
    # Update prompt with learnings
    if insights:
        update_prompt_with_learnings(insights)
        print(f"\n✓ Applied {len(insights)} insights to prompt.txt")
    else:
        print("\n⚠️  No significant insights yet - need more varied data")
    
    # Summary
    print("\n" + "="*70)
    print("LEARNING CYCLE COMPLETE")
    print("="*70)
    print(f"\n✓ Analyzed {len(results)} bets")
    print(f"✓ Current bankroll: €{current_bankroll:.2f} ({roi_pct:+.1f}% ROI)")
    print(f"✓ Applied {len(insights)} new insights")
    print(f"✓ Updated Lambda configuration")
    print("\nNext run: Tomorrow morning before first races")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
