#!/usr/bin/env python3
"""
analyze_prediction_calibration.py - V2.2 Prediction Accountability System

Analyzes prediction accuracy by:
1. Grouping predictions into calibration bins (0-20%, 20-40%, etc.)
2. Comparing predicted probabilities vs actual win rates
3. Calculating Brier score and calibration metrics
4. Identifying systematic failures ("why were we wrong?")
5. Validating successful predictions ("why were we right?")
6. Generating actionable insights for confidence recalibration
"""

import boto3
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple


def load_picks_with_results(days_back: int = 7) -> pd.DataFrame:
    """Load picks with outcomes from DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('SureBetBets')
    
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    all_picks = []
    
    # Query for each date in range
    for i in range(days_back):
        query_date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        
        try:
            response = table.query(
                KeyConditionExpression='bet_date = :date',
                ExpressionAttributeValues={':date': query_date}
            )
            
            picks = response.get('Items', [])
            
            # Filter for picks with outcomes
            for pick in picks:
                outcome = pick.get('outcome', pick.get('actual_result', ''))
                if outcome and outcome.lower() != 'pending':
                    all_picks.append(pick)
                    
        except Exception as e:
            print(f"Error querying {query_date}: {e}")
            continue
    
    if not all_picks:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(all_picks)
    
    # Standardize outcome field
    if 'outcome' in df.columns:
        df['result'] = df['outcome'].str.lower()
    elif 'actual_result' in df.columns:
        df['result'] = df['actual_result'].str.lower()
    else:
        df['result'] = 'unknown'
    
    # Convert to binary win flag
    df['won'] = df['result'].isin(['win', 'won']).astype(int)
    df['placed'] = df['result'].isin(['placed', 'place']).astype(int)
    
    # Extract numeric fields
    df['p_win'] = pd.to_numeric(df.get('p_win', 0), errors='coerce').fillna(0)
    df['confidence'] = pd.to_numeric(df.get('confidence', 0), errors='coerce').fillna(0)
    df['odds'] = pd.to_numeric(df.get('odds', 0), errors='coerce').fillna(0)
    
    return df


def calculate_calibration_bins(df: pd.DataFrame) -> Dict[str, Any]:
    """Group predictions into bins and check calibration"""
    
    if len(df) == 0 or 'p_win' not in df.columns:
        return {}
    
    # Define bins
    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    labels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
    
    df['confidence_bin'] = pd.cut(df['p_win'], bins=bins, labels=labels, include_lowest=True)
    
    calibration_analysis = {}
    
    for bin_name in labels:
        bin_df = df[df['confidence_bin'] == bin_name]
        
        if len(bin_df) == 0:
            continue
        
        predicted_avg = bin_df['p_win'].mean()
        actual_rate = bin_df['won'].mean()
        sample_size = len(bin_df)
        
        calibration_error = actual_rate - predicted_avg
        
        # Determine verdict
        if sample_size < 5:
            verdict = 'INSUFFICIENT DATA'
        elif abs(calibration_error) <= 0.1:
            verdict = 'CALIBRATED ✅'
        elif calibration_error < -0.1:
            verdict = 'OVERCONFIDENT ⚠️'
        else:
            verdict = 'UNDERCONFIDENT ⚠️'
        
        calibration_analysis[bin_name] = {
            'predicted': round(predicted_avg, 3),
            'actual': round(actual_rate, 3),
            'calibration_error': round(calibration_error, 3),
            'sample_size': sample_size,
            'wins': int(bin_df['won'].sum()),
            'verdict': verdict
        }
    
    return calibration_analysis


def calculate_brier_score(df: pd.DataFrame) -> float:
    """Calculate Brier score - measures prediction accuracy (0 = perfect, 0.25 = random)"""
    
    if len(df) == 0 or 'p_win' not in df.columns:
        return None
    
    # Brier score = mean((predicted - actual)^2)
    brier = np.mean((df['p_win'] - df['won']) ** 2)
    
    return round(brier, 4)


def calculate_expected_vs_actual(df: pd.DataFrame) -> Dict[str, Any]:
    """Compare expected wins vs actual wins"""
    
    if len(df) == 0:
        return {}
    
    expected_wins = df['p_win'].sum()
    actual_wins = df['won'].sum()
    
    if expected_wins > 0:
        calibration_ratio = actual_wins / expected_wins
    else:
        calibration_ratio = 0
    
    return {
        'expected_wins': round(expected_wins, 2),
        'actual_wins': int(actual_wins),
        'calibration_ratio': round(calibration_ratio, 3),
        'verdict': 'OVERCONFIDENT' if calibration_ratio < 0.85 else 
                  'UNDERCONFIDENT' if calibration_ratio > 1.15 else 'CALIBRATED'
    }


def analyze_failed_predictions(df: pd.DataFrame) -> Dict[str, Any]:
    """Deep dive into high-confidence losses - Why were we wrong?"""
    
    if len(df) == 0:
        return {}
    
    # High confidence losses (predicted 40%+ to win but lost)
    high_conf_losses = df[(df['p_win'] >= 0.4) & (df['won'] == 0)].copy()
    
    if len(high_conf_losses) == 0:
        return {'count': 0, 'patterns': {}, 'recommendations': []}
    
    failure_patterns = {}
    
    # Pattern 1: By trainer
    if 'trainer' in high_conf_losses.columns:
        trainer_failures = high_conf_losses.groupby('trainer').size().to_dict()
        # Only show trainers with 3+ failures
        trainer_failures = {k: v for k, v in trainer_failures.items() if v >= 3}
        if trainer_failures:
            failure_patterns['by_trainer'] = trainer_failures
    
    # Pattern 2: By course
    if 'course' in high_conf_losses.columns:
        course_failures = high_conf_losses.groupby('course').size().to_dict()
        course_failures = {k: v for k, v in course_failures.items() if v >= 3}
        if course_failures:
            failure_patterns['by_course'] = course_failures
    
    # Pattern 3: By odds range
    if 'odds' in high_conf_losses.columns:
        high_conf_losses['odds_range'] = pd.cut(
            high_conf_losses['odds'],
            bins=[0, 3, 4, 5, 6, 9, 20],
            labels=['<3.0', '3-4', '4-5', '5-6', '6-9', '9+']
        )
        odds_failures = high_conf_losses.groupby('odds_range').size().to_dict()
        failure_patterns['by_odds_range'] = {str(k): v for k, v in odds_failures.items()}
    
    # Pattern 4: By tags (if available)
    if 'tags' in high_conf_losses.columns:
        tag_failures = defaultdict(int)
        for tags in high_conf_losses['tags'].dropna():
            if isinstance(tags, str):
                tags = tags.split(',')
            for tag in tags:
                tag_failures[tag.strip()] += 1
        
        # Only tags with 3+ failures
        tag_failures = {k: v for k, v in tag_failures.items() if v >= 3}
        if tag_failures:
            failure_patterns['by_tag'] = dict(tag_failures)
    
    # Generate recommendations
    recommendations = []
    
    for trainer, count in failure_patterns.get('by_trainer', {}).items():
        recommendations.append({
            'type': 'TRAINER_ISSUE',
            'trainer': trainer,
            'failures': count,
            'action': f"Reduce confidence for {trainer} by 20-30%",
            'reason': f"{count} high-confidence losses - recent form not translating"
        })
    
    for course, count in failure_patterns.get('by_course', {}).items():
        recommendations.append({
            'type': 'COURSE_ISSUE',
            'course': course,
            'failures': count,
            'action': f"Review course-specific factors at {course}",
            'reason': f"{count} high-confidence losses - may have track bias or unknown factors"
        })
    
    for tag, count in failure_patterns.get('by_tag', {}).items():
        recommendations.append({
            'type': 'TAG_FAILING',
            'tag': tag,
            'failures': count,
            'action': f"Reduce confidence boost for '{tag}' tag by 10-15 points",
            'reason': f"{count} high-confidence losses with this tag - signal not reliable"
        })
    
    return {
        'count': len(high_conf_losses),
        'avg_predicted_p_win': round(high_conf_losses['p_win'].mean(), 3),
        'avg_confidence': round(high_conf_losses['confidence'].mean(), 1),
        'patterns': failure_patterns,
        'recommendations': recommendations
    }


def analyze_successful_predictions(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate wins - Why were we right?"""
    
    if len(df) == 0:
        return {}
    
    # Successful predictions (predicted 30%+ and won)
    successes = df[(df['p_win'] >= 0.3) & (df['won'] == 1)].copy()
    
    if len(successes) == 0:
        return {'count': 0, 'patterns': {}, 'reinforcements': []}
    
    success_patterns = {}
    
    # Pattern 1: By trainer
    if 'trainer' in successes.columns:
        trainer_wins = successes.groupby('trainer').size().to_dict()
        trainer_wins = {k: v for k, v in trainer_wins.items() if v >= 2}
        if trainer_wins:
            success_patterns['by_trainer'] = trainer_wins
    
    # Pattern 2: By course
    if 'course' in successes.columns:
        course_wins = successes.groupby('course').size().to_dict()
        course_wins = {k: v for k, v in course_wins.items() if v >= 2}
        if course_wins:
            success_patterns['by_course'] = course_wins
    
    # Pattern 3: By odds range (sweet spot validation)
    if 'odds' in successes.columns:
        successes['odds_range'] = pd.cut(
            successes['odds'],
            bins=[0, 3, 4, 5, 6, 9, 20],
            labels=['<3.0', '3-4', '4-5', '5-6', '6-9', '9+']
        )
        odds_wins = successes.groupby('odds_range').size().to_dict()
        success_patterns['by_odds_range'] = {str(k): v for k, v in odds_wins.items()}
    
    # Pattern 4: By tags (what's working)
    if 'tags' in successes.columns:
        tag_wins = defaultdict(int)
        for tags in successes['tags'].dropna():
            if isinstance(tags, str):
                tags = tags.split(',')
            for tag in tags:
                tag_wins[tag.strip()] += 1
        
        tag_wins = {k: v for k, v in tag_wins.items() if v >= 2}
        if tag_wins:
            success_patterns['by_tag'] = dict(tag_wins)
    
    # Generate reinforcements
    reinforcements = []
    
    for trainer, count in success_patterns.get('by_trainer', {}).items():
        reinforcements.append({
            'type': 'TRAINER_SUCCESS',
            'trainer': trainer,
            'wins': count,
            'action': f"Maintain or increase confidence for {trainer}",
            'reason': f"{count} wins - trainer form is reliable signal"
        })
    
    for course, count in success_patterns.get('by_course', {}).items():
        reinforcements.append({
            'type': 'COURSE_SUCCESS',
            'course': course,
            'wins': count,
            'action': f"Track trainer/jockey patterns at {course}",
            'reason': f"{count} wins - understanding this course well"
        })
    
    for tag, count in success_patterns.get('by_tag', {}).items():
        reinforcements.append({
            'type': 'TAG_WORKING',
            'tag': tag,
            'wins': count,
            'action': f"Reinforce '{tag}' tag - add +5-10 confidence points",
            'reason': f"{count} wins - this signal is working"
        })
    
    # Sweet spot validation
    sweet_spot_wins = success_patterns.get('by_odds_range', {})
    total_sweet_spot_wins = sum(
        v for k, v in sweet_spot_wins.items() 
        if k in ['3-4', '4-5', '5-6', '6-9']
    )
    
    if total_sweet_spot_wins >= len(successes) * 0.6:  # 60%+ wins in sweet spot
        reinforcements.append({
            'type': 'SWEET_SPOT_CONFIRMED',
            'wins': total_sweet_spot_wins,
            'percentage': round(total_sweet_spot_wins / len(successes) * 100, 1),
            'action': "Continue focusing on 3.0-9.0 odds range",
            'reason': f"{total_sweet_spot_wins}/{len(successes)} wins in sweet spot - strategy validated"
        })
    
    return {
        'count': len(successes),
        'avg_predicted_p_win': round(successes['p_win'].mean(), 3),
        'avg_confidence': round(successes['confidence'].mean(), 1),
        'patterns': success_patterns,
        'reinforcements': reinforcements
    }


