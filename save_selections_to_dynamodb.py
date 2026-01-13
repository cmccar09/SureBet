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
import requests

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

def get_betfair_session():
    """Get Betfair session credentials"""
    try:
        with open('./betfair-creds.json', 'r') as f:
            creds = json.load(f)
        return creds.get('session_token'), creds.get('app_key')
    except Exception as e:
        print(f"WARNING: Could not load Betfair credentials: {e}")
        return None, None

def filter_non_runners(bets: list, session_token: str = None, app_key: str = None) -> tuple:
    """
    Filter out non-runners (REMOVED status) from Betfair
    Returns: (filtered_bets, removed_count)
    """
    if not session_token or not app_key:
        print("Skipping non-runner check (no Betfair credentials)")
        return bets, 0
    
    filtered_bets = []
    removed_count = 0
    
    # Group by market to minimize API calls
    from collections import defaultdict
    by_market = defaultdict(list)
    for bet in bets:
        market_id = bet.get('market_id')
        if market_id:
            by_market[market_id].append(bet)
        else:
            # No market_id, keep it
            filtered_bets.append(bet)
    
    # Check each market
    for market_id, market_bets in by_market.items():
        try:
            url = 'https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/'
            headers = {
                'X-Application': app_key,
                'X-Authentication': session_token,
                'Content-Type': 'application/json'
            }
            payload = {
                'marketIds': [market_id],
                'priceProjection': {'priceData': ['EX_BEST_OFFERS']}
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                markets = response.json()
                if markets and len(markets) > 0:
                    runner_statuses = {}
                    for runner in markets[0].get('runners', []):
                        runner_statuses[str(runner.get('selectionId'))] = runner.get('status', 'ACTIVE')
                    
                    # Filter bets based on status
                    for bet in market_bets:
                        selection_id = str(bet.get('selection_id', ''))
                        status = runner_statuses.get(selection_id, 'ACTIVE')
                        
                        if status == 'REMOVED':
                            removed_count += 1
                            print(f"  NON-RUNNER: {bet.get('horse', 'Unknown')} - REMOVED from market")
                        else:
                            filtered_bets.append(bet)
                else:
                    filtered_bets.extend(market_bets)
            else:
                filtered_bets.extend(market_bets)
        except Exception as e:
            print(f"WARNING: Failed to check market {market_id}: {e}")
            filtered_bets.extend(market_bets)
    
    return filtered_bets, removed_count

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

def calculate_combined_confidence(row: pd.Series, race_type: str = 'horse') -> tuple:
    """
    Calculate Combined Confidence Rating (0-100)
    Consolidates multiple confidence signals into one unified metric
    
    Components:
    1. Win Probability (40%) - Core prediction strength
    2. Place Probability (20%) - Backup safety measure
    3. Value Edge (20%) - How much better than market odds
    4. Consistency Score (20%) - Internal signal agreement
    
    IMPROVED RULES (Based on Winner Analysis):
    - Greyhounds without enrichment data: Max 50% combined confidence
    - Missing external validation heavily penalized
    
    Returns: (combined_confidence, confidence_grade, confidence_explanation)
    """
    # Extract raw signals
    p_win = float(row.get('p_win', 0))
    p_place = float(row.get('p_place', 0))
    odds = float(row.get('odds', 0))
    
    # Optional signals if available
    research_confidence = float(row.get('confidence', 0)) / 100 if 'confidence' in row else None
    has_enrichment = bool(row.get('enrichment_data')) or bool(row.get('has_form_data'))
    
    # 1. WIN PROBABILITY COMPONENT (40% weight)
    # Direct measure of how likely we think the horse will win
    win_component = p_win * 40
    
    # PENALTY: Greyhounds without enrichment data
    if race_type == 'greyhound' and not has_enrichment:
        # Reduce win component by 50% if no external data
        win_component = win_component * 0.5
    
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
    if combined_confidence >= 60:
        confidence_grade = "EXCELLENT"
        grade_color = "green"
        explanation = "Strong conviction bet - multiple signals align"
    elif combined_confidence >= 40:
        confidence_grade = "GOOD"
        grade_color = "#FFB84D"  # Light amber
        explanation = "Solid bet - good value with reasonable confidence"
    elif combined_confidence >= 25:
        confidence_grade = "FAIR"
        grade_color = "#FF8C00"  # Dark amber
        explanation = "Acceptable bet - proceed with caution"
    else:
        confidence_grade = "POOR"
        grade_color = "red"
        explanation = "Weak signals - minimal stake or avoid"
    
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


def format_bet_for_dynamodb(row: pd.Series, market_odds: dict = None, sport: str = 'horses') -> dict:
    """Convert CSV row to DynamoDB bet item
    
    Args:
        row: DataFrame row with selection data
        market_odds: Dictionary of odds by selection_id
        sport: 'horses' or 'greyhounds' (default: horses)
    """
    
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
    combined_conf, conf_grade, conf_color, conf_explanation, conf_breakdown = calculate_combined_confidence(row, race_type=sport)
    
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
        'bet_date': datetime.utcnow().strftime("%Y-%m-%d"),  # Primary key
        'timestamp': datetime.utcnow().isoformat(),
        'date': datetime.utcnow().strftime("%Y-%m-%d"),
        
        # Core bet info
        'race_time': race_time,
        'course': venue,
        'horse': horse,  # For horses
        'dog': horse if sport == 'greyhounds' else None,  # For greyhounds (same field)
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
        'sport': sport,  # 'horses' or 'greyhounds'
        
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

def deduplicate_against_database(new_bets: list, table_name: str = None, region: str = 'eu-west-1') -> tuple:
    """
    Check for existing picks in database and apply deduplication logic
    across both existing and new picks for the same race.
    
    Returns: (filtered_new_bets, bet_ids_to_delete, stats_dict)
    """
    from collections import defaultdict
    
    if not HAS_BOTO3:
        return new_bets, [], {}
    
    table_name = table_name or os.environ.get("SUREBET_DDB_TABLE", "SureBetBets")
    
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Scan for existing picks from today
        response = table.scan(
            FilterExpression='begins_with(bet_date, :d)',
            ExpressionAttributeValues={':d': today}
        )
        existing_picks = response.get('Items', [])
        
        print(f"\nFound {len(existing_picks)} existing picks from today in database")
        
        # Group existing picks by race
        existing_by_race = defaultdict(list)
        for pick in existing_picks:
            race_time = pick.get('race_time', '')
            normalized_time = race_time.replace('.000Z', '').replace('Z', '').split('+')[0].split('.')[0]
            race_key = f"{pick.get('course', 'Unknown')}_{normalized_time}"
            
            # Convert Decimal to float for consistent comparison
            pick_dict = {
                'horse': pick.get('horse'),
                'course': pick.get('course'),
                'race_time': pick.get('race_time'),
                'bet_type': pick.get('bet_type', 'WIN'),
                'decision_score': float(pick.get('decision_score', 0)),
                'bet_id': pick.get('bet_id'),
                'is_existing': True
            }
            existing_by_race[race_key].append(pick_dict)
        
        # Group new bets by race
        new_by_race = defaultdict(list)
        for bet in new_bets:
            race_time = bet.get('race_time', '')
            normalized_time = race_time.replace('.000Z', '').replace('Z', '').split('+')[0].split('.')[0]
            race_key = f"{bet.get('course', 'Unknown')}_{normalized_time}"
            
            bet_dict = bet.copy()
            bet_dict['is_existing'] = False
            new_by_race[race_key].append(bet_dict)
        
        # Find races that have conflicts (both existing and new picks)
        conflicting_races = set(existing_by_race.keys()) & set(new_by_race.keys())
        
        if not conflicting_races:
            print("No race conflicts with existing database picks")
            return new_bets, [], {}
        
        print(f"\nFound {len(conflicting_races)} races with potential conflicts:")
        
        bet_ids_to_delete = []
        filtered_new_bets = []
        stats = {
            'races_checked': len(conflicting_races),
            'new_picks_kept': 0,
            'new_picks_filtered': 0,
            'existing_picks_kept': 0,
            'existing_picks_deleted': 0
        }
        
        # Process each conflicting race
        for race_key in conflicting_races:
            all_picks = existing_by_race[race_key] + new_by_race[race_key]
            
            # Apply same filtering logic as filter_picks_per_race
            if len(all_picks) <= 2:
                if len(all_picks) == 2:
                    bet_types = [pick['bet_type'] for pick in all_picks]
                    
                    if bet_types[0] == bet_types[1]:
                        # Both same type - keep only higher scoring one
                        sorted_picks = sorted(all_picks, key=lambda x: x['decision_score'], reverse=True)
                        kept_pick = sorted_picks[0]
                        removed_pick = sorted_picks[1]
                        
                        venue = all_picks[0]['course']
                        print(f"  {venue}: Both {bet_types[0]} - keeping {kept_pick['horse']} (score: {kept_pick['decision_score']:.1f})")
                        
                        if kept_pick['is_existing']:
                            stats['existing_picks_kept'] += 1
                        else:
                            stats['new_picks_kept'] += 1
                        
                        if removed_pick['is_existing']:
                            bet_ids_to_delete.append(removed_pick['bet_id'])
                            stats['existing_picks_deleted'] += 1
                            print(f"    DELETE existing: {removed_pick['horse']}")
                        else:
                            stats['new_picks_filtered'] += 1
                            print(f"    FILTER new: {removed_pick['horse']}")
                    else:
                        # Different types - keep both
                        stats['existing_picks_kept'] += sum(1 for p in all_picks if p['is_existing'])
                        stats['new_picks_kept'] += sum(1 for p in all_picks if not p['is_existing'])
                else:
                    # Only 1 pick - keep it
                    if all_picks[0]['is_existing']:
                        stats['existing_picks_kept'] += 1
                    else:
                        stats['new_picks_kept'] += 1
            else:
                # More than 2 picks - keep top 2 with different types
                sorted_picks = sorted(all_picks, key=lambda x: x['decision_score'], reverse=True)
                top_two = sorted_picks[:2]
                bet_types = [pick['bet_type'] for pick in top_two]
                
                venue = all_picks[0]['course']
                print(f"  {venue}: {len(all_picks)} picks - applying 2-pick limit")
                
                if bet_types[0] != bet_types[1]:
                    # Different types - keep top 2
                    kept_picks = top_two
                else:
                    # Both same type - keep highest + find different type
                    kept_picks = [top_two[0]]
                    different_type = next(
                        (p for p in sorted_picks[1:] if p['bet_type'] != bet_types[0]),
                        None
                    )
                    if different_type:
                        kept_picks.append(different_type)
                
                # Mark picks for keeping/deletion
                for pick in all_picks:
                    if pick in kept_picks:
                        if pick['is_existing']:
                            stats['existing_picks_kept'] += 1
                        else:
                            stats['new_picks_kept'] += 1
                            print(f"    KEEP new: {pick['horse']} ({pick['bet_type']})")
                    else:
                        if pick['is_existing']:
                            bet_ids_to_delete.append(pick['bet_id'])
                            stats['existing_picks_deleted'] += 1
                            print(f"    DELETE existing: {pick['horse']} ({pick['bet_type']})")
                        else:
                            stats['new_picks_filtered'] += 1
                            print(f"    FILTER new: {pick['horse']} ({pick['bet_type']})")
        
        # Filter new_bets to only include those we want to keep
        # For non-conflicting races, keep all new picks
        for race_key in set(new_by_race.keys()) - conflicting_races:
            filtered_new_bets.extend([bet for bet in new_bets if f"{bet.get('course', 'Unknown')}_{bet.get('race_time', '').replace('.000Z', '').replace('Z', '').split('+')[0].split('.')[0]}" == race_key])
        
        # For conflicting races, only keep new picks that weren't filtered
        for race_key in conflicting_races:
            all_picks = existing_by_race[race_key] + new_by_race[race_key]
            
            # Re-apply filtering logic to determine which new picks to keep
            if len(all_picks) <= 2:
                if len(all_picks) == 2:
                    bet_types = [pick['bet_type'] for pick in all_picks]
                    if bet_types[0] == bet_types[1]:
                        sorted_picks = sorted(all_picks, key=lambda x: x['decision_score'], reverse=True)
                        kept_pick = sorted_picks[0]
                        if not kept_pick['is_existing']:
                            # Find original bet object
                            original_bet = next((bet for bet in new_bets if bet.get('horse') == kept_pick['horse'] and bet.get('course') == kept_pick['course']), None)
                            if original_bet:
                                filtered_new_bets.append(original_bet)
                    else:
                        # Keep all new picks (different types)
                        for pick in all_picks:
                            if not pick['is_existing']:
                                original_bet = next((bet for bet in new_bets if bet.get('horse') == pick['horse'] and bet.get('course') == pick['course']), None)
                                if original_bet:
                                    filtered_new_bets.append(original_bet)
                else:
                    # Only 1 pick - keep if it's new
                    if not all_picks[0]['is_existing']:
                        original_bet = next((bet for bet in new_bets if bet.get('horse') == all_picks[0]['horse'] and bet.get('course') == all_picks[0]['course']), None)
                        if original_bet:
                            filtered_new_bets.append(original_bet)
            else:
                # More than 2 picks - complex logic
                sorted_picks = sorted(all_picks, key=lambda x: x['decision_score'], reverse=True)
                top_two = sorted_picks[:2]
                bet_types = [pick['bet_type'] for pick in top_two]
                
                kept_picks = top_two if bet_types[0] != bet_types[1] else [top_two[0]]
                if bet_types[0] == bet_types[1]:
                    different_type = next((p for p in sorted_picks[1:] if p['bet_type'] != bet_types[0]), None)
                    if different_type:
                        kept_picks.append(different_type)
                
                for pick in kept_picks:
                    if not pick['is_existing']:
                        original_bet = next((bet for bet in new_bets if bet.get('horse') == pick['horse'] and bet.get('course') == pick['course']), None)
                        if original_bet:
                            filtered_new_bets.append(original_bet)
        
        print(f"\nDeduplication summary:")
        print(f"  New picks to save: {stats['new_picks_kept']}")
        print(f"  New picks filtered: {stats['new_picks_filtered']}")
        print(f"  Existing picks to delete: {stats['existing_picks_deleted']}")
        print(f"  Existing picks kept: {stats['existing_picks_kept']}")
        
        return filtered_new_bets, bet_ids_to_delete, stats
        
    except Exception as e:
        print(f"WARNING: Database deduplication failed: {e}")
        print("Proceeding with standard filtering only...")
        return new_bets, [], {}

def save_to_dynamodb(bets: list[dict], table_name: str = None, region: str = 'eu-west-1', bet_ids_to_delete: list = None) -> tuple[int, int]:
    """Save bet items to DynamoDB and optionally delete old bet_ids"""
    
    if not HAS_BOTO3:
        print("ERROR: boto3 not installed. Run: pip install boto3", file=sys.stderr)
        sys.exit(1)
    
    table_name = table_name or os.environ.get("SUREBET_DDB_TABLE", "SureBetBets")
    
    print(f"Connecting to DynamoDB table: {table_name} (region: {region})")
    
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)
        
        # Delete old picks first
        if bet_ids_to_delete:
            print(f"\nDeleting {len(bet_ids_to_delete)} superseded picks...")
            deleted_count = 0
            for bet_id in bet_ids_to_delete:
                try:
                    table.delete_item(Key={'bet_id': bet_id})
                    deleted_count += 1
                    print(f"  [DELETED] {bet_id}")
                except Exception as e:
                    print(f"  [ERROR] Failed to delete {bet_id}: {e}")
            print(f"Deleted {deleted_count} old picks\n")
        
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

