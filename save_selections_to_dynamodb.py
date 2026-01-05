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

def calculate_combined_confidence(row: pd.Series) -> tuple:
    """
    Calculate Combined Confidence Rating (0-100)
    Consolidates multiple confidence signals into one unified metric
    
    Components:
    1. Win Probability (40%) - Core prediction strength
    2. Place Probability (20%) - Backup safety measure
    3. Value Edge (20%) - How much better than market odds
    4. Consistency Score (20%) - Internal signal agreement
    
    Returns: (combined_confidence, confidence_grade, confidence_explanation)
    """
    # Extract raw signals
    p_win = float(row.get('p_win', 0))
    p_place = float(row.get('p_place', 0))
    odds = float(row.get('odds', 0))
    
    # Optional signals if available
    research_confidence = float(row.get('confidence', 0)) / 100 if 'confidence' in row else None
    
    # 1. WIN PROBABILITY COMPONENT (40% weight)
    # Direct measure of how likely we think the horse will win
    win_component = p_win * 40
    
    # 2. PLACE PROBABILITY COMPONENT (20% weight)
    # Safety net - even if doesn't win, likely to place
    place_component = p_place * 20
    
    # 3. VALUE EDGE COMPONENT (20% weight)
    # How much better is our probability vs market implied probability
    if odds > 1:
        market_implied_prob = 1 / odds
        edge = p_win - market_implied_prob
        # Normalize edge: 15%+ edge = full 20 points
        edge_component = min(20, (edge / 0.15) * 20) if edge > 0 else 0
    else:
        edge_component = 0
    
    # 4. CONSISTENCY SCORE COMPONENT (20% weight)
    # How well do our different signals agree?
    signals = [p_win]
    if p_place > 0:
        # For consistency, place should be higher than win (logical check)
        place_consistency = 1.0 if p_place >= p_win else (p_place / p_win)
        signals.append(place_consistency)
    
    if research_confidence is not None:
        # Research confidence should align with p_win
        research_alignment = 1.0 - abs(p_win - research_confidence)
        signals.append(research_alignment)
    
    # Calculate consistency as variance from mean
    if len(signals) > 1:
        mean_signal = sum(signals) / len(signals)
        variance = sum((s - mean_signal) ** 2 for s in signals) / len(signals)
        # Low variance = high consistency
        consistency_score = max(0, 1 - (variance * 5))  # Scale variance
    else:
        consistency_score = 0.7  # Default moderate consistency
    
    consistency_component = consistency_score * 20
    
    # TOTAL COMBINED CONFIDENCE
    combined_confidence = win_component + place_component + edge_component + consistency_component
    combined_confidence = max(0, min(100, combined_confidence))  # Clamp to 0-100
    
    # Grade the confidence
    if combined_confidence >= 70:
        confidence_grade = "VERY HIGH"
        grade_color = "green"
        explanation = "Multiple strong signals align - high conviction bet"
    elif combined_confidence >= 50:
        confidence_grade = "HIGH"
        grade_color = "lightgreen"
        explanation = "Good signals with reasonable consistency"
    elif combined_confidence >= 35:
        confidence_grade = "MODERATE"
        grade_color = "orange"
        explanation = "Mixed signals - proceed with caution"
    else:
        confidence_grade = "LOW"
        grade_color = "red"
        explanation = "Weak or conflicting signals - avoid or minimal stake"
    
    # Detailed breakdown for transparency
    breakdown = {
        'win_component': round(win_component, 1),
        'place_component': round(place_component, 1),
        'edge_component': round(edge_component, 1),
        'consistency_component': round(consistency_component, 1),
        'raw_signals': {
            'p_win': p_win,
            'p_place': p_place,
            'market_edge': edge if odds > 1 else 0,
            'consistency_score': round(consistency_score, 2)
        }
    }
    
    return (round(combined_confidence, 1), confidence_grade, grade_color, explanation, breakdown)


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
    
    # Calculate Combined Confidence Rating (NEW - unified confidence metric)
    combined_conf, conf_grade, conf_color, conf_explanation, conf_breakdown = calculate_combined_confidence(row)
    
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
        
        # Decision Rating (bet quality indicator)
        'decision_rating': decision_rating,  # "DO IT", "RISKY", or "NOT GREAT"
        'decision_score': round(decision_score, 1),  # 0-100 numerical score
        'rating_color': rating_color,  # For UI display
        
        # Combined Confidence Rating (NEW - unified confidence metric)
        'combined_confidence': combined_conf,  # 0-100 consolidated confidence
        'confidence_grade': conf_grade,  # "VERY HIGH", "HIGH", "MODERATE", "LOW"
        'confidence_color': conf_color,  # For UI display
        'confidence_explanation': conf_explanation,  # Human-readable reason
        'confidence_breakdown': conf_breakdown,  # Detailed component scores
        
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
    parser.add_argument("--min_roi", type=float, default=0.0, help="Minimum ROI threshold in percentage (default: 0.0 - breakeven)")
    
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
    print(f"\nFormatting for DynamoDB (minimum ROI: {args.min_roi}%)...")
    bets = []
    filtered_out = 0
    for idx, row in df.iterrows():
        try:
            bet_item = format_bet_for_dynamodb(row, market_odds)
            
            # Filter by minimum ROI threshold
            roi = float(bet_item.get('roi', 0))
            if roi < args.min_roi:
                filtered_out += 1
                horse = bet_item.get('horse', 'Unknown')
                print(f"⛔ FILTERED: {horse} (ROI: {roi:.1f}% < {args.min_roi}% minimum)")
                continue
            
            bets.append(bet_item)
        except Exception as e:
            print(f"⚠️  Warning: Failed to format row {idx}: {e}")
    
    print(f"\nFormatted {len(bets)} bet items (filtered out {filtered_out} low ROI bets)")
    
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
