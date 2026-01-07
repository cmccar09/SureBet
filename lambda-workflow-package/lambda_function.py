#!/usr/bin/env python3
"""
Lambda handler for scheduled betting workflow
Runs every 2 hours to fetch odds, generate picks, and store in DynamoDB
Includes learning layer and bankroll management
"""

import os
import json
import boto3
import requests
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
secretsmanager = boto3.client('secretsmanager', region_name='eu-west-1')

# Import learning layer functions
try:
    from lambda_learning_layer import (
        calculate_bet_stake,
        get_current_bankroll,
        analyze_recent_performance,
        adjust_selection_confidence
    )
    LEARNING_ENABLED = True
except ImportError:
    print("Learning layer not available - stakes will use default values")
    LEARNING_ENABLED = False

def get_betfair_certificates():
    """Retrieve Betfair SSL certificates from Secrets Manager"""
    try:
        response = secretsmanager.get_secret_value(SecretId='betfair-ssl-certificate')
        secret = json.loads(response['SecretString'])
        
        # Write to /tmp (Lambda's writable directory)
        cert_path = '/tmp/betfair-client.crt'
        key_path = '/tmp/betfair-client.key'
        
        with open(cert_path, 'w') as f:
            f.write(secret['certificate'])
        
        with open(key_path, 'w') as f:
            f.write(secret['private_key'])
        
        print("✓ SSL certificates loaded from Secrets Manager")
        return cert_path, key_path
        
    except secretsmanager.exceptions.ResourceNotFoundException:
        print("WARNING: SSL certificates not found in Secrets Manager")
        print("Please upload certificates: aws secretsmanager create-secret --name betfair-ssl-certificate")
        return None, None
    except Exception as e:
        print(f"Error loading certificates: {e}")
        return None, None

def convert_floats(obj):
    """Convert floats to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj

def fetch_betfair_odds():
    """Fetch live horse racing odds from Betfair"""
    print("Fetching Betfair odds...")
    
    # Load credentials from environment
    creds = {
        'username': os.environ.get('BETFAIR_USERNAME'),
        'password': os.environ.get('BETFAIR_PASSWORD'),
        'app_key': os.environ.get('BETFAIR_APP_KEY'),
        'session_token': os.environ.get('BETFAIR_SESSION_TOKEN', '')
    }
    
    if not all([creds['username'], creds['password'], creds['app_key']]):
        raise Exception("ERROR: Betfair credentials not configured in Lambda environment variables")
    
    # Try to refresh session token if needed
    if not creds['session_token']:
        print("Authenticating with Betfair...")
        session_token = refresh_betfair_session(creds)
        if session_token:
            creds['session_token'] = session_token
        else:
            raise Exception("ERROR: Betfair authentication failed. Check credentials and SSL certificates in Secrets Manager.")
    
    # Fetch live markets
    try:
        url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/"
        headers = {
            "X-Application": creds['app_key'],
            "X-Authentication": creds['session_token'],
            "Content-Type": "application/json"
        }
        
        now = datetime.utcnow()
        to_time = now + timedelta(hours=24)
        
        payload = {
            "filter": {
                "eventTypeIds": ["7"],  # Horse Racing
                "marketCountries": ["GB", "IE"],
                "marketTypeCodes": ["WIN"],
                "marketStartTime": {
                    "from": now.isoformat() + "Z",
                    "to": to_time.isoformat() + "Z"
                }
            },
            "maxResults": 50,
            "marketProjection": ["RUNNER_DESCRIPTION", "EVENT", "MARKET_START_TIME"]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            markets = response.json()
            
            # Get odds for each market
            races = []
            for market in markets[:10]:  # Limit to 10 races
                market_id = market['marketId']
                
                # Fetch odds
                odds_url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/"
                odds_payload = {
                    "marketIds": [market_id],
                    "priceProjection": {"priceData": ["EX_BEST_OFFERS"]}
                }
                
                odds_response = requests.post(odds_url, headers=headers, json=odds_payload, timeout=30)
                
                if odds_response.status_code == 200:
                    odds_data = odds_response.json()
                    if odds_data and len(odds_data) > 0:
                        market_book = odds_data[0]
                        
                        runners = []
                        for i, runner_catalog in enumerate(market.get('runners', [])):
                            runner_id = runner_catalog['selectionId']
                            
                            # Find matching runner in market book
                            runner_book = next((r for r in market_book.get('runners', []) if r['selectionId'] == runner_id), None)
                            
                            if runner_book and runner_book.get('status') == 'ACTIVE':
                                best_odds = runner_book.get('ex', {}).get('availableToBack', [])
                                odds = best_odds[0]['price'] if best_odds else 0
                                
                                runners.append({
                                    "name": runner_catalog.get('runnerName', f'Runner {i+1}'),
                                    "selection_id": str(runner_id),
                                    "odds": odds
                                })
                        
                        races.append({
                            "market_id": market_id,
                            "market_name": market.get('marketName', 'Unknown'),
                            "venue": market.get('event', {}).get('venue', 'Unknown'),
                            "race_time": market.get('marketStartTime'),
                            "runners": runners
                        })
            
            print(f"Fetched {len(races)} races from Betfair")
            return races
        else:
            raise Exception(f"Betfair API error {response.status_code}: {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error connecting to Betfair: {e}")
    except Exception as e:
        raise Exception(f"Error fetching Betfair data: {e}")

def refresh_betfair_session(creds):
    """Refresh Betfair session token using SSL certificate authentication"""
    try:
        # Get SSL certificates
        cert_path, key_path = get_betfair_certificates()
        
        if cert_path and key_path:
            # Certificate-based authentication (NO username/password needed)
            url = "https://identitysso-cert.betfair.com/api/certlogin"
            print("Using certificate-based authentication")
            
            headers = {
                'X-Application': creds['app_key'],
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Certificate auth - no username/password in body
            data = {
                'username': creds['username']  # Only username required with cert
            }
            
            response = requests.post(
                url, 
                headers=headers, 
                data=data, 
                cert=(cert_path, key_path),
                timeout=30
            )
        else:
            # No certificates - use standard auth (will fail from Lambda)
            url = "https://identitysso.betfair.com/api/login"
            print("WARNING: No certificates - using standard authentication")
            
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
                timeout=30
            )
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
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            
            # Handle both response formats
            if result.get('loginStatus') == 'SUCCESS':
                token = result.get('sessionToken')
            elif result.get('status') == 'SUCCESS':
                token = result.get('token') or result.get('sessionToken')
            else:
                token = None
            
            if token:
                print(f"✓ Betfair authentication successful")
                return token
        
        print(f"❌ Betfair authentication failed: HTTP {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None
        
    except Exception as e:
        print(f"❌ Error during Betfair authentication: {e}")
        return None

# Mock data removed - system will only use real Betfair data
# If authentication fails, Lambda will error (not silently use fake data)

def load_prompt():
    """Load betting strategy prompt"""
    # Try to load from file, fallback to default
    try:
        with open('prompt.txt', 'r') as f:
            return f.read()
    except:
        return """You are an expert horse racing analyst. Analyze the provided races and return your top 5 betting opportunities.