def filter_picks_per_race(bets: list) -> tuple:
    """
    Filter picks to enforce race-level rules:
    - Maximum 2 picks per race
    - If 2 picks for same race, one must be WIN and one must be EW
    
    Returns: (filtered_bets, removed_count)
    """
    from collections import defaultdict
    
    # Group bets by race
    races = defaultdict(list)
    for bet in bets:
        # Normalize race_time by removing timezone suffix and milliseconds for grouping
        race_time = bet.get('race_time', '')
        # Remove .000Z, Z, +00:00 etc to normalize times
        normalized_time = race_time.replace('.000Z', '').replace('Z', '').split('+')[0].split('.')[0]
        
        # Create race key from course + normalized race_time
        race_key = f"{bet.get('course', 'Unknown')}_{normalized_time}"
        races[race_key].append(bet)
    
    filtered_bets = []
    removed_count = 0
    
    for race_key, race_bets in races.items():
        if len(race_bets) <= 2:
            # Check if we have 2 picks with same bet type
            if len(race_bets) == 2:
                bet_types = [bet.get('bet_type', 'WIN') for bet in race_bets]
                
                # If both are same type, keep only the higher decision_score one
                if bet_types[0] == bet_types[1]:
                    # Sort by decision_score descending
                    sorted_bets = sorted(race_bets, key=lambda x: float(x.get('decision_score', 0)), reverse=True)
                    filtered_bets.append(sorted_bets[0])
                    removed_count += 1
                    print(f"  REMOVED: {sorted_bets[1]['horse']} - duplicate {bet_types[0]} type (kept higher scoring pick)")
                else:
                    # Different types (WIN and EW) - keep both
                    filtered_bets.extend(race_bets)
            else:
                # Only 1 pick for this race - keep it
                filtered_bets.extend(race_bets)
        else:
            # More than 2 picks for this race
            # Sort by decision_score and keep top 2
            sorted_bets = sorted(race_bets, key=lambda x: float(x.get('decision_score', 0)), reverse=True)
            
            # Check if top 2 have different bet types
            top_two = sorted_bets[:2]
            bet_types = [bet.get('bet_type', 'WIN') for bet in top_two]
            
            if bet_types[0] != bet_types[1]:
                # Different types - perfect, keep both
                filtered_bets.extend(top_two)
                removed_count += len(sorted_bets) - 2
                for removed_bet in sorted_bets[2:]:
                    print(f"  REMOVED: {removed_bet['horse']} - exceeded 2 picks per race limit")
            else:
                # Both same type - need to find one with different type
                kept_bets = [top_two[0]]  # Keep highest scoring
                
                # Look for best pick with different type
                different_type_bet = None
                for bet in sorted_bets[1:]:
                    if bet.get('bet_type', 'WIN') != bet_types[0]:
                        different_type_bet = bet
                        break
                
                if different_type_bet:
                    kept_bets.append(different_type_bet)
                    print(f"  KEPT: {kept_bets[0]['horse']} ({bet_types[0]}) + {different_type_bet['horse']} ({different_type_bet.get('bet_type')})")
                else:
                    # No different type available, just keep the top one
                    print(f"  KEPT: Only {kept_bets[0]['horse']} ({bet_types[0]}) - no different bet type available")
                
                filtered_bets.extend(kept_bets)
                removed_count += len(sorted_bets) - len(kept_bets)
                
                for removed_bet in sorted_bets:
                    if removed_bet not in kept_bets:
                        print(f"  REMOVED: {removed_bet['horse']} - race limit + bet type rules")
    
    return filtered_bets, removed_count

