import requests
import json
from datetime import datetime, timedelta

# Get credentials
with open('betfair-creds.json', 'r') as f:
    creds = json.load(f)

# Login
cert_file = 'betfair-client.crt'
key_file = 'betfair-client.key'

print("Logging in to Betfair...")
login_response = requests.post(
    'https://identitysso-cert.betfair.com/api/certlogin',
    cert=(cert_file, key_file),
    headers={'X-Application': creds['app_key']},
    data={'username': creds['username'], 'password': creds['password']}
)

session_token = login_response.json()['sessionToken']
print("Logged in successfully\n")

# API setup
api_url = 'https://api.betfair.com/exchange/betting/json-rpc/v1'
headers = {
    'X-Application': creds['app_key'],
    'X-Authentication': session_token,
    'Content-Type': 'application/json'
}

# Get markets from last 24 hours
from_date = datetime.now() - timedelta(hours=24)
to_date = datetime.now() + timedelta(hours=1)

print(f"Fetching race markets from {from_date.strftime('%Y-%m-%d %H:%M')} to {to_date.strftime('%Y-%m-%d %H:%M')}\n")

list_markets_request = {
    'jsonrpc': '2.0',
    'method': 'SportsAPING/v1.0/listMarketCatalogue',
    'params': {
        'filter': {
            'eventTypeIds': ['7'],  # Horse Racing
            'marketStartTime': {
                'from': from_date.isoformat() + 'Z',
                'to': to_date.isoformat() + 'Z'
            },
            'marketTypeCodes': ['WIN'],
            'marketCountries': ['GB', 'IE']  # UK and Ireland only
        },
        'maxResults': 200,
        'marketProjection': ['EVENT', 'MARKET_START_TIME', 'RUNNER_DESCRIPTION']
    },
    'id': 1
}

markets_response = requests.post(api_url, json=list_markets_request, headers=headers)
markets = markets_response.json().get('result', [])

print(f'Found {len(markets)} UK/Ireland race markets\n')

if not markets:
    print("No markets found")
    exit()

# Get market books (results)
market_ids = [m['marketId'] for m in markets]

# Process in batches of 50 (API limit)
all_results = []

for i in range(0, len(market_ids), 50):
    batch_ids = market_ids[i:i+50]
    
    book_request = {
        'jsonrpc': '2.0',
        'method': 'SportsAPING/v1.0/listMarketBook',
        'params': {
            'marketIds': batch_ids,
            'priceProjection': {'priceData': ['SP_AVAILABLE', 'SP_TRADED']}
        },
        'id': 1
    }
    
    book_response = requests.post(api_url, json=book_request, headers=headers)
    market_books = book_response.json().get('result', [])
    
    # Match markets with books
    for market in markets[i:i+50]:
        market_id = market['marketId']
        venue = market.get('event', {}).get('venue', 'Unknown')
        event_name = market.get('event', {}).get('name', 'Unknown')
        start_time = market.get('marketStartTime', 'Unknown')
        
        if start_time != 'Unknown':
            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M')
        else:
            time_str = 'Unknown'
        
        # Find book
        book = None
        for mb in market_books:
            if mb['marketId'] == market_id:
                book = mb
                break
        
        if not book:
            continue
        
        status = book.get('status', 'Unknown')
        
        if status == 'CLOSED':
            # Race finished - get result
            winner_info = None
            runner_details = []
            
            for runner in book.get('runners', []):
                runner_status = runner.get('status', 'Unknown')
                selection_id = runner['selectionId']
                
                # Get runner name from catalog
                runner_name = 'Unknown'
                for cat_runner in market.get('runners', []):
                    if cat_runner['selectionId'] == selection_id:
                        runner_name = cat_runner['runnerName']
                        break
                
                # Get SP
                sp = runner.get('sp', {}).get('actualSP', 'N/A')
                
                runner_details.append({
                    'name': runner_name,
                    'status': runner_status,
                    'sp': sp
                })
                
                if runner_status == 'WINNER':
                    winner_info = {
                        'name': runner_name,
                        'sp': sp,
                        'selection_id': selection_id
                    }
            
            result_entry = {
                'venue': venue,
                'time': time_str,
                'market_id': market_id,
                'status': status,
                'winner': winner_info,
                'all_runners': runner_details
            }
            
            all_results.append(result_entry)

# Display results
print('='*100)
print('RACE RESULTS FROM TODAY')
print('='*100)

settled_count = 0
open_count = 0

for result in all_results:
    if result['status'] == 'CLOSED' and result['winner']:
        settled_count += 1
        print(f"\n{result['venue']} {result['time']}")
        print(f"  WINNER: {result['winner']['name']} @ SP: {result['winner']['sp']}")
        
        # Show placed horses
        placed = [r for r in result['all_runners'] if r['status'] in ['WINNER', 'PLACED']]
        if len(placed) > 1:
            print(f"  PLACED:")
            for r in placed:
                if r['status'] != 'WINNER':
                    print(f"    {r['name']} @ SP: {r['sp']}")

print(f"\n{'='*100}")
print(f"SUMMARY: {settled_count} races with results, {len(markets) - settled_count} races pending/open")
print('='*100)

# Save to file
with open('race_results.json', 'w') as f:
    json.dump(all_results, f, indent=2)

print(f"\nResults saved to race_results.json")
