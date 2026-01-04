#!/usr/bin/env python3
"""
save_selections_to_dynamodb.py - Save daily selections to SureBetBets table
Integrates the learning workflow outputs with your existing database/frontend
"""

import os
import sys
import json
import argparse
from datetime import datetime
from decimal import Decimal
import pandas as pd

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

def convert_floats(obj):
    """Convert float values to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats(item) for item in obj]
    return obj

def load_market_odds(snapshot_path: str = 'response_live.json') -> dict:
    """Load actual market odds from Betfair snapshot"""
    odds_map = {}  # {selection_id: odds}
    
    if not os.path.exists(snapshot_path):
        print(f"WARNING: Snapshot file not found: {snapshot_path}")
        return odds_map
    
    try:
        with open(snapshot_path, 'r') as f:
            data = json.load(f)
        
        for race in data.get('races', []):
            for runner in race.get('runners', []):
                selection_id = str(runner.get('selectionId', ''))
                odds = runner.get('odds', None)
                if selection_id and odds:
                    odds_map[selection_id] = float(odds)
    except Exception as e:
        print(f"WARNING: Failed to load market odds: {e}")
    
    return odds_map

def load_market_odds(snapshot_path: str = 'response_live.json') -> dict:
    """Load actual market odds from Betfair snapshot"""
    odds_map = {}  # {selection_id: odds}
    
    if not os.path.exists(snapshot_path):
        print(f"WARNING: Snapshot file not found: {snapshot_path}")
        return odds_map
    
    try:
        with open(snapshot_path, 'r') as f:
            data = json.load(f)
        
        for race in data.get('races', []):
            for runner in race.get('runners', []):
                selection_id = str(runner.get('selectionId', ''))
                odds = runner.get('odds', None)
                if selection_id and odds:
                    odds_map[selection_id] = float(odds)
    except Exception as e:
        print(f"WARNING: Failed to load market odds: {e}")
    
    return odds_map

def load_selections(csv_path: str) -> pd.DataFrame:
    """Load selections CSV"""
    if not os.path.exists(csv_path):
        print(f"ERROR: Selections file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def format_bet_for_dynamodb(row: pd.Series, market_odds: dict = None) -> dict:
    """Convert CSV row to DynamoDB bet item"""
    
    if market_odds is None:
        market_odds = {}
    
    # Extract key fields
    horse = str(row.get('runner_name', 'Unknown'))
    venue = str(row.get('venue', 'Unknown'))
    race_time = str(row.get('start_time_dublin', ''))
    market_id = str(row.get('market_id', ''))
    selection_id = str(row.get('selection_id', ''))
    
    # Generate bet_id
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    bet_id = f"{race_time}_{venue}_{horse}".replace(" ", "_").replace(":", "")
    if not bet_id or bet_id == "__":
        bet_id = f"bet_{timestamp_slug}_{selection_id}"
    
    # Parse probabilities and EVs
    p_win = float(row.get('p_win', 0))
    p_place = float(row.get('p_place', 0))
    
    # Get actual market odds from snapshot, fall back to implied odds
    market_odds_value = market_odds.get(selection_id)
    if market_odds_value:
        implied_odds = market_odds_value
    else:
        # Fall back to implied odds from probability
        implied_odds = (1 / p_win) if p_win > 0 else 0
        print(f"  WARNING: No market odds found for {horse} (ID: {selection_id}), using implied odds {implied_odds:.2f}")
    
    # Parse EW terms
    ew_places = int(row.get('ew_places', 0)) if pd.notna(row.get('ew_places')) else 0
    ew_fraction = float(row.get('ew_fraction', 0)) if pd.notna(row.get('ew_fraction')) else 0
    
    # Determine bet type - use CSV value if present, otherwise infer from EW terms
    bet_type = row.get('bet_type', '').strip().upper() if pd.notna(row.get('bet_type')) else ''
    if not bet_type:
        # Fallback: infer from EW terms
        bet_type = "EW" if ew_places > 0 and ew_fraction > 0 else "WIN"
    
    # Extract tags and rationale
    tags = str(row.get('tags', '')).split(',') if pd.notna(row.get('tags')) else []
    tags = [t.strip() for t in tags if t.strip()]
    why_now = str(row.get('why_now', 'Value identified'))
    
    # Calculate Expected Value (EV) properly for WIN vs EW bets
    if bet_type == 'WIN':
        ev = (implied_odds * p_win) - 1 if p_win > 0 else 0
    else:  # EW bet
        # Split stake 50/50 between win and place
        # If horse wins: you get both win return AND place return
        # If horse places (but doesn't win): you get only place return
        # If horse loses: you get nothing
        
        place_odds = 1 + ((implied_odds - 1) * ew_fraction)
        
        # If horse wins (probability p_win): get full win return + place return
        win_scenario_return = (0.5 * implied_odds) + (0.5 * place_odds)
        
        # If horse places but doesn't win (probability p_place - p_win): get only place return
        place_only_prob = max(0, p_place - p_win)
        place_scenario_return = 0.5 * place_odds
        
        # Expected return
        total_return = (p_win * win_scenario_return) + (place_only_prob * place_scenario_return)
        ev = total_return - 1  # Subtract the full stake
    
    # Calculate Decision Rating (combined score for easy decision making)
    roi_pct = ev * 100
    confidence_score = int(p_win * 100) if p_win > 0 else 50
    
    # Scoring system (0-100 scale):
    # - ROI weight: 40% (normalized to 0-40, capped at 50% ROI = max score)
    # - EV weight: 30% (normalized to 0-30, capped at €10 EV = max score)
    # - Confidence weight: 20% (normalized to 0-20)
    # - Place probability weight: 10% (for EW bets)
    
    roi_score = min(40, (roi_pct / 50) * 40) if roi_pct > 0 else 0
    ev_score = min(30, (ev / 10) * 30) if ev > 0 else 0
    confidence_weight = (confidence_score / 100) * 20
    place_weight = (p_place * 10) if bet_type == 'EW' else (p_win * 10)
    
    decision_score = roi_score + ev_score + confidence_weight + place_weight
    
    # Map to categories
    if decision_score >= 70:
        decision_rating = "DO IT"
        rating_color = "green"
    elif decision_score >= 45:
        decision_rating = "RISKY"
        rating_color = "orange"
    else:
        decision_rating = "NOT GREAT"
        rating_color = "red"
    
    # Build bet item matching your Lambda schema
    bet_item = {
        'bet_id': bet_id,
        'timestamp': datetime.utcnow().isoformat(),
        'date': datetime.utcnow().strftime("%Y-%m-%d"),
        
        # Core bet info
        'race_time': race_time,
        'course': venue,
        'horse': horse,
        'bet_type': bet_type,
        'market_id': market_id,
        'selection_id': selection_id,
        
        # Probabilities and odds
        'odds': implied_odds,
        'p_win': p_win,
        'p_place': p_place,
        
        # EW terms
        'ew_places': ew_places,
        'ew_fraction': ew_fraction,
        
        # Analysis
        'why_now': why_now,
        'tags': tags,
        'confidence': confidence_score,
        'roi': roi_pct,  # ROI as percentage
        'recommendation': 'BACK' if bet_type == 'WIN' else 'EW',
        
        # Decision Rating (NEW - combined metric)
        'decision_rating': decision_rating,  # "DO IT", "RISKY", or "NOT GREAT"
        'decision_score': round(decision_score, 1),  # 0-100 numerical score
        'rating_color': rating_color,  # For UI display
        
        # Source tracking
        'source': 'learning_workflow',
        'prompt_version': 'prompt.txt',
        
        # Audit fields
        'audit': {
            'created_by': 'learning_workflow',
            'created_at': datetime.utcnow().isoformat(),
            'status': 'pending_outcome'
        },
        
        # Learning fields (updated after race)
        'outcome': None,
        'actual_position': None,
        'learning_notes': None,
        'feedback_processed': False,
        
        # Full bet object for reference
        'bet': {
            'race_time': race_time,
            'course': venue,
            'horse': horse,
            'bet_type': bet_type,
            'odds': implied_odds,
            'p_win': p_win,
            'p_place': p_place,
            'why_now': why_now,
            'tags': tags
        }
    }
    
    return bet_item

def save_to_dynamodb(bets: list[dict], table_name: str = None, region: str = 'us-east-1') -> tuple[int, int]:
    """Save bet items to DynamoDB"""
    
    if not HAS_BOTO3:
        print("ERROR: boto3 not installed. Run: pip install boto3", file=sys.stderr)
        sys.exit(1)
    
    table_name = table_name or os.environ.get("SUREBET_DDB_TABLE", "SureBetBets")
    
    print(f"Connecting to DynamoDB table: {table_name} (region: {region})")
    
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)
        
        success_count = 0
        error_count = 0
        
        for bet in bets:
            try:
                # Convert floats to Decimals
                bet_converted = convert_floats(bet)
                
                # Put item
                table.put_item(Item=bet_converted)
                
                success_count += 1
                print(f"[OK] Saved: {bet['horse']} at {bet['course']} ({bet['bet_type']})")
                
            except Exception as e:
                error_count += 1
                print(f"[ERROR] Failed to save {bet.get('horse', 'unknown')}: {e}", file=sys.stderr)
        
        return success_count, error_count
        
    except Exception as e:
        print(f"ERROR connecting to DynamoDB: {e}", file=sys.stderr)
        sys.exit(1)

def save_to_json_backup(bets: list[dict], output_path: str):
    """Save to local JSON as backup"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Convert Decimals back to floats for JSON
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decimal_to_float(item) for item in obj]
        return obj
    
    bets_json = decimal_to_float(bets)
    
    with open(output_path, 'w') as f:
        json.dump(bets_json, f, indent=2)
    
    print(f"[OK] Backup saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Save selections to DynamoDB SureBetBets table")
    parser.add_argument("--selections", type=str, required=True, help="Path to selections CSV")
    parser.add_argument("--table", type=str, default="", help="DynamoDB table name (default: SureBetBets)")
    parser.add_argument("--region", type=str, default="us-east-1", help="AWS region")
    parser.add_argument("--backup", type=str, default="", help="JSON backup path (optional)")
    parser.add_argument("--dry_run", action="store_true", help="Don't actually save to DynamoDB")
    
    args = parser.parse_args()
    
    print(f"{'='*60}")
    print("Save Selections to DynamoDB")
    print(f"{'='*60}")
    
    # Load selections
    print(f"\nLoading selections from: {args.selections}")
    df = load_selections(args.selections)
    print(f"Found {len(df)} selections")
    
    if df.empty:
        print("No selections to save")
        return
    
    # Load market odds from snapshot
    print("\nLoading market odds from snapshot...")
    market_odds = load_market_odds()
    print(f"Loaded odds for {len(market_odds)} runners")
    
    # Convert to bet items
    print("\nFormatting for DynamoDB...")
    bets = []
    for idx, row in df.iterrows():
        try:
            bet_item = format_bet_for_dynamodb(row, market_odds)
            bets.append(bet_item)
        except Exception as e:
            print(f"⚠️  Warning: Failed to format row {idx}: {e}")
    
    print(f"Formatted {len(bets)} bet items")
    
    # Save to DynamoDB
    if not args.dry_run:
        print(f"\nSaving to DynamoDB...")
        success, errors = save_to_dynamodb(bets, args.table, args.region)
        
        print(f"\n{'='*60}")
        print(f"Results: {success} saved, {errors} errors")
        print(f"{'='*60}")
    else:
        print("\n🔍 DRY RUN - Would save these bets:")
        for bet in bets:
            print(f"  - {bet['horse']} at {bet['course']} ({bet['bet_type']}) - p_win: {bet['p_win']:.1%}")
        print("\nRun without --dry_run to actually save to DynamoDB")
    
    # Save backup if requested
    if args.backup:
        save_to_json_backup(bets, args.backup)
    
    print("\n[OK] Complete")

if __name__ == "__main__":
    main()
