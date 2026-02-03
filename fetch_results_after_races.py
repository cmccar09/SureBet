"""
Automated Results Fetcher - Runs 30 minutes after each race

This script should be scheduled to run at specific times (30 min after each race)
to capture results while they're still available in Betfair API.

Usage:
  python fetch_results_after_races.py

Scheduling:
  - Windows Task Scheduler: Schedule for 30 minutes after known race times
  - Or: Run in loop mode checking every 15 minutes
"""

import boto3
import json
import requests
from datetime import datetime, timedelta
from decimal import Decimal

# Load Betfair credentials
with open('betfair-creds.json', 'r') as f:
    creds = json.load(f)

BETFAIR_USERNAME = creds['username']
BETFAIR_PASSWORD = creds['password']
APP_KEY = creds['app_key']
CERT_PATH = 'betfair-client.crt'
KEY_PATH = 'betfair-client.key'

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

def betfair_login():
    """Login to Betfair"""
    login_url = 'https://identitysso-cert.betfair.com/api/certlogin'
    response = requests.post(
        login_url,
        cert=(CERT_PATH, KEY_PATH),
        data={'username': BETFAIR_USERNAME, 'password': BETFAIR_PASSWORD},
        headers={'X-Application': APP_KEY}
    )
    if response.status_code == 200:
        return response.json().get('sessionToken')
    return None

def get_races_needing_results():
    """Get races from last 2 hours that don't have results yet"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    response = table.query(
        KeyConditionExpression='bet_date = :date',
        FilterExpression='show_in_ui = :ui AND attribute_not_exists(outcome)',
        ExpressionAttributeValues={
            ':date': today,
            ':ui': True
        }
    )
    
    # Group by race
    races = {}
    for item in response['Items']:
        race_key = f"{item.get('course')}_{item.get('race_time')}"
        if race_key not in races:
            races[race_key] = {
                'course': item.get('course'),
                'race_time': item.get('race_time'),
                'market_id': item.get('market_id'),
                'horses': []
            }
        races[race_key]['horses'].append(item)
    
    # Filter to races from last 2 hours that should be finished
    cutoff_time = datetime.now() - timedelta(minutes=15)
    recent_races = {}
    
    for race_key, race_data in races.items():
        race_time_str = race_data['race_time']
        if race_time_str and 'T' in race_time_str:
            race_time = datetime.strptime(race_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            if race_time < cutoff_time:  # Race finished more than 15 min ago
                recent_races[race_key] = race_data
    
    return recent_races

def fetch_race_result(session_token, market_id):
    """Fetch result for a specific market"""
    url = 'https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/'
    
    headers = {
        'X-Application': APP_KEY,
        'X-Authentication': session_token,
        'Content-Type': 'application/json'
    }
    
    payload = {
        'marketIds': [market_id],
        'priceProjection': {'priceData': ['SP_AVAILABLE', 'SP_TRADED']}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0]
        return None
    except Exception as e:
        print(f"Error fetching market {market_id}: {e}")
        return None

def update_race_results(race_data, market_result):
    """Update database with race results"""
    if not market_result or market_result.get('status') != 'CLOSED':
        return False
    
    runners = market_result.get('runners', [])
    winner_id = None
    winner_name = None
    
    # Find winner
    for runner in runners:
        if runner.get('status') == 'WINNER':
            winner_id = runner.get('selectionId')
            break
    
    if not winner_id:
        print(f"No winner found for {race_data['course']} {race_data['race_time']}")
        return False
    
    # Update our horses
    updates = 0
    for horse_item in race_data['horses']:
        # Check if this horse won
        outcome = 'loss'
        profit = -30.0
        
        # Try to match winner (this is simplified - need better matching)
        if winner_name and winner_name.lower() in horse_item.get('horse_name', '').lower():
            outcome = 'win'
            odds = float(horse_item.get('decimal_odds', 0))
            profit = (odds * 30) - 30
        
        table.update_item(
            Key={
                'bet_date': horse_item['bet_date'],
                'bet_id': horse_item['bet_id']
            },
            UpdateExpression='SET outcome = :outcome, profit_loss = :profit, result_updated = :updated',
            ExpressionAttributeValues={
                ':outcome': outcome,
                ':profit': Decimal(str(profit)),
                ':updated': 'yes'
            }
        )
        updates += 1
    
    return updates > 0

def main():
    print("\n" + "="*80)
    print("AUTOMATED RESULTS FETCHER")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # Login
    session_token = betfair_login()
    if not session_token:
        print("ERROR: Betfair login failed")
        return
    
    print("Logged in to Betfair\n")
    
    # Get races needing results
    races = get_races_needing_results()
    
    if not races:
        print("No races needing results (all up to date or too recent)")
        return
    
    print(f"Found {len(races)} races needing results:\n")
    
    results_found = 0
    
    for race_key, race_data in races.items():
        course = race_data['course']
        race_time = race_data['race_time']
        market_id = race_data.get('market_id')
        
        print(f"Checking: {course} {race_time}")
        
        if not market_id:
            print("  WARNING: No market_id stored - cannot fetch from Betfair")
            print("  SOLUTION: Need to capture market_id when adding races")
            continue
        
        # Fetch result
        market_result = fetch_race_result(session_token, market_id)
        
        if market_result:
            status = market_result.get('status', 'Unknown')
            print(f"  Market status: {status}")
            
            if status == 'CLOSED':
                if update_race_results(race_data, market_result):
                    results_found += 1
                    print(f"  Results updated")
            else:
                print(f"  Race not finished yet")
        else:
            print(f"  No data from Betfair API")
    
    print("\n" + "="*80)
    print(f"Updated {results_found} races with results")
    print("="*80)
    
    if results_found == 0:
        print("\nNOTE: If Betfair API isn't returning data, use Racing Post scraper instead")
        print("      Results are only available for ~30 minutes after race finish")

if __name__ == '__main__':
    main()