def generate_calibration_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive calibration report"""
    
    if len(df) == 0:
        return {
            'generated_at': datetime.now().isoformat(),
            'sample_size': 0,
            'message': 'No data available for calibration analysis'
        }
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'sample_size': len(df),
        'date_range': {
            'start': df['bet_date'].min() if 'bet_date' in df.columns else 'unknown',
            'end': df['bet_date'].max() if 'bet_date' in df.columns else 'unknown'
        }
    }
    
    # Overall stats
    report['overall'] = {
        'total_picks': len(df),
        'wins': int(df['won'].sum()),
        'win_rate': round(df['won'].mean(), 3),
        'avg_predicted_p_win': round(df['p_win'].mean(), 3),
        'avg_confidence': round(df['confidence'].mean(), 1)
    }
    
    # Calibration analysis
    report['calibration_bins'] = calculate_calibration_bins(df)
    
    # Brier score
    report['brier_score'] = {
        'score': calculate_brier_score(df),
        'interpretation': 'Good' if calculate_brier_score(df) < 0.20 else 
                         'Needs improvement' if calculate_brier_score(df) < 0.25 else 
                         'Poor',
        'target': '< 0.20'
    }
    
    # Expected vs actual
    report['expected_vs_actual'] = calculate_expected_vs_actual(df)
    
    # Failed predictions analysis
    report['failures'] = analyze_failed_predictions(df)
    
    # Successful predictions validation
    report['successes'] = analyze_successful_predictions(df)
    
    # Overall verdict and actions
    report['verdict'] = generate_verdict(report)
    
    return report


def generate_verdict(report: Dict[str, Any]) -> Dict[str, Any]:
    """Generate overall verdict and action items"""
    
    verdict = {
        'calibration_status': 'UNKNOWN',
        'key_issues': [],
        'key_successes': [],
        'priority_actions': []
    }
    
    # Check calibration
    expected_vs_actual = report.get('expected_vs_actual', {})
    calibration_ratio = expected_vs_actual.get('calibration_ratio', 1.0)
    
    if 0.85 <= calibration_ratio <= 1.15:
        verdict['calibration_status'] = 'CALIBRATED ✅'
    elif calibration_ratio < 0.85:
        verdict['calibration_status'] = 'OVERCONFIDENT ⚠️'
        verdict['priority_actions'].append(
            f"Reduce overall confidence by {int((1 - calibration_ratio) * 100)}%"
        )
    else:
        verdict['calibration_status'] = 'UNDERCONFIDENT ⚠️'
        verdict['priority_actions'].append(
            "Can be more confident in selections - increase confidence by 10-15%"
        )
    
    # Check Brier score
    brier = report.get('brier_score', {}).get('score', 0.25)
    if brier >= 0.25:
        verdict['key_issues'].append(
            f"High Brier score ({brier}) - predictions not accurate enough"
        )
        verdict['priority_actions'].append(
            "Review selection criteria - focus on proven winners in sweet spot"
        )
    
    # Add failure recommendations
    failures = report.get('failures', {})
    for rec in failures.get('recommendations', [])[:3]:  # Top 3
        verdict['key_issues'].append(f"{rec['type']}: {rec['reason']}")
        verdict['priority_actions'].append(rec['action'])
    
    # Add success reinforcements
    successes = report.get('successes', {})
    for reinforce in successes.get('reinforcements', [])[:3]:  # Top 3
        verdict['key_successes'].append(f"{reinforce['type']}: {reinforce['reason']}")
        if 'SWEET_SPOT' in reinforce['type']:
            verdict['priority_actions'].insert(0, reinforce['action'])  # Priority
    
    return verdict


def print_calibration_report(report: Dict[str, Any]):
    """Pretty print the calibration report"""
    
    print("\n" + "="*80)
    print("🎯 PREDICTION CALIBRATION ANALYSIS")
    print("="*80)
    
    print(f"\nGenerated: {report['generated_at'][:19]}")
    print(f"Sample size: {report['sample_size']} picks")
    
    if report['sample_size'] < 10:
        print("\n⚠️ WARNING: Insufficient data for reliable calibration analysis")
        print("   Need at least 10 settled picks for meaningful insights")
        return
    
    # Overall stats
    overall = report.get('overall', {})
    print(f"\n📊 OVERALL PERFORMANCE:")
    print(f"   Wins: {overall['wins']}/{overall['total_picks']} ({overall['win_rate']:.1%})")
    print(f"   Predicted avg: {overall['avg_predicted_p_win']:.1%}")
    print(f"   Avg confidence: {overall['avg_confidence']:.1f}%")
    
    # Calibration bins
    print(f"\n📈 CALIBRATION BY CONFIDENCE BINS:")
    calibration = report.get('calibration_bins', {})
    for bin_name, stats in calibration.items():
        print(f"\n   {bin_name} predictions:")
        print(f"      Predicted: {stats['predicted']:.1%} | Actual: {stats['actual']:.1%} | Error: {stats['calibration_error']:+.1%}")
        print(f"      Sample: {stats['sample_size']} picks ({stats['wins']} wins)")
        print(f"      Status: {stats['verdict']}")
    
    # Brier score
    brier = report.get('brier_score', {})
    print(f"\n🎲 BRIER SCORE:")
    print(f"   Score: {brier['score']:.4f} ({brier['interpretation']})")
    print(f"   Target: {brier['target']}")
    
    # Expected vs Actual
    exp_actual = report.get('expected_vs_actual', {})
    print(f"\n⚖️ EXPECTED VS ACTUAL:")
    print(f"   Expected wins: {exp_actual['expected_wins']:.1f}")
    print(f"   Actual wins: {exp_actual['actual_wins']}")
    print(f"   Ratio: {exp_actual['calibration_ratio']:.3f} ({exp_actual['verdict']})")
    
    # Failures
    failures = report.get('failures', {})
    if failures.get('count', 0) > 0:
        print(f"\n❌ HIGH CONFIDENCE FAILURES: {failures['count']} losses")
        print(f"   Avg predicted: {failures['avg_predicted_p_win']:.1%}")
        
        if failures.get('recommendations'):
            print(f"\n   ⚠️ SYSTEMATIC ISSUES FOUND:")
            for rec in failures['recommendations'][:5]:
                print(f"      • {rec['type']}: {rec['reason']}")
                print(f"        Action: {rec['action']}")
    
    # Successes
    successes = report.get('successes', {})
    if successes.get('count', 0) > 0:
        print(f"\n✅ SUCCESSFUL PREDICTIONS: {successes['count']} wins")
        print(f"   Avg predicted: {successes['avg_predicted_p_win']:.1%}")
        
        if successes.get('reinforcements'):
            print(f"\n   🎯 WORKING STRATEGIES:")
            for reinforce in successes['reinforcements'][:5]:
                print(f"      • {reinforce['type']}: {reinforce['reason']}")
                print(f"        Action: {reinforce['action']}")
    
    # Verdict
    verdict = report.get('verdict', {})
    print(f"\n" + "="*80)
    print(f"📋 OVERALL VERDICT: {verdict['calibration_status']}")
    print("="*80)
    
    if verdict.get('key_issues'):
        print(f"\n⚠️ KEY ISSUES:")
        for issue in verdict['key_issues']:
            print(f"   • {issue}")
    
    if verdict.get('key_successes'):
        print(f"\n✅ KEY SUCCESSES:")
        for success in verdict['key_successes']:
            print(f"   • {success}")
    
    if verdict.get('priority_actions'):
        print(f"\n🔧 PRIORITY ACTIONS:")
        for i, action in enumerate(verdict['priority_actions'], 1):
            print(f"   {i}. {action}")
    
    print("\n" + "="*80)


def main():
    """Run calibration analysis"""
    
    print("Loading picks with results from last 7 days...")
    df = load_picks_with_results(days_back=7)
    
    if len(df) == 0:
        print("No picks with results found in last 7 days")
        return
    
    print(f"Loaded {len(df)} picks with outcomes")
    
    # Generate calibration report
    report = generate_calibration_report(df)
    
    # Save to file
    output_file = Path(__file__).parent / "calibration_report.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Saved calibration report to: {output_file}")
    
    # Print report
    print_calibration_report(report)
    
    print(f"\n✅ Calibration analysis complete")


if __name__ == "__main__":
    main()
