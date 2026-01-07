#!/usr/bin/env python3
"""
Lambda: Learning Analysis
Runs HOURLY to continuously analyze race results and improve strategy
Generates insights with detailed loss analysis and pattern recognition
Updates after every result batch for real-time learning
"""

import os
import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('SUREBET_DDB_TABLE', 'SureBetBets')
learning_table_name = os.environ.get('LEARNING_TABLE', 'BettingPerformance')

def get_results_for_period(days=7):
    """Get all bets with results from last N days"""
    table = dynamodb.Table(table_name)
    
    all_results = []
    
    for days_ago in range(days):
        date = (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        try:
            response = table.query(
                KeyConditionExpression='bet_date = :date',
                FilterExpression='attribute_exists(actual_result) AND track_performance = :track',
                ExpressionAttributeValues={':date': date, ':track': True}
            )
            all_results.extend(response.get('Items', []))
        except Exception as e:
            print(f"Error querying {date}: {e}")
    
    print(f"Found {len(all_results)} bets with results from last {days} days")
    return all_results

def analyze_performance(results):
    """Analyze what's working and what's not"""
    
    analysis = {
        'overall': {
            'total_bets': len(results),
            'total_stake': 0,
            'total_pnl': 0,
            'wins': 0,
            'places': 0,
            'losses': 0,
            'win_rate': 0,
            'place_rate': 0,
            'roi': 0
        },
        'by_odds_range': defaultdict(lambda: {
            'count': 0, 'stake': 0, 'pnl': 0, 'wins': 0
        }),
        'by_course': defaultdict(lambda: {
            'count': 0, 'stake': 0, 'pnl': 0, 'wins': 0
        }),
        'by_bet_type': defaultdict(lambda: {
            'count': 0, 'stake': 0, 'pnl': 0, 'wins': 0
        }),
        'by_decision_rating': defaultdict(lambda: {
            'count': 0, 'stake': 0, 'pnl': 0, 'wins': 0
        }),
        'loss_analysis': {
            'total_losses': 0,
            'loss_amount': 0,
            'common_patterns': [],
            'favorites_lost': 0,  # Horses with odds < 3.0
            'longshots_lost': 0,  # Horses with odds > 8.0
            'high_confidence_losses': 0,  # Lost despite >70% confidence
            'do_it_losses': 0,  # Lost despite 'DO IT' rating
            'by_position': defaultdict(int),  # Track finishing positions
        }
    }
    
    for result in results:
        stake = float(result.get('stake', 0))
        pnl = float(result.get('pnl', 0))
        odds = float(result.get('odds', 0))
        is_winner = result.get('is_winner', False)
        is_placed = result.get('is_placed', False)
        course = result.get('course', 'Unknown')
        bet_type = result.get('bet_type', 'WIN')
        decision_rating = result.get('decision_rating', 'UNKNOWN')
        confidence = float(result.get('confidence', 0))
        actual_position = result.get('actual_position', 'Unknown')
        
        # Overall stats
        analysis['overall']['total_stake'] += stake
        analysis['overall']['total_pnl'] += pnl
        if is_winner:
            analysis['overall']['wins'] += 1
        elif is_placed:
            analysis['overall']['places'] += 1
        else:
            analysis['overall']['losses'] += 1            
            # DETAILED LOSS ANALYSIS
            analysis['loss_analysis']['total_losses'] += 1
            analysis['loss_analysis']['loss_amount'] += abs(pnl)
            
            # Track finish position for losses
            if actual_position != 'Unknown':
                analysis['loss_analysis']['by_position'][str(actual_position)] += 1
            
            # Categorize types of losses
            if odds < 3.0:
                analysis['loss_analysis']['favorites_lost'] += 1
            elif odds > 8.0:
                analysis['loss_analysis']['longshots_lost'] += 1
            
            if confidence > 70:
                analysis['loss_analysis']['high_confidence_losses'] += 1
            
            if decision_rating == 'DO IT':
                analysis['loss_analysis']['do_it_losses'] += 1        
        # By odds range
        if odds <= 3.0:
            odds_range = 'favorite'
        elif odds <= 6.0:
            odds_range = 'medium'
        elif odds <= 10.0:
            odds_range = 'long_shot'
        else:
            odds_range = 'very_long'
        
        analysis['by_odds_range'][odds_range]['count'] += 1
        analysis['by_odds_range'][odds_range]['stake'] += stake
        analysis['by_odds_range'][odds_range]['pnl'] += pnl
        if is_winner:
            analysis['by_odds_range'][odds_range]['wins'] += 1
        
        # By course
        analysis['by_course'][course]['count'] += 1
        analysis['by_course'][course]['stake'] += stake
        analysis['by_course'][course]['pnl'] += pnl
        if is_winner:
            analysis['by_course'][course]['wins'] += 1
        
        # By bet type
        analysis['by_bet_type'][bet_type]['count'] += 1
        analysis['by_bet_type'][bet_type]['stake'] += stake
        analysis['by_bet_type'][bet_type]['pnl'] += pnl
        if is_winner:
            analysis['by_bet_type'][bet_type]['wins'] += 1
        
        # By decision rating
        analysis['by_decision_rating'][decision_rating]['count'] += 1
        analysis['by_decision_rating'][decision_rating]['stake'] += stake
        analysis['by_decision_rating'][decision_rating]['pnl'] += pnl
        if is_winner:
            analysis['by_decision_rating'][decision_rating]['wins'] += 1
    
    # Calculate rates
    total_bets = analysis['overall']['total_bets']
    if total_bets > 0:
        analysis['overall']['win_rate'] = analysis['overall']['wins'] / total_bets
        analysis['overall']['place_rate'] = (analysis['overall']['wins'] + analysis['overall']['places']) / total_bets
    
    total_stake = analysis['overall']['total_stake']
    if total_stake > 0:
        analysis['overall']['roi'] = (analysis['overall']['total_pnl'] / total_stake) * 100
    
    # Calculate ROI for each category
    for category in ['by_odds_range', 'by_course', 'by_bet_type', 'by_decision_rating']:
        for key, stats in analysis[category].items():
            if stats['stake'] > 0:
                stats['roi'] = (stats['pnl'] / stats['stake']) * 100
                stats['win_rate'] = stats['wins'] / stats['count'] if stats['count'] > 0 else 0
    
    return analysis

def generate_insights(analysis):
    """Generate actionable insights from analysis with detailed loss patterns"""
    
    insights = {
        'strengths': [],
        'weaknesses': [],
        'recommendations': [],
        'loss_patterns': []  # NEW: Specific reasons for losses
    }
    
    # ANALYZE LOSS PATTERNS FIRST (Critical for improvement)
    loss_data = analysis['loss_analysis']
    total_losses = loss_data['total_losses']
    
    if total_losses > 0:
        # Pattern 1: Losing on favorites
        if loss_data['favorites_lost'] > total_losses * 0.3:
            insights['loss_patterns'].append(
                f"Losing {loss_data['favorites_lost']}/{total_losses} on favorites (odds <3.0) - may be overestimating short-priced horses"
            )
            insights['recommendations'].append("CRITICAL: Reduce confidence on favorites by 15-20%, they're less value than expected")
        
        # Pattern 2: Losing on longshots
        if loss_data['longshots_lost'] > total_losses * 0.4:
            insights['loss_patterns'].append(
                f"Losing {loss_data['longshots_lost']}/{total_losses} on longshots (odds >8.0) - backing too many outsiders"
            )
            insights['recommendations'].append("AVOID: Significantly reduce longshot bets (>8.0 odds), they're not hitting often enough")
        
        # Pattern 3: High confidence failures
        if loss_data['high_confidence_losses'] > 3:
            insights['loss_patterns'].append(
                f"{loss_data['high_confidence_losses']} high-confidence bets (>70%) lost - overconfident"
            )
            insights['recommendations'].append("RECALIBRATE: Reduce ALL confidence scores by 10-15% - current model is overconfident")
        
        # Pattern 4: 'DO IT' rating failures
        if loss_data['do_it_losses'] > 2:
            do_it_total = analysis['by_decision_rating']['DO IT']['count']
            do_it_loss_rate = loss_data['do_it_losses'] / do_it_total if do_it_total > 0 else 0
            if do_it_loss_rate > 0.4:  # >40% failure rate on top picks
                insights['loss_patterns'].append(
                    f"{loss_data['do_it_losses']}/{do_it_total} 'DO IT' picks lost ({do_it_loss_rate*100:.0f}% failure rate)"
                )
                insights['recommendations'].append("URGENT: Tighten 'DO IT' criteria - require 20%+ ROI AND 80%+ confidence, current threshold too loose")
        
        # Pattern 5: Finishing positions
        if loss_data['by_position']:
            # Check if horses are finishing close (2nd-4th) or nowhere
            close_finishes = sum(loss_data['by_position'].get(str(pos), 0) for pos in [2, 3, 4])
            nowhere = sum(loss_data['by_position'].get(str(pos), 0) for pos in range(5, 20))
            
            if close_finishes > total_losses * 0.5:
                insights['loss_patterns'].append(
                    f"{close_finishes} losses finished 2nd-4th (close calls) - consider Each Way bets"
                )
                insights['recommendations'].append("STRATEGY: Switch high-confidence WIN bets (>65%) to Each Way for better place coverage")
            
            if nowhere > total_losses * 0.6:
                insights['loss_patterns'].append(
                    f"{nowhere} losses finished 5th or worse (not competitive) - poor selection"
                )
                insights['recommendations'].append("SELECTION: Review horse form analysis - too many uncompetitive picks, need stricter filters")
    
    # Analyze odds ranges
    best_odds_roi = -999
    best_odds_range = None
    worst_odds_roi = 999
    worst_odds_range = None
    
    for odds_range, stats in analysis['by_odds_range'].items():
        if stats['count'] < 3:  # Need minimum sample
            continue
        roi = stats.get('roi', 0)
        if roi > best_odds_roi:
            best_odds_roi = roi
            best_odds_range = odds_range
        if roi < worst_odds_roi:
            worst_odds_roi = roi
            worst_odds_range = odds_range
    
    if best_odds_range and best_odds_roi > 5:
        insights['strengths'].append(f"Strong performance on {best_odds_range} odds ({best_odds_roi:.1f}% ROI)")
        insights['recommendations'].append(f"Increase stake on {best_odds_range} selections")
    
    if worst_odds_range and worst_odds_roi < -10:
        insights['weaknesses'].append(f"Poor performance on {worst_odds_range} odds ({worst_odds_roi:.1f}% ROI)")
        insights['recommendations'].append(f"Reduce or avoid {worst_odds_range} selections")
    
    # Analyze decision ratings
    for rating in ['DO IT', 'RISKY', 'NOT GREAT']:
        stats = analysis['by_decision_rating'].get(rating, {})
        if stats.get('count', 0) >= 3:
            roi = stats.get('roi', 0)
            win_rate = stats.get('win_rate', 0)
            
            if rating == 'DO IT':
                if roi > 10:
                    insights['strengths'].append(f"'{rating}' picks performing well ({roi:.1f}% ROI, {win_rate*100:.1f}% win rate)")
                elif roi < 0:
                    insights['weaknesses'].append(f"'{rating}' picks underperforming ({roi:.1f}% ROI)")
                    insights['recommendations'].append("Review criteria for 'DO IT' rating - may be too optimistic")
            
            elif rating == 'RISKY':
                if roi > 5:
                    insights['strengths'].append(f"'{rating}' picks justified ({roi:.1f}% ROI)")
                elif roi < -5:
                    insights['weaknesses'].append(f"'{rating}' picks too risky ({roi:.1f}% ROI)")
                    insights['recommendations'].append("Reduce stakes or avoid 'RISKY' selections")
    
    # Best courses
    best_courses = sorted(
        [(course, stats) for course, stats in analysis['by_course'].items() if stats['count'] >= 3],
        key=lambda x: x[1].get('roi', 0),
        reverse=True
    )[:3]
    
    if best_courses and best_courses[0][1]['roi'] > 10:
        course, stats = best_courses[0]
        insights['strengths'].append(f"Excellent at {course} ({stats['roi']:.1f}% ROI, {stats['wins']}/{stats['count']} wins)")
    
    # Overall performance
    overall_roi = analysis['overall']['roi']
    if overall_roi > 5:
        insights['strengths'].append(f"Profitable overall: {overall_roi:.1f}% ROI")
    elif overall_roi < 0:
        insights['weaknesses'].append(f"Losing overall: {overall_roi:.1f}% ROI")
        insights['recommendations'].append("Consider reducing stakes or reviewing selection criteria")
    
    return insights

def store_learning_data(analysis, insights):
    """Store performance data and insights in DynamoDB"""
    try:
        learning_table = dynamodb.Table(learning_table_name)
    except:
        # Table doesn't exist, create it
        print(f"Creating {learning_table_name} table...")
        dynamodb.create_table(
            TableName=learning_table_name,
            KeySchema=[
                {'AttributeName': 'period', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'period', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Waiting for table creation...")
        dynamodb.meta.client.get_waiter('table_exists').wait(TableName=learning_table_name)
        learning_table = dynamodb.Table(learning_table_name)
    
    # Convert to JSON-serializable format
    def convert_to_json(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, defaultdict) or isinstance(obj, dict):
            return {k: convert_to_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_json(v) for v in obj]
        return obj
    
    analysis_json = convert_to_json(analysis)
    
    # Store in DynamoDB
    item = {
        'period': 'last_7_days',
        'timestamp': datetime.utcnow().isoformat(),
        'analysis': json.dumps(analysis_json),
        'insights': json.dumps(insights),
        'overall_roi': Decimal(str(analysis['overall']['roi'])),
        'overall_win_rate': Decimal(str(analysis['overall']['win_rate'])),
        'total_bets': analysis['overall']['total_bets'],
        'total_pnl': Decimal(str(analysis['overall']['total_pnl']))
    }
    
    learning_table.put_item(Item=item)
    print(f"✓ Stored learning data in {learning_table_name}")

def lambda_handler(event, context):
    """Main Lambda handler"""
    
    print("=== LEARNING ANALYSIS ===")
    print(f"Time: {datetime.utcnow().isoformat()}")
    
    # Get results from last 7 days
    results = get_results_for_period(days=7)
    
    if len(results) < 5:
        print("Not enough results for analysis (need at least 5)")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Insufficient data', 'results_count': len(results)})
        }
    
    # Analyze performance
    print("\nAnalyzing performance patterns...")
    analysis = analyze_performance(results)
    
    # Generate insights
    print("\nGenerating insights...")
    insights = generate_insights(analysis)
    
    # Print summary
    print("\n=== PERFORMANCE SUMMARY ===")
    print(f"Total bets: {analysis['overall']['total_bets']}")
    print(f"Win rate: {analysis['overall']['win_rate']*100:.1f}%")
    print(f"ROI: {analysis['overall']['roi']:.1f}%")
    print(f"Total P&L: €{analysis['overall']['total_pnl']:.2f}")
    
    print("\n=== LOSS ANALYSIS ===")
    loss_data = analysis['loss_analysis']
    print(f"Total losses: {loss_data['total_losses']}")
    print(f"Favorites lost: {loss_data['favorites_lost']}")
    print(f"Longshots lost: {loss_data['longshots_lost']}")
    print(f"High confidence losses: {loss_data['high_confidence_losses']}")
    print(f"'DO IT' rating losses: {loss_data['do_it_losses']}")
    if loss_data['by_position']:
        print(f"Finish positions: {dict(loss_data['by_position'])}")
    
    print("\n=== INSIGHTS ===")
    for pattern in insights['loss_patterns']:
        print(f"📊 LOSS PATTERN: {pattern}")
    for strength in insights['strengths']:
        print(f"✓ {strength}")
    for weakness in insights['weaknesses']:
        print(f"⚠ {weakness}")
    
    print("\n=== RECOMMENDATIONS (Auto-applied to next run) ===")
    for rec in insights['recommendations']:
        print(f"→ {rec}")
    
    # Store learning data
    store_learning_data(analysis, insights)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Learning analysis complete',
            'results_analyzed': len(results),
            'roi': float(analysis['overall']['roi']),
            'win_rate': float(analysis['overall']['win_rate']),
            'insights': insights
        })
    }
