#!/usr/bin/env python3
"""
run_enhanced_analysis.py - Use the new enhanced multi-pass analysis system
Drop-in replacement for run_saved_prompt.py with superior analysis
"""

import os
import sys
import json
import csv
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from enhanced_analysis import EnhancedAnalyzer

def load_race_data(json_path: str) -> list:
    """Load race data from JSON snapshot"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different JSON formats
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        # Try different keys
        return data.get('races', data.get('result', data.get('markets', data.get('data', []))))
    else:
        print(f"ERROR: Unexpected JSON format", file=sys.stderr)
        return []

def save_selections_csv(selections: list, output_path: str):
    """Save selections to CSV format"""
    
    if not selections:
        print("No selections to save")
        return
    
    # Required columns
    columns = [
        "runner_name", "selection_id", "market_id", "market_name", "venue",
        "start_time_dublin", "p_win", "p_place", "bet_type", "ew_places", "ew_fraction",
        "tags", "why_now"
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        
        for sel in selections:
            # Build row with defaults for missing fields
            row = {
                "runner_name": sel.get('runner_name', ''),
                "selection_id": sel.get('selection_id', ''),
                "market_id": sel.get('market_id', ''),
                "market_name": sel.get('market_name', ''),
                "venue": sel.get('venue', ''),
                "start_time_dublin": sel.get('start_time_dublin', ''),
                "p_win": sel.get('p_win', 0.0),
                "p_place": sel.get('p_place', 0.0),
                "bet_type": sel.get('bet_type', 'EW'),  # Default to EW if not specified
                "ew_places": sel.get('ew_places', 3),  # Default 3 places
                "ew_fraction": sel.get('ew_fraction', 0.2),  # Default 1/5 odds
                "tags": "enhanced_analysis," + sel.get('strengths', ''),
                "why_now": sel.get('why_now', sel.get('reasoning', ''))
            }
            writer.writerow(row)
    
    print(f"[OK] Saved {len(selections)} selections to: {output_path}")

def main():
    """Main execution"""
    
    # Find latest snapshot
    snapshot_path = os.path.join('.', 'response_live.json')
    if not os.path.exists(snapshot_path):
        print(f"ERROR: Snapshot not found: {snapshot_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load race data
    print(f"Loading market data from: {snapshot_path}")
    races = load_race_data(snapshot_path)
    
    if not races:
        print("ERROR: No races found in snapshot", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(races)} races")
    
    # Process with enhanced analysis
    # Limit to first 4-5 races to keep analysis time reasonable
    max_races = int(os.getenv('MAX_RACES', '5'))
    races_to_process = races[:max_races]
    
    print(f"Processing first {len(races_to_process)} races (max_races={max_races})")
    
    analyzer = EnhancedAnalyzer()
    
    all_selections = []
    for i, race in enumerate(races_to_process, 1):
        print(f"\n[{i}/{len(races_to_process)}] Processing: {race.get('market_name', 'Unknown')}")
        
        try:
            selections = analyzer.analyze_race_enhanced(race)
            all_selections.extend(selections)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            continue
    
    # Rank all selections by confidence and take top 5
    all_selections.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    top_selections = all_selections[:5]
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(all_selections)} selections generated")
    print(f"Ranking by confidence...")
    print(f"[OK] Selected top 5 picks:")
    for i, sel in enumerate(top_selections, 1):
        print(f"  {i}. {sel.get('runner_name', 'Unknown')} @ {sel.get('venue', 'Unknown')} (p_win: {sel.get('p_win', 0):.2f})")
    
    # Save to history folder
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join('history', f'selections_{timestamp}.csv')
    
    # Ensure history directory exists
    os.makedirs('history', exist_ok=True)
    
    save_selections_csv(top_selections, output_path)
    
    # Also save as today_picks.csv for compatibility
    save_selections_csv(top_selections, 'today_picks.csv')
    
    print(f"\n{'='*60}")
    print("SUMMARY: 5 selections generated")
    print(f"Output: {output_path}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