def main():
    parser = argparse.ArgumentParser(description="Save selections to DynamoDB SureBetBets table")
    parser.add_argument("--selections", type=str, required=True, help="Path to selections CSV")
    parser.add_argument("--table", type=str, default="", help="DynamoDB table name (default: SureBetBets)")
    parser.add_argument("--region", type=str, default="us-east-1", help="AWS region")
    parser.add_argument("--backup", type=str, default="", help="JSON backup path (optional)")
    parser.add_argument("--dry_run", action="store_true", help="Don't actually save to DynamoDB")
    parser.add_argument("--min_roi", type=float, default=0.0, help="Minimum ROI threshold in percentage (default: 0.0 - breakeven)")
    parser.add_argument("--sport", type=str, choices=['horses', 'greyhounds'], default='horses', help="Sport type: horses or greyhounds (default: horses)")
    
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
    # Auto-detect sport per-pick based on venue (for mixed horse/greyhound selections)
    greyhound_venues = ['Monmore', 'Central Park', 'Perry Barr', 'Romford', 'Crayford', 'Belle Vue', 
                        'Sheffield', 'Newcastle (Greyhounds)', 'Sunderland', 'Harlow', 'Henlow', 'Oxford']
    
    print(f"\nFormatting for DynamoDB (minimum ROI: {args.min_roi}%)...")
    bets = []
    filtered_out = 0
    for idx, row in df.iterrows():
        try:
            # Auto-detect sport from venue
            venue = row.get('venue', '')
            detected_sport = 'greyhounds' if venue in greyhound_venues else 'horses'
            
            bet_item = format_bet_for_dynamodb(row, market_odds, detected_sport)
            
            # Filter by minimum ROI threshold
            roi = float(bet_item.get('roi', 0))
            if roi < args.min_roi:
                filtered_out += 1
                horse = bet_item.get('horse', 'Unknown')
                print(f"FILTERED: {horse} (ROI: {roi:.1f}% < {args.min_roi}% minimum)")
                continue
            
            bets.append(bet_item)
        except Exception as e:
            print(f"WARNING: Failed to format row {idx}: {e}")
    
    print(f"\nFormatted {len(bets)} bet items (filtered out {filtered_out} low ROI bets)")
    
    # VALIDATE PICK QUALITY (Improved rules from winner analysis)
    print(f"\nValidating pick quality...")
    validated_bets = []
    validation_rejected = 0
    
    for bet in bets:
        confidence = float(bet.get('confidence', 0))
        combined_confidence = float(bet.get('combined_confidence', confidence))
        has_enrichment = bool(bet.get('enrichment_data'))
        reasoning = bet.get('why_now', '').lower()
        horse = bet.get('horse', 'Unknown')
        
        # Rule 1: Greyhounds with high confidence MUST have enrichment data
        if args.sport == 'greyhounds' and confidence >= 60 and not has_enrichment:
            print(f"REJECTED: {horse} - {confidence}% confidence but NO form data")
            validation_rejected += 1
            continue
        
        # Rule 2: Greyhounds without enrichment capped at 50%
        if args.sport == 'greyhounds' and not has_enrichment and confidence > 50:
            print(f"REJECTED: {horse} - {confidence}% without form data (max 50%)")
            validation_rejected += 1
            continue
        
        # Rule 3: Combined confidence threshold for greyhounds
        if args.sport == 'greyhounds' and combined_confidence < 50:
            print(f"REJECTED: {horse} - Combined confidence {combined_confidence}% < 50%")
            validation_rejected += 1
            continue
        
        # Rule 4: Shallow reasoning check
        shallow_indicators = ['lowest odds', 'shortest odds', 'best odds']
        performance_indicators = ['form', 'win rate', 'recent performance', 'track record', 'trainer']
        
        has_shallow = any(indicator in reasoning for indicator in shallow_indicators)
        has_performance = any(indicator in reasoning for indicator in performance_indicators)
        
        if has_shallow and not has_performance and confidence >= 60:
            print(f"REJECTED: {horse} - Shallow reasoning for {confidence}% confidence")
            validation_rejected += 1
            continue
        
        # Rule 5: Minimum combined confidence
        if combined_confidence < 2:
            print(f"REJECTED: {horse} - Combined confidence {combined_confidence}% < 2%")
            validation_rejected += 1
            continue
        
        # Passed all validation rules
        validated_bets.append(bet)
    
    print(f"Quality validation: {len(validated_bets)} passed, {validation_rejected} rejected")
    bets = validated_bets
    
    # Check for non-runners via Betfair API
    print(f"\nChecking for non-runners...")
    session_token, app_key = get_betfair_session()
    bets, non_runners = filter_non_runners(bets, session_token, app_key)
    if non_runners > 0:
        print(f"Removed {non_runners} non-runners")
    print(f"Remaining picks: {len(bets)}")
    
    # Apply race-level filtering rules
    print(f"\nApplying race-level filtering (max 2 picks/race, mixed types)...")
    bets, race_filtered = filter_picks_per_race(bets)
    print(f"Removed {race_filtered} picks due to race-level rules")
    print(f"Final pick count: {len(bets)} bets")
    
    # Deduplicate against existing database picks
    print(f"\nChecking for conflicts with existing database picks...")
    bets, bet_ids_to_delete, dedup_stats = deduplicate_against_database(bets, args.table, args.region)
    print(f"After database deduplication: {len(bets)} bets to save")
    
    # Save to DynamoDB
    if not args.dry_run:
        print(f"\nSaving to DynamoDB...")
        success, errors = save_to_dynamodb(bets, args.table, args.region, bet_ids_to_delete)
        
        print(f"\n{'='*60}")
        print(f"Results: {success} saved, {errors} errors")
        if bet_ids_to_delete:
            print(f"Deleted: {len(bet_ids_to_delete)} superseded picks")
        print(f"{'='*60}")
    else:
        print("\nDRY RUN - Would save these bets:")
        for bet in bets:
            print(f"  - {bet['horse']} at {bet['course']} ({bet['bet_type']}) - p_win: {bet['p_win']:.1%}")
        if bet_ids_to_delete:
            print(f"\nDRY RUN - Would delete these bet_ids:")
            for bet_id in bet_ids_to_delete:
                print(f"  - {bet_id}")
        print("\nRun without --dry_run to actually save to DynamoDB")
    
    # Save backup if requested
    if args.backup:
        save_to_json_backup(bets, args.backup)
    
    print("\n[OK] Complete")

if __name__ == "__main__":
    main()
