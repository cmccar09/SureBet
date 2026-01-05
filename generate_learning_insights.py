"""
generate_learning_insights.py - Extract learnings from performance data

Analyzes historical betting results to generate insights that improve
future selections. Creates learning_insights.json that enhanced_analysis.py
can load to adapt its strategy.
"""

import json
import pandas as pd
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict


def load_all_results(days_back: int = 30) -> List[Dict]:
    """Load all results from history folder"""
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    results = []
    history_path = Path(__file__).parent / "history"
    
    for results_file in history_path.glob("results_*.json"):
        # Extract date from filename (results_20260104.json)
        date_str = results_file.stem.replace("results_", "")
        try:
            file_date = datetime.strptime(date_str, "%Y%m%d")
            if file_date >= cutoff_date:
                with open(results_file, 'r') as f:
                    data = json.load(f)
                    results.append({
                        'date': date_str,
                        'data': data
                    })
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Skipping {results_file}: {e}")
            continue
    
    return results


def merge_all_selections_with_results(days_back: int = 30) -> pd.DataFrame:
    """Merge selections with results across all days"""
    
    history_path = Path(__file__).parent / "history"
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    all_data = []
    
    # Find all selection files
    for selections_file in sorted(history_path.glob("selections_*.csv")):
        # Extract date from filename
        date_str = selections_file.stem.split('_')[1]  # selections_20260104_hhmmss.csv
        
        try:
            file_date = datetime.strptime(date_str, "%Y%m%d")
            if file_date < cutoff_date:
                continue
            
            # Load selections
            selections_df = pd.read_csv(selections_file)
            
            # Find corresponding results file
            results_file = history_path / f"results_{date_str}.json"
            
            if not results_file.exists():
                print(f"No results for {date_str} yet")
                continue
            
            with open(results_file, 'r') as f:
                results_data = json.load(f)
            
            # Results can be either:
            # 1. Flat list of runners with market_id/selection_id
            # 2. Nested dict with 'markets' key containing runners
            if isinstance(results_data, list):
                # Check if it's a flat list (new format)
                if results_data and 'market_id' in results_data[0]:
                    # Flat format: convert to dict for easier lookup
                    results_lookup = {
                        (str(r.get('market_id')), str(r.get('selection_id'))): r 
                        for r in results_data
                    }
                else:
                    # Old nested format
                    markets = results_data
                    results_lookup = None
            else:
                markets = results_data.get('markets', [])
                results_lookup = None
            
            # Merge selections with results
            for _, row in selections_df.iterrows():
                selection_id = str(row.get('selection_id', ''))
                market_id = str(row.get('market_id', ''))
                
                # Find result for this selection
                result = None
                
                # Use flat lookup if available
                if results_lookup is not None:
                    result = results_lookup.get((market_id, selection_id))
                else:
                    # Old nested format
                    for market in markets:
                        if str(market.get('market_id')) == market_id:
                            for runner in market.get('runners', []):
                                if str(runner.get('selection_id')) == selection_id:
                                    result = runner
                                    break
                            break
                
                if result:
                    # Handle both old and new status formats
                    status = result.get('status', 'UNKNOWN')
                    is_winner = result.get('is_winner', False) or status == 'WINNER'
                    is_placed = result.get('is_placed', False) or status in ['WINNER', 'PLACED']
                    
                    merged = {
                        'date': date_str,
                        'runner_name': row.get('runner_name', ''),
                        'venue': row.get('venue', ''),
                        'market_name': row.get('market_name', ''),
                        'p_win': float(row.get('p_win', 0)),
                        'p_place': float(row.get('p_place', 0)),
                        'bet_type': row.get('bet_type', 'EW'),
                        'tags': row.get('tags', ''),
                        'why_now': row.get('why_now', ''),
                        'status': status,
                        'won': is_winner,
                        'placed': is_placed
                    }
                    all_data.append(merged)
        
        except Exception as e:
            print(f"Error processing {selections_file}: {e}")
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    return pd.DataFrame(all_data)


