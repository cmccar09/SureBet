#!/usr/bin/env python3
"""
Lambda: Fetch Race Results
Runs hourly to check for completed races and fetch results from Betfair
Stores results in DynamoDB for learning analysis
"""

import os
import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('SUREBET_DDB_TABLE', 'SureBetBets')

try:
    from betfair_odds_fetcher import get_betfair_session
    from betfair_cert_auth import authenticate_with_certificate
    import requests
    BETFAIR_AVAILABLE = True
except ImportError as e:
    print(f"Betfair modules not available: {e}")
    BETFAIR_AVAILABLE = False

def convert_floats(obj):
    """Convert floats to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats(v) for v in obj]
    return obj

def get_pending_results():
    """Get bets from last 24 hours that don't have results yet"""
    table = dynamodb.Table(table_name)
    
    # Get today's date for partition key
    today = datetime.utcnow().strftime('%Y-%m-%d')
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    pending_bets = []
    
    for date in [today, yesterday]:
        try:
            response = table.query(
                KeyConditionExpression='bet_date = :date',
                FilterExpression='attribute_not_exists(actual_result) AND track_performance = :track',
                ExpressionAttributeValues={':date': date, ':track': True}
            )
            pending_bets.extend(response.get('Items', []))
        except Exception as e:
            print(f"Error querying {date}: {e}")
    
    # Filter for races that happened >1 hour ago
    cutoff_time = datetime.utcnow() - timedelta(hours=1)
    ready_for_results = []
    
    for bet in pending_bets:
        race_time_str = bet.get('race_time', '')
        if not race_time_str:
            continue
        
        try:
            # Parse ISO format race time
            race_time = datetime.fromisoformat(race_time_str.replace('Z', '+00:00'))
            if race_time.replace(tzinfo=None) < cutoff_time:
                ready_for_results.append(bet)
        except Exception as e:
            print(f"Error parsing race time {race_time_str}: {e}")
    
    print(f"Found {len(ready_for_results)} bets ready for results (>1hr since race)")
    return ready_for_results

