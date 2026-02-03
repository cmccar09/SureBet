"""
Fetch settled Betfair markets for today and match results
"""
import boto3
import requests
import json
from datetime import datetime, timedelta
import pytz
from decimal import Decimal

# Load Betfair credentials
with open('betfair-creds.json', 'r') as f:
    creds = json.load(f)

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
    
    print(f"✗ Login failed")
    return None

def get_settled_markets(session_token):
    """Get SETTLED markets from today"""
    url = 'https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/'
    
    uk_tz = pytz.timezone('Europe/London')
    now = datetime.now(uk_tz)
    today_start = now.replace(hour=0, minute=0, second=0)
    
    headers = {
        'X-Application': creds['app_key'],
        'X-Authentication': session_token,
        'Content-Type': 'application/json'
    }
    
    # Get settled markets
    payload = {
        "filter": {
            "eventTypeIds": ["7"],  # Horse Racing
            "marketCountries": ["GB", "IE"],
            "marketTypeCodes": ["WIN"],
            "marketStartTime": {
                "from": today_start.isoformat(),
                "to": now.isoformat()
            }
        },
        "maxResults": 1000,
        "marketProjection": [
            "MARKET_START_TIME",
            "RUNNER_DESCRIPTION",
            "EVENT",
            "MARKET_DESCRIPTION"
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        markets = response.json()
        print(f"✓ Found {len(markets)} markets")
        return markets
    else:
        print(f"✗ Failed to get markets: {response.status_code}")
        return []

def get_market_book(session_token, market_id):
    """Get market book including settled results"""
    url = 'https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/'
    
    headers = {
        'X-Application': creds['app_key'],
        'X-Authentication': session_token,
        'Content-Type': 'application/json'
    }
    
    payload = {
        "marketIds": [market_id]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    return None

# Main
print("="*80)
print("BETFAIR SETTLED RESULTS FETCHER")
print("="*80)

session_token = betfair_login()
if not session_token:
    exit(1)

# Get settled markets
markets = get_settled_markets(session_token)

# Get our picks
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
print(f"✓ Found {len(our_picks)} UI picks\n")

uk_tz = pytz.timezone('Europe/London')
matched_count = 0
wins = 0
losses = 0

for pick in our_picks:
    horse = pick.get('horse', '')
    course = pick.get('course', '').lower()
    race_time_str = pick.get('race_time', '')
    odds = float(pick.get('odds', 0))
    
    if 'T' not in race_time_str:
        continue
    
    race_dt = datetime.fromisoformat(race_time_str.replace('Z', '+00:00'))
    race_uk = race_dt.astimezone(uk_tz)
    time_str = race_uk.strftime('%H:%M')
    
    print(f"\n{time_str} {course.title():15} {horse:25}")
    
    # Find matching market
    best_match = None
    for market in markets:
        event_name = market.get('event', {}).get('name', '').lower()
        market_time = datetime.fromisoformat(market['marketStartTime'].replace('Z', '+00:00')).astimezone(uk_tz)
        market_time_str = market_time.strftime('%H:%M')
        
        # Match by course name and time (within 5 minutes)
        time_diff = abs((market_time - race_uk).total_seconds())
        
        if course in event_name and time_diff < 300:  # 5 minutes tolerance
            best_match = market
            break
    
    if not best_match:
        print(f"  ✗ No matching market found")
        continue
    
    print(f"  ✓ Matched: {best_match['marketName']}")
    
    # Get results
    market_book = get_market_book(session_token, best_match['marketId'])
    
    if not market_book or len(market_book) == 0:
        print(f"  ✗ No market book data")
        continue
    
    book = market_book[0]
    
    if book.get('status') != 'CLOSED':
        print(f"  ⏳ Market not settled yet (status: {book.get('status')})")
        continue
    
    # Find winner
    runners = book.get('runners', [])
    winner_name = None
    our_horse_won = False
    
    for runner in runners:
        if runner.get('status') == 'WINNER':
            # Find runner name
            for r in best_match.get('runners', []):
                if r['selectionId'] == runner['selectionId']:
                    winner_name = r['runnerName']
                    break
            
            if winner_name:
                print(f"  🏆 Winner: {winner_name}")
                
                # Check if our pick won (fuzzy match)
                if (horse.lower() in winner_name.lower() or 
                    winner_name.lower() in horse.lower() or
                    horse.replace(' ', '').lower() == winner_name.replace(' ', '').lower()):
                    our_horse_won = True
                    print(f"  ✅ OUR PICK WON!")
                else:
                    print(f"  ❌ Our pick lost")
                
                break
    
    if not winner_name:
        print(f"  ✗ No winner found in market")
        continue
    
    # Update database
    if our_horse_won:
        outcome = 'win'
        profit = Decimal(str(odds * 30 - 30))  # €30 stake
        wins += 1
    else:
        outcome = 'loss'
        profit = Decimal(str(-30))
        losses += 1
    
    table.update_item(
        Key={
            'bet_date': '2026-02-03',
            'bet_id': pick['bet_id']
        },
        UpdateExpression='SET outcome = :outcome, profit_loss = :pl, actual_winner = :winner, result_updated = :ts',
        ExpressionAttributeValues={
            ':outcome': outcome,
            ':pl': profit,
            ':winner': winner_name,
            ':ts': datetime.now().isoformat()
        }
    )
    
    matched_count += 1

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"Races matched: {matched_count}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")
print(f"{'='*80}")