def analyze_tag_performance(df: pd.DataFrame) -> Dict[str, Dict]:
    """Analyze which selection strategies work best"""
    
    tag_stats = defaultdict(lambda: {'wins': 0, 'places': 0, 'total': 0, 'p_win_avg': []})
    
    for _, row in df.iterrows():
        tags = str(row.get('tags', '')).split(',')
        
        for tag in tags:
            tag = tag.strip()
            if not tag or tag == 'enhanced_analysis':
                continue
            
            tag_stats[tag]['total'] += 1
            tag_stats[tag]['p_win_avg'].append(row.get('p_win', 0))
            
            if row.get('won', False):
                tag_stats[tag]['wins'] += 1
            if row.get('placed', False):
                tag_stats[tag]['places'] += 1
    
    # Calculate rates
    results = {}
    for tag, stats in tag_stats.items():
        if stats['total'] >= 3:  # Minimum sample size
            win_rate = stats['wins'] / stats['total']
            place_rate = stats['places'] / stats['total']
            avg_p_win = sum(stats['p_win_avg']) / len(stats['p_win_avg'])
            
            results[tag] = {
                'win_rate': win_rate,
                'place_rate': place_rate,
                'expected_win_rate': avg_p_win,
                'calibration': win_rate - avg_p_win,
                'sample_size': stats['total'],
                'verdict': 'WORKING' if win_rate >= avg_p_win * 0.8 else 'FAILING'
            }
    
    return results


def extract_pattern_learnings(df: pd.DataFrame, tag_performance: Dict) -> Dict[str, Any]:
    """Extract specific learnings from the data"""
    
    learnings = {
        'generated_at': datetime.now().isoformat(),
        'sample_size': len(df),
        'date_range': f"{df['date'].min()} to {df['date'].max()}" if len(df) > 0 else "No data",
        'overall_stats': {},
        'winning_patterns': [],
        'failing_patterns': [],
        'recommendations': []
    }
    
    if len(df) == 0:
        learnings['recommendations'].append("Insufficient data - need at least 30 days of results")
        return learnings
    
    # Overall stats
    learnings['overall_stats'] = {
        'total_bets': len(df),
        'wins': int(df['won'].sum()),
        'win_rate': float(df['won'].mean()),
        'places': int(df['placed'].sum()),
        'place_rate': float(df['placed'].mean()),
        'avg_p_win': float(df['p_win'].mean())
    }
    
    # Winning patterns (tags that outperform)
    for tag, stats in tag_performance.items():
        if stats['verdict'] == 'WORKING' and stats['sample_size'] >= 5:
            learnings['winning_patterns'].append({
                'pattern': tag,
                'win_rate': f"{stats['win_rate']:.1%}",
                'expected': f"{stats['expected_win_rate']:.1%}",
                'sample_size': stats['sample_size'],
                'action': 'KEEP - this strategy is working'
            })
    
    # Failing patterns (tags that underperform)
    for tag, stats in tag_performance.items():
        if stats['verdict'] == 'FAILING' and stats['sample_size'] >= 5:
            learnings['failing_patterns'].append({
                'pattern': tag,
                'win_rate': f"{stats['win_rate']:.1%}",
                'expected': f"{stats['expected_win_rate']:.1%}",
                'sample_size': stats['sample_size'],
                'action': 'REDUCE - underperforming expectations'
            })
    
    # Generate recommendations
    overall_win_rate = learnings['overall_stats']['win_rate']
    avg_p_win = learnings['overall_stats']['avg_p_win']
    
    if overall_win_rate < avg_p_win * 0.7:
        learnings['recommendations'].append(
            f"CRITICAL: Win rate ({overall_win_rate:.1%}) is significantly below predictions ({avg_p_win:.1%}). "
            "AI is overconfident. Consider increasing selectivity or adjusting probability estimates."
        )
    elif overall_win_rate > avg_p_win * 1.2:
        learnings['recommendations'].append(
            f"OPPORTUNITY: Win rate ({overall_win_rate:.1%}) exceeds predictions ({avg_p_win:.1%}). "
            "AI is underconfident. Consider being more aggressive with Win bets."
        )
    else:
        learnings['recommendations'].append(
            f"CALIBRATED: Win rate ({overall_win_rate:.1%}) matches predictions ({avg_p_win:.1%}). "
            "Probability model is well-calibrated."
        )
    
    # Win vs EW performance
    if 'bet_type' in df.columns:
        win_bets = df[df['bet_type'] == 'WIN']
        ew_bets = df[df['bet_type'] == 'EW']
        
        if len(win_bets) >= 5:
            win_strike_rate = win_bets['won'].mean()
            learnings['recommendations'].append(
                f"Win bets: {len(win_bets)} bets, {win_strike_rate:.1%} strike rate"
            )
        
        if len(ew_bets) >= 5:
            ew_place_rate = ew_bets['placed'].mean()
            learnings['recommendations'].append(
                f"EW bets: {len(ew_bets)} bets, {ew_place_rate:.1%} place rate"
            )
    
    return learnings


