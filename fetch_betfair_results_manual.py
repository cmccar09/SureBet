"""
Fetch Betfair results and match to today's finished races
"""
import boto3
import requests
import json
from datetime import datetime, timedelta
import pytz

# Load Betfair credentials
with open('betfair-creds.json', 'r') as f:
    creds = json.load(f)

# Betfair login
def betfair_login():
    """Login to Betfair using certificate"""
    url = 'https://identitysso-cert.betfair.com/api/certlogin'
    
    headers = {
        'X-Application': creds['app_key'],
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'username': creds['username'],
        'password': creds['password']
    }
    
    response = requests.post(
        url,
        headers=headers,
        data=data,
        cert=('betfair-client.crt', 'betfair-client.key')
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('loginStatus') == 'SUCCESS':
            print(f"✓ Betfair login successful")
            return result['sessionToken']
    
    print(f"✗ Login failed: {response.text}")
    return None

# Get results for UK/Irish horse racing today
def get_race_results(session_token):
    """Get race results from Betfair for today"""
    url = 'https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/'
    
    uk_tz = pytz.timezone('Europe/London')
    now = datetime.now(uk_tz)
    today_start = now.replace(hour=0, minute=0, second=0)
    today_end = now.replace(hour=23, minute=59, second=59)
    
    headers = {
        'X-Application': creds['app_key'],
        'X-Authentication': session_token,
        'Content-Type': 'application/json'
    }
    
    # Get all horse racing markets for today
    payload = {
        "filter": {
            "eventTypeIds": ["7"],  # Horse Racing
            "marketCountries": ["GB", "IE"],
            "marketTypeCodes": ["WIN"],
            "marketStartTime": {
                "from": today_start.isoformat(),
                "to": today_end.isoformat()
            }
        },
        "maxResults": 200,
        "marketProjection": [
            "MARKET_START_TIME",
            "RUNNER_DESCRIPTION",
            "EVENT"
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        markets = response.json()
        print(f"✓ Found {len(markets)} markets")
        return markets
    else:
        print(f"✗ Failed to get markets: {response.text}")
        return []

# Get market results
def get_market_winners(session_token, market_id):
    """Get winner for a specific market"""
    url = 'https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/'
    
    headers = {
        'X-Application': creds['app_key'],
        'X-Authentication': session_token,
        'Content-Type': 'application/json'
    }
    
    payload = {
        "marketIds": [market_id],
        "priceProjection": {
            "priceData": ["EX_BEST_OFFERS"]
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    return None

# Main execution
print("="*80)
print("BETFAIR RESULTS FETCHER - MANUAL MATCHING")
print("="*80)

# Login
session_token = betfair_login()
if not session_token:
    print("Cannot proceed without login")
    exit(1)

# Get markets
markets = get_race_results(session_token)

# Get our database races
db = boto3.resource('dynamodb', region_name='eu-west-1')
table = db.Table('SureBetBets')

response = table.query(
    KeyConditionExpression='bet_date = :date',
    FilterExpression='show_in_ui = :ui',
    ExpressionAttributeValues={
        ':date': '2026-02-03',
        ':ui': True
    }
)

our_picks = response['Items']
print(f"\n✓ Found {len(our_picks)} UI picks in database")

# Try to match by venue and time
uk_tz = pytz.timezone('Europe/London')
now = datetime.now(uk_tz)

print(f"\nCurrent UK time: {now.strftime('%H:%M')}")
print("\n" + "="*80)
print("MATCHING RACES:")
print("="*80)

matched = 0
for pick in our_picks:
    horse = pick.get('horse', '')
    course = pick.get('course', '').lower()
    race_time_str = pick.get('race_time', '')
    
    # Parse race time
    if 'T' in race_time_str:
        race_dt = datetime.fromisoformat(race_time_str.replace('Z', '+00:00'))
        race_time = race_dt.astimezone(uk_tz)
        time_str = race_time.strftime('%H:%M')
    else:
        time_str = race_time_str
        continue
    
    # Check if race has finished
    if race_time > now:
        print(f"\n⏳ {time_str} {course.title():15} - Not finished yet")
        continue
    
    print(f"\n🔍 {time_str} {course.title():15} {horse:25}")
    
    # Try to find matching market
    for market in markets:
        event_name = market.get('event', {}).get('name', '').lower()
        market_time = datetime.fromisoformat(market['marketStartTime'].replace('Z', '+00:00')).astimezone(uk_tz)
        market_time_str = market_time.strftime('%H:%M')
        
        # Match by venue name and time
        if course in event_name and time_str == market_time_str:
            print(f"  ✓ Matched market: {market['marketName']}")
            
            # Get results
            market_id = market['marketId']
            results = get_market_winners(session_token, market_id)
            
            if results and len(results) > 0:
                runners = results[0].get('runners', [])
                
                # Find winner
                winner = None
                for runner in runners:
                    if runner.get('status') == 'WINNER':
                        # Match runner to our picks
                        runner_name = None
                        for r in market.get('runners', []):
                            if r['selectionId'] == runner['selectionId']:
                                runner_name = r['runnerName']
                                break
                        
                        if runner_name:
                            winner = runner_name
                            print(f"  🏆 Winner: {winner}")
                            
                            # Check if our pick won
                            if horse.lower() in winner.lower() or winner.lower() in horse.lower():
                                print(f"  ✅ OUR PICK WON!")
                                outcome = 'win'
                                profit = float(pick.get('odds', 0)) * 30  # €30 stake
                            else:
                                print(f"  ❌ Our pick lost")
                                outcome = 'loss'
                                profit = -30
                            
                            # Update database
                            table.update_item(
                                Key={
                                    'bet_date': '2026-02-03',
                                    'bet_id': pick['bet_id']
                                },
                                UpdateExpression='SET outcome = :outcome, profit_loss = :pl, actual_winner = :winner, result_updated = :ts',
                                ExpressionAttributeValues={
                                    ':outcome': outcome,
                                    ':pl': profit,
                                    ':winner': winner,
                                    ':ts': datetime.now().isoformat()
                                }
                            )
                            
                            matched += 1
                            break
            
            break

print(f"\n{'='*80}")
print(f"SUMMARY: Matched {matched} races with results")
print("="*80)