For each selection provide:
- horse: runner name
- course: venue
- race_time: start time
- odds: decimal odds
- bet_type: 'WIN' or 'EW' (each-way)
- p_win: win probability (0-1 decimal)
- p_place: place probability for EW bets (0-1 decimal)
- ew_places: number of places paid for EW (typically 3-4)
- ew_fraction: place fraction for EW (typically 0.2 or 0.25)
- roi: expected return on investment as decimal (e.g., 0.15 for 15%)
- ev: expected value as decimal
- confidence: confidence score 0-100
- why_now: brief explanation
- tags: array of relevant tags

Return a JSON array with exactly 5 selections."""

def call_claude_bedrock(prompt_text, race_data):
    """Call Claude via AWS Bedrock"""
    print("Calling Claude via Bedrock...")
    
    # Format race data
    races_text = ""
    for i, race in enumerate(race_data, 1):
        races_text += f"\nRace {i}: {race['market_name']} at {race['venue']}\n"
        races_text += f"Start Time: {race['race_time']}\n"
        races_text += f"Market ID: {race['market_id']}\n"
        races_text += "Runners:\n"
        for runner in race['runners']:
            races_text += f"  - {runner['name']}: {runner['odds']} (ID: {runner['selection_id']})\n"
    
    full_prompt = f"{prompt_text}\n\nRACE DATA:\n{races_text}\n\nReturn exactly 5 selections as JSON array."
    
    try:
        # Use Claude Sonnet 4 via Bedrock
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": full_prompt}]
        })
        
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Extract JSON from response
        start = content.find('[')
        end = content.rfind(']') + 1
        if start >= 0 and end > start:
            selections = json.loads(content[start:end])
            print(f"Claude returned {len(selections)} selections")
            return selections
        else:
            print("No valid JSON found in response")
            return []
            
    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return []

def store_picks_in_dynamodb(picks, metadata=None):
    """Store picks in DynamoDB"""
    table_name = os.environ.get("SUREBET_DDB_TABLE", "SureBetBets")
    table = dynamodb.Table(table_name)
    
    print(f"Storing {len(picks)} picks in DynamoDB...")
    
    timestamp = datetime.utcnow().isoformat()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    for pick in picks:
        # Create unique bet ID
        bet_id = f"{pick.get('race_time','')}_{pick.get('horse','')}"
        
        item = {
            "bet_id": bet_id,
            "timestamp": timestamp,
            "date": date_str,
            "horse": pick.get("horse", "Unknown"),
            "course": pick.get("course", "Unknown"),
            "race_time": pick.get("race_time"),
            "market_id": pick.get("market_id", ""),
            "selection_id": str(pick.get("selection_id", "")),
            "odds": convert_floats(pick.get("odds", 0)),
            "bet_type": pick.get("bet_type", "WIN"),
            "p_win": convert_floats(pick.get("p_win", 0)),
            "p_place": convert_floats(pick.get("p_place", 0)),
            "ew_places": int(pick.get("ew_places", 0)),
            "ew_fraction": convert_floats(pick.get("ew_fraction", 0)),
            "roi": convert_floats(pick.get("roi", 0)),
            "ev": convert_floats(pick.get("ev", 0)),
            "confidence": convert_floats(pick.get("confidence", 0)),
            "why_now": pick.get("why_now", ""),
            "tags": pick.get("tags", []),
            "market_name": pick.get("market_name", ""),
            "stake": convert_floats(pick.get("stake", 0)),
            "bankroll": convert_floats(pick.get("bankroll", 1000)),
            "expected_roi": convert_floats(pick.get("expected_roi", 0)),
            "result": pick.get("result", "pending"),
            "created_by": "lambda-scheduled",
            "status": "active"
        }
        
        # Add metadata if provided
        if metadata:
            item["metadata"] = convert_floats(metadata)
        
        table.put_item(Item=item)
        print(f"  Stored: {pick.get('horse')} at {pick.get('course')}")
    
    print(f"Successfully stored {len(picks)} picks")

def lambda_handler(event, context):
    """Main Lambda handler - runs on schedule"""
    try:
        print("="*60)
        print("BETTING WORKFLOW LAMBDA EXECUTION")
        print(f"Time: {datetime.utcnow().isoformat()}")
        print("="*60)
        
        # Step 0: Analyze recent performance and get current bankroll
        if LEARNING_ENABLED:
            print("\n=== LEARNING LAYER ===")
            recent_perf = analyze_recent_performance(days=7)
            current_bankroll = get_current_bankroll()
        else:
            recent_perf = None
            current_bankroll = 1000.0  # Default
        
        # Step 1: Fetch odds
        races = fetch_betfair_odds()
        print(f"\nFetched {len(races)} races")
        
        if not races:
            print("No races available, exiting")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No races available"})
            }
        
        # Step 2: Load prompt
        prompt_text = load_prompt()
        
        # Step 3: Generate picks
        picks = call_claude_bedrock(prompt_text, races[:5])  # Limit to 5 races
        
        if not picks:
            print("No picks generated")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No picks generated"})
            }
        
        # Step 4: Apply learning and calculate stakes
        print("\n=== CALCULATING STAKES ===")
        for pick in picks:
            # Adjust confidence based on recent performance
            if LEARNING_ENABLED and recent_perf:
                pick = adjust_selection_confidence(pick, recent_perf)
            
            # Calculate optimal stake
            if LEARNING_ENABLED:
                odds = float(pick.get('odds', 0))
                p_win = float(pick.get('p_win', 0))
                p_place = float(pick.get('p_place', p_win * 2.5))
                bet_type = pick.get('bet_type', 'WIN')
                ew_fraction = float(pick.get('ew_fraction', 0.2))
                
                stake = calculate_bet_stake(
                    odds=odds,
                    p_win=p_win,
                    bankroll=current_bankroll,
                    bet_type=bet_type,
                    p_place=p_place,
                    ew_fraction=ew_fraction
                )
                
                pick['stake'] = stake
                pick['bankroll'] = current_bankroll
                
                # Calculate expected ROI
                if bet_type == 'WIN':
                    expected_return = p_win * odds * stake
                    expected_roi = ((expected_return - stake) / stake * 100)
                else:  # EW
                    win_return = p_win * odds * stake
                    place_return = p_place * (1 + (odds - 1) * ew_fraction) * stake
                    expected_return = (win_return + place_return) / 2
                    expected_roi = ((expected_return - stake) / stake * 100)
                
                pick['expected_roi'] = round(expected_roi, 1)
                
                print(f"  {pick.get('horse')}: €{stake} stake (expected ROI: {expected_roi:+.1f}%)")
            else:
                # Default stake
                pick['stake'] = 10.0
                pick['bankroll'] = current_bankroll
        
        # Step 5: Store in DynamoDB
        metadata = {
            "race_count": len(races),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "lambda-scheduled",
            "bankroll": current_bankroll
        }
        if recent_perf:
            metadata['recent_performance'] = recent_perf
        
        store_picks_in_dynamodb(picks, metadata)
        
        print("\n" + "="*60)
        print("WORKFLOW COMPLETE")
        print(f"Generated and stored {len(picks)} picks")
        print("="*60)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "picks_generated": len(picks),
                "races_analyzed": len(races),
                "timestamp": datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
