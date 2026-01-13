#!/usr/bin/env python3
"""
evaluate_performance.py - Analyze prediction accuracy and calculate performance metrics
Compares selections vs actual results to identify what's working and what needs adjustment
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd

def load_selections(path: str) -> pd.DataFrame:
    """Load daily selections CSV"""
    if not os.path.exists(path):
        print(f"ERROR: Selections file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return pd.read_csv(path)

def load_results(path: str) -> pd.DataFrame:
    """Load race results JSON"""
    if not os.path.exists(path):
        print(f"ERROR: Results file not found: {path}", file=sys.stderr)
        sys.exit(1)
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    return pd.DataFrame(data)

def merge_selections_with_results(selections: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """Merge predictions with actual outcomes"""
    
    # Ensure results DataFrame has required columns
    if "selection_id" not in results.columns:
        print("ERROR: Results DataFrame missing 'selection_id' column", file=sys.stderr)
        print(f"Available columns: {results.columns.tolist()}", file=sys.stderr)
        return selections
    
    # Ensure numeric types for merge
    selections["selection_id"] = pd.to_numeric(selections["selection_id"], errors="coerce")
    selections["market_id"] = selections["market_id"].astype(str)
    
    results["selection_id"] = pd.to_numeric(results["selection_id"], errors="coerce")
    results["market_id"] = results["market_id"].astype(str)
    
    # Merge on both market_id and selection_id
    merged = selections.merge(
        results[["market_id", "selection_id", "is_winner", "is_placed"]],
        on=["market_id", "selection_id"],
        how="left"
    )
    
    return merged

def calculate_metrics(data: pd.DataFrame) -> Dict:
    """Calculate performance metrics"""
    
    total = len(data)
    if total == 0:
        return {}
    
    # Win/Place rates
    wins = data["is_winner"].sum() if "is_winner" in data.columns else 0
    places = data["is_placed"].sum() if "is_placed" in data.columns else 0
    
    win_rate = wins / total
    place_rate = places / total
    
    # Probability calibration (comparing predicted p_win vs actual outcomes)
    data["p_win"] = pd.to_numeric(data["p_win"], errors="coerce")
    data["p_place"] = pd.to_numeric(data["p_place"], errors="coerce")
    
    # Bin by predicted probability
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0]
    data["p_win_bin"] = pd.cut(data["p_win"], bins=bins)
    
    calibration = []
    for bin_label, group in data.groupby("p_win_bin"):
        if len(group) > 0:
            predicted_prob = group["p_win"].mean()
            actual_rate = group["is_winner"].mean() if "is_winner" in group.columns else 0
            count = len(group)
            
            calibration.append({
                "predicted_prob": predicted_prob,
                "actual_rate": actual_rate,
                "count": count,
                "error": abs(predicted_prob - actual_rate)
            })
    
    # ROI calculation (simplified - needs actual odds at bet time)
    # Assuming we bet 1 unit per selection
    stakes = total
    # Returns = sum of (stake * odds * is_winner) for each bet
    # For now, estimate using implied odds from p_win
    
    metrics = {
        "total_selections": total,
        "wins": int(wins),
        "places": int(places),
        "win_rate": round(win_rate, 3),
        "place_rate": round(place_rate, 3),
        "strike_rate_expected": round(data["p_win"].mean(), 3),
        "calibration_error": round(sum(c["error"] * c["count"] for c in calibration) / total if calibration else 0, 3),
        "calibration_by_bin": calibration
    }
    
    return metrics

def analyze_by_tags(data: pd.DataFrame) -> Dict:
    """Analyze performance by edge tag types"""
    
    tag_performance = {}
    
    # Parse tags column (comma-separated)
    data["tags"] = data["tags"].fillna("")
    
    # Common tag types from prompt
    tag_types = [
        "pace/draw edge",
        "class-drop sanity",
        "EW value",
        "Global Raider",
        "hot T-J combo",
        "market-confirmed",
        "draw-bias confirmed"
    ]
    
    for tag in tag_types:
        mask = data["tags"].str.contains(tag, case=False, na=False)
        subset = data[mask]
        
        if len(subset) > 0:
            wins = subset["is_winner"].sum() if "is_winner" in subset.columns else 0
            places = subset["is_placed"].sum() if "is_placed" in subset.columns else 0
            
            tag_performance[tag] = {
                "count": len(subset),
                "wins": int(wins),
                "win_rate": round(wins / len(subset), 3),
                "place_rate": round(places / len(subset), 3) if "is_placed" in subset.columns else 0
            }
    
    return tag_performance

def identify_adjustments(metrics: Dict, tag_performance: Dict) -> List[str]:
    """Identify recommended prompt adjustments based on performance"""
    
    adjustments = []
    
    # Calibration issues
    calib_error = metrics.get("calibration_error", 0)
    if calib_error > 0.1:
        adjustments.append(
            f"HIGH_PRIORITY: Calibration error is {calib_error:.1%}. "
            "Consider adjusting probability model or isotonic regression parameters."
        )
    
    # Strike rate too low
    win_rate = metrics.get("win_rate", 0)
    expected_rate = metrics.get("strike_rate_expected", 0)
    if win_rate < expected_rate * 0.7:  # More than 30% below expected
        adjustments.append(
            f"MEDIUM_PRIORITY: Win rate {win_rate:.1%} is significantly below expected {expected_rate:.1%}. "
            "Consider tightening overlay threshold or increasing min_back price filter."
        )
    
    # Tag-specific issues
    for tag, perf in tag_performance.items():
        if perf["count"] >= 5:  # Enough samples
            if perf["win_rate"] < 0.1:  # Less than 10% win rate
                adjustments.append(
                    f"LOW_PRIORITY: Tag '{tag}' has poor win rate ({perf['win_rate']:.1%} from {perf['count']} bets). "
                    "Consider removing or adjusting selection criteria for this edge type."
                )
            elif perf["win_rate"] > 0.25:  # Strong performer
                adjustments.append(
                    f"OPPORTUNITY: Tag '{tag}' performing well ({perf['win_rate']:.1%} from {perf['count']} bets). "
                    "Consider increasing allocation or relaxing filters for this edge type."
                )
    
    # Portfolio ROI
    if win_rate > 0 and win_rate < 0.15:  # Low hit rate
        adjustments.append(
            "MEDIUM_PRIORITY: Low strike rate suggests overlay threshold may need increase. "
            "Current: ≥10%. Consider testing ≥15% or ≥20%."
        )
    
    return adjustments

def generate_feedback_report(metrics: Dict, tag_performance: Dict, adjustments: List[str]) -> str:
    """Generate human-readable performance report"""
    
    report = f"""
