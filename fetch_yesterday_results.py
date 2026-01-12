#!/usr/bin/env python3
"""Fetch yesterday's race results from Betfair"""
import json
import requests
import boto3
from datetime import datetime, timedelta

# Load credentials
with open('betfair-creds.json', 'r') as f:
    creds = json.load(f)

# AWS DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("=" * 70)
print("FETCHING YESTERDAY'S RESULTS")
print("=" * 70)

# Step 1: Login
print("\n[1/4] Logging in to Betfair...")
cert_url = "https://identitysso-cert.betfair.com/api/certlogin"

response = requests.post(
    cert_url,
    headers={
        'X-Application': creds['app_key'],
        'Content-Type': 'application/x-www-form-urlencoded'
    },
    data={'username': creds['username'], 'password': creds['password']},
    cert=('betfair-client.crt', 'betfair-client.key'),
    timeout=10
)

if response.status_code == 200:
    result = response.json()
    login_status = result.get('loginStatus', result.get('status'))
    
    if login_status == 'SUCCESS':
        session_token = result.get('sessionToken')
        print(f"  [OK] Logged in successfully")
    else:
        print(f"  [FAILED] Login status: {login_status}")
        exit(1)
else:
    print(f"  [FAILED] HTTP {response.status_code}")
    exit(1)

# Step 2: Get yesterday's bets
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
print(f"\n[2/4] Loading bets from {yesterday}...")

response = table.query(
    KeyConditionExpression='bet_date = :date',
    ExpressionAttributeValues={':date': yesterday}
)

bets = response.get('Items', [])
pending = [b for b in bets if not b.get('actual_result') and b.get('market_id')]

print(f"  Found {len(bets)} total bets, {len(pending)} without results")

if not pending:
    print("\n[OK] All bets already have results")
    exit(0)

# Group by market
markets = {}
for bet in pending:
    market_id = bet.get('market_id')
    if market_id not in markets:
        markets[market_id] = []
    markets[market_id].append(bet)

# Step 3: Fetch results
print(f"\n[3/4] Fetching results for {len(markets)} markets...")

api_url = "https://api.betfair.com/exchange/betting/json-rpc/v1"
headers = {
    'X-Application': creds['app_key'],
    'X-Authentication': session_token,
    'Content-Type': 'application/json'
}

updated_count = 0

for i, (market_id, market_bets) in enumerate(markets.items(), 1):
    venue = market_bets[0].get('course', 'Unknown')
    race_time = market_bets[0].get('race_time', '')[:16]
    
    print(f"\n  [{i}/{len(markets)}] {venue} - {race_time}")
    
    payload = {
        "jsonrpc": "2.0",
        "method": "SportsAPING/v1.0/listMarketBook",
        "params": {
            "marketIds": [market_id],
            "priceProjection": {"priceData": ["EX_BEST_OFFERS"]}
        },
        "id": 1
    }
    
    try:
        api_response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        
        if api_response.status_code == 200:
            api_result = api_response.json()
            
            if 'result' in api_result and len(api_result['result']) > 0:
                market_data = api_result['result'][0]
                status = market_data.get('status', '')
                
                if status != 'CLOSED':
                    print(f"    Status: {status} (not closed yet)")
                    continue
                
                # Update each bet
                for bet in market_bets:
                    selection_id = str(bet.get('selection_id', ''))
                    bet_type = bet.get('bet_type', 'WIN')
                    race_type = bet.get('sport', 'horses')
                    
                    for runner in market_data.get('runners', []):
                        if str(runner.get('selectionId')) == selection_id:
                            runner_status = runner.get('status')
                            
                            # For Each Way bets on horses, PLACED counts as WON
                            if bet_type == 'EW' and race_type == 'horses':
                                if runner_status == 'WINNER':
                                    result = 'WON'
                                elif runner_status == 'PLACED':
                                    result = 'WON'  # EW bet placed = win
                                elif runner_status == 'LOSER':
                                    result = 'LOST'
                                else:
                                    continue
                            else:
                                # For WIN bets or greyhounds, only WINNER counts
                                if runner_status == 'WINNER':
                                    result = 'WON'
                                elif runner_status == 'LOSER' or runner_status == 'PLACED':
                                    result = 'LOST'
                                else:
                                    continue
                            
                            # Update database
                            table.update_item(
                                Key={
                                    'bet_date': bet['bet_date'],
                                    'bet_id': bet['bet_id']
                                },
                                UpdateExpression='SET actual_result = :result',
                                ExpressionAttributeValues={':result': result}
                            )
                            
                            horse = bet.get('horse', 'Unknown')
                            print(f"    [OK] {horse}: {result}")
                            updated_count += 1
                            break
            else:
                print(f"    [NO DATA]")
        else:
            print(f"    [ERROR] HTTP {api_response.status_code}")
    except Exception as e:
        print(f"    [ERROR] {str(e)[:60]}")

# Step 4: Summary
print("\n" + "=" * 70)
print(f"RESULTS: Updated {updated_count}/{len(pending)} bets")
print("=" * 70)

if updated_count > 0:
    print("\n[TIP] Run: python daily_learning_cycle.py")
