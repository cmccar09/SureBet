#!/usr/bin/env python3
"""
Hourly Results Updater
Fetches race results for recently completed races (within last few hours)
Run this every hour to capture results while still available in Betfair API
"""

import os
import json
import requests
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

def get_betfair_session():
    """Get Betfair session token using username/password"""
    # Try to load from creds file first
    try:
        with open('./betfair-creds.json', 'r') as f:
            creds = json.load(f)
            app_key = creds.get('app_key', 'XDDM8EHzaw8tokvQ')
            username = creds.get('username', 'cmccar02')
            password = creds.get('password')
    except:
        app_key = os.environ.get('BETFAIR_APP_KEY', 'XDDM8EHzaw8tokvQ')
        username = os.environ.get('BETFAIR_USERNAME', 'cmccar02')
        password = os.environ.get('BETFAIR_PASSWORD', 'Liv!23456')
    
    url = "https://identitysso.betfair.com/api/login"
    headers = {
        'X-Application': app_key,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    data = {
        'username': username,
        'password': password
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            result = response.json()
            session_token = result.get('token') or result.get('sessionToken')
            if session_token and result.get('status') == 'SUCCESS':
                return session_token
    except Exception as e:
        print(f"  Error getting session: {e}")
    
    return None

def fetch_market_results(market_ids, session_token):
    """Fetch market results from Betfair"""
    
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
                    market_status = market.get('status')
                    
                    # Only process closed/settled markets
                    if market_status not in ['CLOSED', 'SETTLED']:
                        continue
                    
                    for runner in market.get('runners', []):
                        selection_id = str(runner.get('selectionId'))
                        status = runner.get('status')
                        
                        # Map Betfair status to our outcome
                        if status == 'WINNER':
                            results[selection_id] = 'WON'
                        elif status == 'LOSER':
                            results[selection_id] = 'LOST'
                        elif status in ['PLACED']:
                            results[selection_id] = 'PLACED'
                        else:
                            results[selection_id] = 'LOST'
            else:
                print(f"  API response: {response.status_code}")
                
        except Exception as e:
            print(f"  Error fetching batch: {e}")
    
    return results

def update_pick_outcome(bet_id, outcome, odds, p_win, bet_type, table):
    """Update pick outcome in DynamoDB with profit/loss calculation"""
    try:
        # Calculate profit/loss (assuming 1 unit stake)
        if outcome == 'WON':
            if bet_type == 'WIN':
                profit_loss = float(odds) - 1.0
            else:  # EW
                # Won outright on EW bet = full win + place portion
                place_odds = 1.0 + ((float(odds) - 1.0) / 4.0)
                profit_loss = (float(odds) - 1.0) + (place_odds - 1.0)
        elif outcome == 'PLACED':
            # Only for EW bets - place portion only
            place_odds = 1.0 + ((float(odds) - 1.0) / 4.0)
            profit_loss = place_odds - 1.0 - 1.0  # Place return minus total EW stake
        else:
            # LOST
            if bet_type == 'EW':
                profit_loss = -2.0  # Lost both win and place stakes
            else:
                profit_loss = -1.0  # Lost win stake only
        
        table.update_item(
            Key={'bet_id': bet_id},
            UpdateExpression='SET outcome = :outcome, profit_loss = :pl, updated_at = :ts',
            ExpressionAttributeValues={
                ':outcome': outcome,
                ':pl': Decimal(str(round(profit_loss, 2))),
                ':ts': datetime.now().isoformat()
            }
        )
        return True, profit_loss
    except Exception as e:
        print(f"  Error updating {bet_id}: {e}")
        return False, 0

def main():
    print("="*70)
    print(f"HOURLY RESULTS UPDATE - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    # Connect to DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('SureBetBets')
    
    # Get picks from today and yesterday without outcomes
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"\n[1/5] Loading recent picks without results...")
    all_picks = []
    
    for date in [today, yesterday]:
        response = table.scan(
            FilterExpression='#date = :date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':date': date}
        )
        all_picks.extend(response.get('Items', []))
    
    # Filter to only picks without outcomes
    pending_picks = [p for p in all_picks if not p.get('outcome') or p.get('outcome') == 'Pending']
    
    print(f"  Found {len(pending_picks)} picks without results")
    
    if not pending_picks:
        print("\n✓ All recent picks already have results!")
        return
    
    # Get unique market IDs
    market_ids = list(set([str(pick.get('market_id')) for pick in pending_picks if pick.get('market_id')]))
    print(f"\n[2/5] Checking {len(market_ids)} markets for completed races...")
    
    # Get Betfair session
    session_token = get_betfair_session()
    if not session_token:
        print("  ❌ Failed to get Betfair session")
        print("  Will retry on next hourly run")
        return
    print("  ✓ Betfair session obtained")
    
    # Fetch results
    print(f"\n[3/5] Fetching market data...")
    results = fetch_market_results(market_ids, session_token)
    print(f"  Retrieved {len(results)} settled selections")
    
    if not results:
        print("  No markets settled yet (races may still be running)")
        return
    
    # Update picks
    print(f"\n[4/5] Updating outcomes...")
    updated = 0
    total_profit = 0
    
    for pick in pending_picks:
        selection_id = str(pick.get('selection_id', ''))
        
        if selection_id in results:
            outcome = results[selection_id]
            bet_id = pick.get('bet_id')
            horse = pick.get('horse', 'Unknown')
            odds = float(pick.get('odds', 0))
            p_win = float(pick.get('p_win', 0))
            bet_type = pick.get('bet_type', 'WIN')
            
            success, profit = update_pick_outcome(bet_id, outcome, odds, p_win, bet_type, table)
            if success:
                updated += 1
                total_profit += profit
                emoji = "🏆" if outcome == 'WON' else "📍" if outcome == 'PLACED' else "❌"
                print(f"  {emoji} {horse}: {outcome} ({profit:+.2f})")
    
    # Summary
    print(f"\n[5/5] Summary:")
    print(f"  Pending picks:   {len(pending_picks)}")
    print(f"  Updated:         {updated}")
    print(f"  Still pending:   {len(pending_picks) - updated}")
    if updated > 0:
        print(f"  Session P/L:     {total_profit:+.2f} units")
    
    print(f"\n✅ Update complete - {datetime.now().strftime('%H:%M:%S')}")
    print("="*70)

if __name__ == "__main__":
    main()