# Performance Evaluation Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overall Metrics
- Total Selections: {metrics.get('total_selections', 0)}
- Wins: {metrics.get('wins', 0)} ({metrics.get('win_rate', 0):.1%})
- Places: {metrics.get('places', 0)} ({metrics.get('place_rate', 0):.1%})
- Expected Strike Rate: {metrics.get('strike_rate_expected', 0):.1%}
- Calibration Error: {metrics.get('calibration_error', 0):.1%}

## Calibration Analysis
"""
    
    for cal in metrics.get("calibration_by_bin", []):
        report += f"\\n- Predicted: {cal['predicted_prob']:.1%} -> Actual: {cal['actual_rate']:.1%} (n={cal['count']}, error={cal['error']:.1%})"
    
    report += "\n\n## Performance by Edge Type\n"
    for tag, perf in tag_performance.items():
        report += f"\n- **{tag}**: {perf['wins']}/{perf['count']} wins ({perf['win_rate']:.1%}), {perf['place_rate']:.1%} place rate"
    
    report += "\n\n## Recommended Adjustments\n"
    if adjustments:
        for i, adj in enumerate(adjustments, 1):
            report += f"\n{i}. {adj}\n"
    else:
        report += "\nNo adjustments needed - performance within expected parameters.\n"
    
    return report

def update_prompt_file(adjustments: List[str], prompt_path: str = "./prompt.txt", dry_run: bool = True):
    """Update prompt.txt with learned adjustments"""
    
    if not adjustments:
        print("No adjustments to apply")
        return
    
    # Read current prompt
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt = f.read()
    
    # Add performance-based adjustments section
    timestamp = datetime.now().strftime("%Y-%m-%d")
    
    adjustment_section = f"\n\n{'='*60}\nPerformance-Based Adjustments (Updated: {timestamp})\n{'='*60}\n\n"
    for i, adj in enumerate(adjustments, 1):
        adjustment_section += f"{i}. {adj}\n\n"
    
    # Append to prompt
    updated_prompt = prompt + adjustment_section
    
    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN - Would add to prompt.txt:")
        print("="*60)
        print(adjustment_section)
        print("\nRun with --apply to actually update prompt.txt")
    else:
        # Backup original
        backup_path = f"{prompt_path}.backup.{timestamp}"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"✓ Backed up original to: {backup_path}")
        
        # Write updated
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(updated_prompt)
        print(f"✓ Updated: {prompt_path}")

def main():
    parser = argparse.ArgumentParser(description="Evaluate prediction performance and suggest improvements")
    parser.add_argument("--selections", type=str, required=True, help="Path to selections CSV")
    parser.add_argument("--results", type=str, required=True, help="Path to results JSON")
    parser.add_argument("--report", type=str, default="./performance_report.md", help="Output report path")
    parser.add_argument("--prompt", type=str, default="./prompt.txt", help="Prompt file to update")
    parser.add_argument("--apply", action="store_true", help="Actually update prompt.txt (default: dry run)")
    
    args = parser.parse_args()
    
    # Load data
    print("Loading selections and results...")
    selections = load_selections(args.selections)
    results = load_results(args.results)
    
    # Merge
    data = merge_selections_with_results(selections, results)
    print(f"Matched {len(data)} selections with results")
    
    # Calculate metrics
    print("\nCalculating performance metrics...")
    metrics = calculate_metrics(data)
    tag_performance = analyze_by_tags(data)
    
    # Identify adjustments
    print("Identifying recommended adjustments...")
    adjustments = identify_adjustments(metrics, tag_performance)
    
    # Generate report
    report = generate_feedback_report(metrics, tag_performance, adjustments)
    
    # Save report
    with open(args.report, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nSaved report to: {args.report}")
    
    # Print summary
    print(report)
    
    # Update prompt if adjustments exist
    if adjustments:
        update_prompt_file(adjustments, args.prompt, dry_run=not args.apply)

if __name__ == "__main__":
    main()