def generate_prompt_guidance(learnings: Dict) -> str:
    """Generate guidance text to add to AI prompts"""
    
    if learnings['sample_size'] < 10:
        return "INSUFFICIENT DATA - Continue with standard analysis approach."
    
    guidance = f"""
HISTORICAL PERFORMANCE INSIGHTS (Last {learnings['sample_size']} bets):

WHAT'S WORKING:
"""
    
    for pattern in learnings['winning_patterns'][:5]:  # Top 5
        guidance += f"- {pattern['pattern']}: {pattern['win_rate']} win rate (expected {pattern['expected']})\n"
    
    if learnings['failing_patterns']:
        guidance += "\nWHAT'S NOT WORKING:\n"
        for pattern in learnings['failing_patterns'][:5]:
            guidance += f"- {pattern['pattern']}: {pattern['win_rate']} win rate (expected {pattern['expected']}) - BE CAUTIOUS\n"
    
    guidance += "\nRECOMMENDATIONS:\n"
    for rec in learnings['recommendations']:
        guidance += f"- {rec}\n"
    
    return guidance


def main():
    """Generate learning insights from historical data"""
    
    print("="*60)
    print("Generating Learning Insights")
    print("="*60)
    
    # Load and merge all data
    print("\nLoading historical data (last 30 days)...")
    df = merge_all_selections_with_results(days_back=30)
    
    if len(df) == 0:
        print("No historical data found yet")
        
        # Create empty insights file
        empty_insights = {
            'generated_at': datetime.now().isoformat(),
            'sample_size': 0,
            'message': 'Insufficient data - need settled results from at least 5 days',
            'prompt_guidance': 'INSUFFICIENT DATA - Continue with standard analysis approach.'
        }
        
        output_file = Path(__file__).parent / "learning_insights.json"
        with open(output_file, 'w') as f:
            json.dump(empty_insights, f, indent=2)
        
        print(f"Created placeholder: {output_file}")
        return
    
    print(f"Loaded {len(df)} historical bets")
    
    # Analyze performance
    print("\nAnalyzing tag performance...")
    tag_performance = analyze_tag_performance(df)
    
    print(f"Found {len(tag_performance)} distinct strategies")
    
    # Extract learnings
    print("\nGenerating insights...")
    learnings = extract_pattern_learnings(df, tag_performance)
    
    # Generate prompt guidance
    prompt_guidance = generate_prompt_guidance(learnings)
    learnings['prompt_guidance'] = prompt_guidance
    
    # Save to file
    output_file = Path(__file__).parent / "learning_insights.json"
    with open(output_file, 'w') as f:
        json.dump(learnings, f, indent=2)
    
    print(f"\n[OK] Saved insights to: {output_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Sample size: {learnings['sample_size']} bets")
    print(f"Win rate: {learnings['overall_stats']['win_rate']:.1%}")
    print(f"Expected: {learnings['overall_stats']['avg_p_win']:.1%}")
    print(f"\nWorking patterns: {len(learnings['winning_patterns'])}")
    print(f"Failing patterns: {len(learnings['failing_patterns'])}")
    print(f"\nRecommendations: {len(learnings['recommendations'])}")
    
    print("\n" + "="*60)
    print("PROMPT GUIDANCE")
    print("="*60)
    print(prompt_guidance)


if __name__ == "__main__":
    main()
