#!/usr/bin/env python3
"""
Fetch and update results for all pending picks
Works with both horses and greyhounds
"""

import os
import json
import requests
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize AWS
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

def get_betfair_session():
    """Get Betfair session token using password auth"""
    
    # Try credentials file first
    try:
        with open('betfair-creds.json', 'r') as f:
            creds = json.load(f)
            username = creds.get('username')
            password = creds.get('password')
            app_key = creds.get('app_key')
    except:
        username = os.environ.get('BETFAIR_USERNAME', 'cmccar02')
        password = os.environ.get('BETFAIR_PASSWORD', 'Liv!23456')
        app_key = os.environ.get('BETFAIR_APP_KEY', 'XDDM8EHzaw8tokvQ')
    
    url = "https://identitysso.betfair.com/api/login"
    headers = {
        'X-Application': app_key,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'username': username,
        'password': password
    }
    
    try:
        print(f"Logging in to Betfair as {username}...")
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            token = response.json().get('token')
            if token:
                print("[OK] Logged in successfully")
                return token, app_key
        print(f"[ERROR] Login failed: {response.text}")
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
    
    return None, None

def fetch_market_results(market_id, session_token, app_key):
    """Fetch results for a specific market"""
    
    url = "https://api.betfair.com/exchange/betting/json-rpc/v1"
    headers = {
        'X-Application': app_key,
        'X-Authentication': session_token,
        'Content-Type': 'application/json'
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": "SportsAPING/v1.0/listMarketBook",
        "params": {
            "marketIds": [market_id],
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS"]
            }
        },
        "id": 1
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and len(result['result']) > 0:
                return result['result'][0]
    except Exception as e:
        print(f"  [ERROR] Error fetching {market_id}: {e}")
    
    return None

def get_pending_bets(days_back=3):
    """Get bets without results from last N days"""
    
    pending = []
    
    for i in range(days_back):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        
        try:
            response = table.query(
                KeyConditionExpression='bet_date = :date',
                ExpressionAttributeValues={':date': date}
            )
            
            items = response.get('Items', [])
            
            # Filter for items without results
            for item in items:
                if not item.get('actual_result') and item.get('market_id'):
                    pending.append(item)
                    
        except Exception as e:
            print(f"[ERROR] Error querying {date}: {e}")
    
    return pending

def update_bet_results(picks, market_data):
    """Update picks with actual results"""
    
    updated = 0
    
    for pick in picks:
        market_id = pick.get('market_id')
        selection_id = str(pick.get('selection_id', ''))
        
        if not market_data:
            continue
        
        # Find runner in market data
        for runner in market_data.get('runners', []):
            if str(runner.get('selectionId')) == selection_id:
                status = runner.get('status')
                
                if status == 'WINNER':
                    result = 'WON'
                elif status == 'LOSER':
                    result = 'LOST'
                elif status == 'PLACED':
                    result = 'PLACED'
                else:
                    continue
                
                # Update database
                try:
                    bet_date = pick['bet_date']
                    bet_id = pick['bet_id']
                    
                    table.update_item(
                        Key={
                            'bet_date': bet_date,
                            'bet_id': bet_id
                        },
                        UpdateExpression='SET actual_result = :result, actual_position = :pos',
                        ExpressionAttributeValues={
                            ':result': result,
                            ':pos': runner.get('handicap', 0)
                        }
                    )
                    
                    name = pick.get('horse', 'Unknown')
                    venue = pick.get('course', 'Unknown')
                    print(f"  [OK] {name} @ {venue}: {result}")
                    updated += 1
                    
                except Exception as e:
                    print(f"  [ERROR] Failed to update: {e}")
                
                break
    
    return updated

def main():
    print("=" * 60)
    print("FETCHING RACE RESULTS")
    print("=" * 60)
    print()
    
    # Login to Betfair
    session_token, app_key = get_betfair_session()
    if not session_token:
        print("[ERROR] Could not log in to Betfair")
        return
    
    # Get pending bets
    print("\nLoading pending bets...")
    pending = get_pending_bets(days_back=3)
    print(f"Found {len(pending)} picks without results")
    
    if not pending:
        print("\n[OK] No pending bets to update")
        return
    
    # Group by market_id
    markets = {}
    for pick in pending:
        market_id = pick.get('market_id')
        if market_id:
            if market_id not in markets:
                markets[market_id] = []
            markets[market_id].append(pick)
    
    print(f"Fetching results for {len(markets)} markets...")
    print()
    
    total_updated = 0
    
    for i, (market_id, picks) in enumerate(markets.items(), 1):
        venue = picks[0].get('course', 'Unknown')
        race_time = picks[0].get('race_time', '')
        
        print(f"[{i}/{len(markets)}] {venue} - {race_time}")
        
        # Fetch market results
        market_data = fetch_market_results(market_id, session_token, app_key)
        
        if market_data:
            status = market_data.get('status', '')
            if status != 'CLOSED':
                print(f"  Market status: {status} (not closed yet)")
                continue
            
            # Update picks for this market
            updated = update_bet_results(picks, market_data)
            total_updated += updated
        else:
            print(f"  [NO DATA] Could not fetch market data")
    
    print()
    print("=" * 60)
    print(f"SUMMARY: Updated {total_updated}/{len(pending)} picks")
    print("=" * 60)

if __name__ == '__main__':
    main()
