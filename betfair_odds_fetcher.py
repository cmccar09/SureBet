"""
Betfair Odds Fetcher
Fetches live odds from Betfair API for multiple sports
Supports: Horse Racing, Darts, Cricket, Rugby, Football
Uses session token from AWS Secrets Manager
"""

import json
import boto3
import requests
import datetime

secrets_client = boto3.client('secretsmanager')

# Betfair Event Type IDs
SPORT_EVENT_TYPES = {
    'horse_racing': '7',
    'darts': '3',
    'cricket': '4',
    'rugby': '5',
    'football': '1'
}

def get_betfair_session():
    """Get current Betfair session token from Secrets Manager"""
    try:
        response = secrets_client.get_secret_value(SecretId='betfair-credentials')
        secret_string = response['SecretString']
        
        # Handle escaped quotes from PowerShell
        if secret_string.startswith('{\\'):
            secret_string = secret_string.replace('\\', '')
        
        credentials = json.loads(secret_string)
        return credentials['app_key'], credentials['session_token']
    except Exception as e:
        print(f"Error getting Betfair session: {e}")
        raise Exception("Betfair credentials not found in Secrets Manager")

def fetch_betfair_markets(app_key, session_token, sport='horse_racing'):
    """Fetch markets from Betfair for specified sport"""
    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/"
    
    now = datetime.datetime.utcnow()
    to_time = now + datetime.timedelta(hours=24)
    
    event_type_id = SPORT_EVENT_TYPES.get(sport, '7')  # Default to horse racing
    
    # Base filter
    market_filter = {
        "eventTypeIds": [event_type_id],
        "marketStartTime": {
            "from": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": to_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    }
    
    # Sport-specific filters
    if sport == 'horse_racing':
        market_filter["marketCountries"] = ["GB", "IE"]
        market_filter["marketTypeCodes"] = ["WIN"]
    elif sport in ['football', 'rugby', 'cricket']:
        market_filter["marketTypeCodes"] = ["MATCH_ODDS"]
    elif sport == 'darts':
        market_filter["marketTypeCodes"] = ["MATCH_ODDS"]
    
    # Request UK/IRE markets in next 24 hours
    request_body = {
        "filter": market_filter,
        "maxResults": 50,
        "marketProjection": ["RUNNER_METADATA", "EVENT", "MARKET_START_TIME"]
    }
    
    headers = {
        'X-Application': app_key,
        'X-Authentication': session_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        
        if response.status_code == 401:
            raise Exception("Betfair session expired - will refresh on next schedule")
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching Betfair markets: {e}")
        raise

def fetch_betfair_odds(app_key, session_token, market_ids):
    """Fetch current odds for given market IDs"""
    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/"
    
    request_body = {
        "marketIds": market_ids,
        "priceProjection": {
            "priceData": ["EX_BEST_OFFERS"]
        }
    }
    
    headers = {
        'X-Application': app_key,
        'X-Authentication': session_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching Betfair odds: {e}")
        raise

def get_live_betfair_races():
    """
    Main function to fetch live UK/IRE horse racing with odds
    Returns races in format compatible with main Lambda
    """
    print("Fetching Betfair session from Secrets Manager...")
    app_key, session_token = get_betfair_session()
    
    print("Fetching UK/IRE horse racing markets...")
    markets = fetch_betfair_markets(app_key, session_token)
    
    if not markets:
        print("No horse racing markets found")
        return []
    
    print(f"Found {len(markets)} markets, fetching odds...")
    
    # Betfair API limit is ~10 markets per request for listMarketBook
    # Batch the requests to avoid 400 errors
    odds_by_market = {}
    batch_size = 10
    
    for i in range(0, min(len(markets), 30), batch_size):  # Limit to first 30 markets
        batch = markets[i:i+batch_size]
        market_ids = [market['marketId'] for market in batch]
        
        try:
            print(f"Fetching odds for batch {i//batch_size + 1} ({len(market_ids)} markets)...")
            odds_data = fetch_betfair_odds(app_key, session_token, market_ids)
            
            # Add to lookup
            for book in odds_data:
                odds_by_market[book['marketId']] = book
        except Exception as e:
            print(f"Error fetching odds batch {i//batch_size + 1}: {e}")
            continue
    
    # Format races for main Lambda
    races = []
    now = datetime.datetime.utcnow()
    
    for market in markets:
        market_id = market['marketId']
        market_start = datetime.datetime.strptime(market['marketStartTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
        
        # Filter to 15 mins - 24 hours window
        time_diff = (market_start - now).total_seconds()
        if time_diff < 900 or time_diff > 86400:  # 15 mins to 24 hours
            continue
        
        # Get odds for this market
        odds = odds_by_market.get(market_id, {})
        runners_data = odds.get('runners', [])
        
        # Format runners with odds
        runners = []
        for i, runner_meta in enumerate(market.get('runners', [])):
            runner_id = runner_meta['selectionId']
            runner_name = runner_meta['runnerName']
            
            # Find odds for this runner
            runner_odds = next((r for r in runners_data if r['selectionId'] == runner_id), None)
            
            if runner_odds and runner_odds.get('ex', {}).get('availableToBack'):
                best_back = runner_odds['ex']['availableToBack'][0]['price']
                runners.append({
                    "name": runner_name,
                    "selectionId": runner_id,
                    "odds": best_back
                })
        
        if runners:
            races.append({
                "market_id": market_id,
                "race_time": market['marketStartTime'],
                "course": market.get('event', {}).get('venue', 'Unknown'),
                "runners": runners,
                "start_time": market_start
            })
    
    print(f"Returning {len(races)} races with odds in betting window")
    return races
