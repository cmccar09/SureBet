#!/usr/bin/env python3
"""
Update bet results from Betfair
Fetches race results and updates DynamoDB with outcomes
Run this after races complete to feed the learning system
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
    """Get Betfair session token"""
    
    url = "https://identitysso.betfair.com/api/login"
    headers = {
        'X-Application': os.environ.get('BETFAIR_APP_KEY', 'XDDM8EHzaw8tokvQ'),
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'username': os.environ.get('BETFAIR_USERNAME', 'cmccar02'),
        'password': os.environ.get('BETFAIR_PASSWORD', 'Liv!23456')
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get('token')
    except Exception as e:
        print(f"Error getting session: {e}")
    
    return None

def fetch_race_results(market_ids, session_token):
    """Fetch results for specific markets from Betfair"""
    
    url = "https://api.betfair.com/exchange/betting/json-rpc/v1"
    headers = {
        'X-Application': os.environ.get('BETFAIR_APP_KEY'),
        'X-Authentication': session_token,
        'Content-Type': 'application/json'
    }
    
    results = {}
    
    for market_id in market_ids:
        payload = {
            "jsonrpc": "2.0",
            "method": "SportsAPING/v1.0/listMarketBook",
            "params": {
                "marketIds": [market_id],
                "priceProjection": {
                    "priceData": ["EX_TRADED"]
                }
            },
            "id": 1
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and len(data['result']) > 0:
                    market_book = data['result'][0]
                    
                    # Find winners
                    for runner in market_book.get('runners', []):
                        selection_id = str(runner['selectionId'])
                        status = runner.get('status')
                        
                        if status == 'WINNER':
                            results[selection_id] = 'won'
                        elif status == 'PLACED':
                            results[selection_id] = 'placed'
                        elif status == 'LOSER':
                            results[selection_id] = 'lost'
                        
        except Exception as e:
            print(f"Error fetching results for {market_id}: {e}")
    
    return results

def get_pending_bets():
    """Get all pending bets from DynamoDB"""
    
    try:
        # Scan for pending bets from last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        
        response = table.scan(
            FilterExpression='#status = :status AND #ts > :cutoff',
            ExpressionAttributeNames={
                '#status': 'status',
                '#ts': 'timestamp'
            },
            ExpressionAttributeValues={
                ':status': 'active',
                ':cutoff': cutoff.isoformat()
            }
        )
        
        return response.get('Items', [])
        
    except Exception as e:
        print(f"Error getting pending bets: {e}")
        return []

def update_bet_result(bet_id, result):
    """Update bet result in DynamoDB"""
    
    try:
        table.update_item(
            Key={'bet_id': bet_id},
            UpdateExpression='SET #result = :result, #status = :status',
            ExpressionAttributeNames={
                '#result': 'result',
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':result': result,
                ':status': 'completed'
            }
        )
        return True
    except Exception as e:
        print(f"Error updating {bet_id}: {e}")
        return False

def main():
    """Main execution"""
    
    print("="*60)
    print("UPDATING BET RESULTS FROM BETFAIR")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Get pending bets
    print("\n[1/4] Loading pending bets...")
    pending_bets = get_pending_bets()
    print(f"  Found {len(pending_bets)} pending bets")
    
    if not pending_bets:
        print("\n✓ No pending bets to update")
        return
    
    # Extract unique market IDs
    market_ids = list(set([bet.get('market_id') for bet in pending_bets if bet.get('market_id')]))
    print(f"\n[2/4] Fetching results for {len(market_ids)} markets...")
    
    # Get Betfair session
    session_token = get_betfair_session()
    if not session_token:
        print("  ❌ Failed to get Betfair session token")
        print("  Cannot update results automatically")
        return
    
    # Fetch results
    results = fetch_race_results(market_ids, session_token)
    print(f"  Retrieved results for {len(results)} selections")
    
    # Update bets
    print("\n[3/4] Updating bet outcomes...")
    updated = 0
    for bet in pending_bets:
        selection_id = bet.get('selection_id', '')
        
        if selection_id in results:
            result = results[selection_id]
            bet_id = bet.get('bet_id')
            horse = bet.get('horse', 'Unknown')
            
            if update_bet_result(bet_id, result):
                updated += 1
                print(f"  ✓ {horse}: {result}")
    
    # Summary
    print(f"\n[4/4] Summary:")
    print(f"  Pending bets:  {len(pending_bets)}")
    print(f"  Updated:       {updated}")
    print(f"  Still pending: {len(pending_bets) - updated}")
    
    if updated > 0:
        print("\n✓ Results updated successfully!")
        print("\nNext: Run daily learning cycle to analyze performance")
        print("  python daily_learning_cycle.py")
    else:
        print("\n⚠️  No results available yet (races may still be running)")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
