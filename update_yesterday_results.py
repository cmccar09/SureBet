#!/usr/bin/env python3
"""
Update yesterday's race results from Betfair
Specifically designed to update picks that don't have outcomes yet
"""

import os
import json
import requests
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

def get_betfair_session():
    """Get Betfair session token using certificate auth"""
    cert_file = './betfair-client.crt'
    key_file = './betfair-client.key'
    
    url = "https://identitysso-cert.betfair.com/api/certlogin"
    headers = {
        'X-Application': os.environ.get('BETFAIR_APP_KEY', 'XDDM8EHzaw8tokvQ'),
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'username': os.environ.get('BETFAIR_USERNAME', 'cmccar02'),
        'password': os.environ.get('BETFAIR_PASSWORD', 'Liv!23456')
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, cert=(cert_file, key_file))
        result = response.json()
        if result.get('loginStatus') == 'SUCCESS':
            return result.get('sessionToken')
    except Exception as e:
        print(f"Error getting session: {e}")
    
    return None

def fetch_market_results(market_ids, session_token):
    """Fetch settled market results from Betfair"""
    
    app_key = os.environ.get('BETFAIR_APP_KEY', 'XDDM8EHzaw8tokvQ')
    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/"
    
    headers = {
        "X-Application": app_key,
        "X-Authentication": session_token,
        "Content-Type": "application/json"
    }
    
    results = {}
    
    # Process in batches of 10
    for i in range(0, len(market_ids), 10):
        batch = market_ids[i:i+10]
        
        payload = {
            "marketIds": batch,
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS"]
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                markets = response.json()
                
                for market in markets:
                    for runner in market.get('runners', []):
                        selection_id = str(runner.get('selectionId'))
                        status = runner.get('status')
                        
                        # Map Betfair status to our outcome
                        if status == 'WINNER':
                            results[selection_id] = 'WON'
                        elif status == 'LOSER':
                            results[selection_id] = 'LOST'
                        elif status in ['PLACED']:
                            # Need to check the place position
                            results[selection_id] = 'PLACED'
                        else:
                            results[selection_id] = 'LOST'  # Default for non-winners
            else:
                print(f"Error response: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Error fetching batch: {e}")
    
    return results

def update_pick_outcome(bet_id, outcome, odds, p_win, table):
    """Update pick outcome in DynamoDB"""
    try:
        # Calculate profit/loss (assuming 1 unit stake)
        if outcome == 'WON':
            profit_loss = float(odds) - 1.0  # Profit on 1 unit
        elif outcome == 'PLACED':
            # Assuming 1/4 odds for places (simplified)
            place_odds = 1.0 + ((float(odds) - 1.0) / 4.0)
            profit_loss = place_odds - 1.0
        else:
            profit_loss = -1.0  # Lost the stake
        
        table.update_item(
            Key={'bet_id': bet_id},
            UpdateExpression='SET outcome = :outcome, profit_loss = :pl, updated_at = :ts',
            ExpressionAttributeValues={
                ':outcome': outcome,
                ':pl': Decimal(str(profit_loss)),
                ':ts': datetime.now().isoformat()
            }
        )
        return True
    except Exception as e:
        print(f"Error updating {bet_id}: {e}")
        return False

def main():
    print("="*70)
    print("UPDATING YESTERDAY'S RACE RESULTS")
    print("="*70)
    
    # Get yesterday's date
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\nTarget date: {yesterday}")
    
    # Connect to DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('SureBetBets')
    
    # Scan for yesterday's picks without outcomes
    print("\n[1/4] Loading yesterday's picks...")
    response = table.scan(
        FilterExpression='#date = :yesterday',
        ExpressionAttributeNames={'#date': 'date'},
        ExpressionAttributeValues={
            ':yesterday': yesterday
        }
    )
    
    picks = response.get('Items', [])
    print(f"  Found {len(picks)} picks without results")
    
    if not picks:
        print("\n✓ All picks already have results!")
        return
    
    # Get unique market IDs
    market_ids = list(set([str(pick.get('market_id')) for pick in picks if pick.get('market_id')]))
    print(f"\n[2/4] Fetching results for {len(market_ids)} markets...")
    
    # Get Betfair session
    session_token = get_betfair_session()
    if not session_token:
        print("  ❌ Failed to get Betfair session")
        return
    print("  ✓ Betfair session obtained")
    
    # Fetch results
    results = fetch_market_results(market_ids, session_token)
    print(f"  Retrieved {len(results)} selection results")
    
    # Update picks
    print("\n[3/4] Updating outcomes...")
    updated = 0
    
    for pick in picks:
        selection_id = str(pick.get('selection_id', ''))
        
        # Skip if already has outcome
        current_outcome = pick.get('outcome')
        if current_outcome and current_outcome != 'Pending':
            continue
            
        if selection_id in results:
            outcome = results[selection_id]
            bet_id = pick.get('bet_id')
            horse = pick.get('horse', 'Unknown')
            odds = float(pick.get('odds', 0))
            p_win = float(pick.get('p_win', 0))
            
            if update_pick_outcome(bet_id, outcome, odds, p_win, table):
                updated += 1
                print(f"  ✓ {horse}: {outcome}")
        else:
            horse = pick.get('horse', 'Unknown')
            print(f"  ⚠️  {horse}: No result data (market may not be settled yet)")
    
    # Summary
    print(f"\n[4/4] Summary:")
    print(f"  Total picks:     {len(picks)}")
    print(f"  Updated:         {updated}")
    print(f"  Still pending:   {len(picks) - updated}")
    
    if updated > 0:
        print("\n✅ Results updated! Re-running report...")
        # Re-run the report
        os.system('python send_yesterday_top5_report.py')
    else:
        print("\n⚠️  No results available - races may not be settled yet")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
