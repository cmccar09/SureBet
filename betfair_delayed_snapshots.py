#!/usr/bin/env python3
"""
betfair_delayed_snapshots.py
Fetches live horse racing odds from Betfair API and saves as snapshot JSON
Uses credentials from betfair-creds.json
"""

import json
import sys
import os
import argparse
from datetime import datetime, timedelta
import requests

def load_credentials():
    """Load Betfair credentials from betfair-creds.json"""
    creds_path = os.path.join(os.path.dirname(__file__), 'betfair-creds.json')
    
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Credentials file not found: {creds_path}")
    
    with open(creds_path, 'r') as f:
        creds = json.load(f)
    
    return creds['app_key'], creds['session_token']

def fetch_markets(app_key, session_token, hours_ahead=24):
    """Fetch UK/IRE horse racing markets from Betfair"""
    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/"
    
    now = datetime.utcnow()
    to_time = now + timedelta(hours=hours_ahead)
    
    payload = {
        "filter": {
            "eventTypeIds": ["7"],  # Horse Racing
            "marketCountries": ["GB", "IE"],
            "marketTypeCodes": ["WIN"],
            "marketStartTime": {
                "from": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": to_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        },
        "maxResults": 100,
        "marketProjection": ["RUNNER_METADATA", "EVENT", "MARKET_START_TIME", "COMPETITION", "RUNNER_DESCRIPTION"]
    }
    
    headers = {
        'X-Application': app_key,
        'X-Authentication': session_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 401:
            print("ERROR: Betfair session expired - run betfair_session_refresh_eu.py", file=sys.stderr)
            sys.exit(1)
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching markets: {e}", file=sys.stderr)
        sys.exit(1)

def fetch_odds(app_key, session_token, market_ids):
    """Fetch odds for given market IDs"""
    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/"
    
    payload = {
        "marketIds": market_ids,
        "priceProjection": {
            "priceData": ["EX_BEST_OFFERS", "EX_ALL_OFFERS"]
        }
    }
    
    headers = {
        'X-Application': app_key,
        'X-Authentication': session_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching odds: {e}", file=sys.stderr)
        return []

def format_snapshot(markets, odds_by_market):
    """Format data into snapshot structure for run_saved_prompt.py"""
    races = []
    now = datetime.utcnow()
    
    for market in markets:
        market_id = market['marketId']
        market_name = market.get('marketName', 'Unknown Race')
        
        # Parse market start time
        try:
            market_start = datetime.strptime(market['marketStartTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            market_start = datetime.strptime(market['marketStartTime'], "%Y-%m-%dT%H:%M:%SZ")
        
        # Filter: 15 mins ahead to 24 hours
        time_diff = (market_start - now).total_seconds()
        if time_diff < 900 or time_diff > 86400:  # 15 mins to 24 hours
            continue
        
        # Get venue/course info
        event = market.get('event', {})
        venue = event.get('venue', event.get('name', 'Unknown'))
        competition = market.get('competition', {}).get('name', 'Unknown')
        
        # Get odds data for this market
        odds_data = odds_by_market.get(market_id, {})
        runners_odds = odds_data.get('runners', [])
        
        # Build runners list
        runners = []
        for runner_meta in market.get('runners', []):
            selection_id = runner_meta['selectionId']
            runner_name = runner_meta['runnerName']
            
            # Find matching odds
            runner_odds = next((r for r in runners_odds if r['selectionId'] == selection_id), None)
            
            # Extract best back odds
            best_back = None
            if runner_odds and runner_odds.get('status') == 'ACTIVE':
                back_offers = runner_odds.get('ex', {}).get('availableToBack', [])
                if back_offers:
                    best_back = back_offers[0]['price']
            
            if best_back:
                runners.append({
                    "name": runner_name,
                    "selectionId": selection_id,
                    "odds": best_back
                })
        
        # Only include races with odds available
        if runners:
            races.append({
                "market_id": market_id,
                "market_name": market_name,
                "venue": venue,
                "course": venue,  # Alias
                "competition": competition,
                "start_time": market['marketStartTime'],
                "runners": runners,
                "total_runners": len(runners)
            })
    
    return {
        "timestamp": now.isoformat() + "Z",
        "races": races,
        "total_races": len(races)
    }

def main():
    parser = argparse.ArgumentParser(description="Fetch live Betfair horse racing odds")
    parser.add_argument('--out', type=str, default='response.json',
                        help='Output JSON file path (default: response.json)')
    parser.add_argument('--hours', type=int, default=24,
                        help='Hours ahead to fetch (default: 24)')
    parser.add_argument('--max_races', type=int, default=100,
                        help='Maximum races to fetch (default: 100)')
    
    args = parser.parse_args()
    
    print("Loading Betfair credentials...")
    app_key, session_token = load_credentials()
    
    print(f"Fetching markets (next {args.hours} hours)...")
    markets = fetch_markets(app_key, session_token, args.hours)
    
    if not markets:
        print("WARNING: No markets found", file=sys.stderr)
        sys.exit(0)
    
    print(f"Found {len(markets)} markets")
    
    # Fetch odds in batches (Betfair limit ~10 per request)
    odds_by_market = {}
    batch_size = 10
    
    for i in range(0, min(len(markets), args.max_races), batch_size):
        batch = markets[i:i+batch_size]
        market_ids = [m['marketId'] for m in batch]
        
        print(f"Fetching odds batch {i//batch_size + 1}/{(min(len(markets), args.max_races) + batch_size - 1)//batch_size}...")
        odds_batch = fetch_odds(app_key, session_token, market_ids)
        
        for book in odds_batch:
            odds_by_market[book['marketId']] = book
    
    print(f"Fetched odds for {len(odds_by_market)} markets")
    
    # Format snapshot
    snapshot = format_snapshot(markets, odds_by_market)
    
    print(f"Formatted {snapshot['total_races']} races with odds")
    
    # Save to file
    with open(args.out, 'w') as f:
        json.dump(snapshot, f, indent=2)
    
    print(f"✓ Saved snapshot to {args.out}")
    print(f"  Races: {snapshot['total_races']}")
    print(f"  Timestamp: {snapshot['timestamp']}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