def fetch_market_results(market_ids, session_token, app_key):
    """Fetch settled market results from Betfair"""
    
    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/"
    
    headers = {
        "X-Application": app_key,
        "X-Authentication": session_token,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    results = []
    
    # Process markets in batches of 10 (API limit)
    for i in range(0, len(market_ids), 10):
        batch = market_ids[i:i+10]
        
        payload = {
            "marketIds": batch,
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS", "EX_TRADED"]
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            batch_results = response.json()
            results.extend(batch_results if isinstance(batch_results, list) else [])
            print(f"✓ Fetched results for {len(batch)} markets")
        except Exception as e:
            print(f"ERROR fetching batch: {e}")
            continue
    
    return results

def update_bet_results(bet, result_data):
    """Update bet in DynamoDB with actual result"""
    table = dynamodb.Table(table_name)
    
    bet_id = bet['bet_id']
    bet_date = bet['bet_date']
    
    update_data = {
        'actual_result': result_data['status'],
        'is_winner': result_data['is_winner'],
        'is_placed': result_data['is_placed'],
        'final_odds': result_data.get('last_price_traded', 0),
        'result_fetched_at': datetime.utcnow().isoformat()
    }
    
    # Calculate P&L
    stake = float(bet.get('stake', 0))
    bet_type = bet.get('bet_type', 'WIN')
    odds = float(bet.get('odds', 0))
    
    pnl = 0
    if bet_type == 'WIN':
        if result_data['is_winner']:
            pnl = stake * (odds - 1)
        else:
            pnl = -stake
    elif bet_type == 'EW':
        ew_fraction = float(bet.get('ew_fraction', 0.2))
        half_stake = stake / 2
        
        if result_data['is_winner']:
            # Both win and place pay
            win_profit = half_stake * (odds - 1)
            place_odds = 1 + ((odds - 1) * ew_fraction)
            place_profit = half_stake * (place_odds - 1)
            pnl = win_profit + place_profit
        elif result_data['is_placed']:
            # Only place pays
            place_odds = 1 + ((odds - 1) * ew_fraction)
            place_profit = half_stake * (place_odds - 1)
            pnl = place_profit - half_stake  # Lost win portion
        else:
            pnl = -stake
    
    update_data['pnl'] = convert_floats(pnl)
    
    try:
        table.update_item(
            Key={'bet_date': bet_date, 'bet_id': bet_id},
            UpdateExpression='SET actual_result = :result, is_winner = :winner, is_placed = :placed, '
                           'final_odds = :final_odds, result_fetched_at = :fetched, pnl = :pnl',
            ExpressionAttributeValues={
                ':result': update_data['actual_result'],
                ':winner': update_data['is_winner'],
                ':placed': update_data['is_placed'],
                ':final_odds': convert_floats(update_data['final_odds']),
                ':fetched': update_data['result_fetched_at'],
                ':pnl': update_data['pnl']
            }
        )
        print(f"✓ Updated {bet_id}: {update_data['actual_result']} (P&L: €{pnl:.2f})")
        return True
    except Exception as e:
        print(f"ERROR updating {bet_id}: {e}")
        return False

def lambda_handler(event, context):
    """Main Lambda handler"""
    
    print("=== RACE RESULTS FETCHER ===")
    print(f"Time: {datetime.utcnow().isoformat()}")
    
    if not BETFAIR_AVAILABLE:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Betfair modules not available'})
        }
    
    # Get credentials
    username = os.environ.get('BETFAIR_USERNAME')
    password = os.environ.get('BETFAIR_PASSWORD')
    app_key = os.environ.get('BETFAIR_APP_KEY')
    
    if not all([username, password, app_key]):
        print("ERROR: Missing Betfair credentials")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Missing credentials'})
        }
    
    # Authenticate
    print("Authenticating with Betfair...")
    session_token = authenticate_with_certificate(username, password, app_key)
    if not session_token:
        print("ERROR: Authentication failed")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Authentication failed'})
        }
    
    print("✓ Authentication successful")
    
    # Get pending bets
    pending_bets = get_pending_results()
    
    if not pending_bets:
        print("No bets ready for results")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'No pending results', 'updated': 0})
        }
    
    # Extract unique market IDs
    market_ids = list(set([bet.get('market_id') for bet in pending_bets if bet.get('market_id')]))
    print(f"Fetching results for {len(market_ids)} markets...")
    
    # Fetch results from Betfair
    market_results = fetch_market_results(market_ids, session_token, app_key)
    
    # Build lookup map: market_id -> selection_id -> result
    results_map = {}
    for market in market_results:
        market_id = market.get('marketId')
        status = market.get('status')
        
        if status not in ['CLOSED', 'SETTLED']:
            print(f"  Market {market_id}: {status} (not settled)")
            continue
        
        results_map[market_id] = {}
        
        for runner in market.get('runners', []):
            selection_id = str(runner.get('selectionId'))
            runner_status = runner.get('status', '')
            
            results_map[market_id][selection_id] = {
                'status': runner_status,
                'is_winner': runner_status == 'WINNER',
                'is_placed': runner_status in ['WINNER', 'PLACED'],
                'last_price_traded': runner.get('lastPriceTraded', 0)
            }
    
    # Update bets with results
    updated_count = 0
    
    for bet in pending_bets:
        market_id = bet.get('market_id')
        selection_id = str(bet.get('selection_id', ''))
        
        if market_id not in results_map:
            print(f"  No results for market {market_id}")
            continue
        
        if selection_id not in results_map[market_id]:
            print(f"  No result for selection {selection_id} in market {market_id}")
            continue
        
        result_data = results_map[market_id][selection_id]
        
        if update_bet_results(bet, result_data):
            updated_count += 1
    
    print(f"\n=== COMPLETE ===")
    print(f"Updated {updated_count} bets with results")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Results fetched',
            'pending_bets': len(pending_bets),
            'updated': updated_count
        })
    }
