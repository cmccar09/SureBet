"""
AWS Lambda function to serve betting picks from DynamoDB
Provides REST API for frontend hosted on Amplify
"""
import json
import boto3
from datetime import datetime
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj

def lambda_handler(event, context):
    """Handle API Gateway requests"""
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Get path - handle both API Gateway and Lambda URL formats
    path = event.get('rawPath', event.get('path', ''))
    method = event.get('requestContext', {}).get('http', {}).get('method', event.get('httpMethod', 'GET'))
    
    print(f"Request: {method} {path}")
    print(f"Event keys: {event.keys()}")
    print(f"Path check - 'workflow/run' in path: {'workflow/run' in path}")
    
    try:
        # Route requests - handle both /api/picks and /picks
        if 'picks/today' in path or path.endswith('/today'):
            return get_today_picks(headers)
        elif 'results/today' in path or path.endswith('/results'):
            return check_today_results(headers)
        elif 'workflow/run' in path or 'workflow' in path or path.endswith('/run'):
            return trigger_workflow(headers)
        elif 'picks' in path:
            return get_all_picks(headers)
        elif 'health' in path:
            return get_health(headers)
        elif path == '/':
            # Root path - return API info
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'service': 'Betting Picks API',
                    'endpoints': [
                        '/api/picks/today',
                        '/api/picks',
                        '/api/results/today',
                        '/api/workflow/run',
                        '/api/health'
                    ]
                })
            }
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'error': f'Endpoint not found: {path}'
                })
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

def get_all_picks(headers):
    """Get all picks from DynamoDB"""
    response = table.scan()
    items = response.get('Items', [])
    
    # Convert Decimals to floats
    items = [decimal_to_float(item) for item in items]
    
    # Sort by timestamp descending
    items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'success': True,
            'picks': items,
            'count': len(items)
        })
    }

def get_today_picks(headers):
    """Get today's picks only"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    response = table.scan(
        FilterExpression='#d = :today',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={':today': today}
    )
    
    items = response.get('Items', [])
    items = [decimal_to_float(item) for item in items]
    items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'success': True,
            'picks': items,
            'count': len(items),
            'date': today
        })
    }

def get_health(headers):
    """Health check endpoint"""
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'status': 'ok',
            'service': 'betting-picks-api',
            'timestamp': datetime.now().isoformat()
        })
    }

def check_today_results(headers):
    """Check results for today's picks by fetching from Betfair"""
    import requests
    import os
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get today's picks
    response = table.scan(
        FilterExpression='#d = :today',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={':today': today}
    )
    
    picks = response.get('Items', [])
    picks = [decimal_to_float(item) for item in picks]
    
    # Debug logging
    print(f"Total picks retrieved: {len(picks)}")
    print(f"Sample ROIs: {[float(p.get('roi', 0)) for p in picks[:5]]}")
    
    # Filter for positive ROI picks only
    positive_roi_picks = [pick for pick in picks if float(pick.get('roi', 0)) > 0]
    
    print(f"Positive ROI picks: {len(positive_roi_picks)}")
    print(f"BEFORE filter - picks variable length: {len(picks)}")
    
    if not positive_roi_picks:
        print("NO POSITIVE ROI PICKS - returning empty")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': f'No positive ROI picks for today (checked {len(picks)} total picks)',
                'picks': [],
                'results': [],
                'total_picks_today': len(picks)
            })
        }
    
    # Use only positive ROI picks for results checking
    picks = positive_roi_picks
    print(f"AFTER filter - picks variable length: {len(picks)}")
    print(f"Proceeding with {len(picks)} positive ROI picks")
    
    # Load Betfair credentials from environment or Secrets Manager
    session_token = os.environ.get('BETFAIR_SESSION_TOKEN', '')
    app_key = os.environ.get('BETFAIR_APP_KEY', '')
    
    if not session_token or not app_key:
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Betfair credentials not configured - results unavailable',
                'picks': picks,
                'results': [],
                'error': 'Configure BETFAIR_SESSION_TOKEN and BETFAIR_APP_KEY environment variables'
            })
        }
    
    # Extract unique market IDs
    market_ids = list(set([str(pick.get('market_id', '')) for pick in picks if pick.get('market_id')]))
    
    if not market_ids:
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'No market IDs found in picks',
                'picks': picks,
                'results': []
            })
        }
    
    # Fetch market results from Betfair
    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/"
    betfair_headers = {
        "X-Application": app_key,
        "X-Authentication": session_token,
        "Content-Type": "application/json"
    }
    
    all_results = []
    
    # Process in batches of 10
    for i in range(0, len(market_ids), 10):
        batch = market_ids[i:i+10]
        payload = {
            "marketIds": batch,
            "priceProjection": {"priceData": ["EX_BEST_OFFERS"]},
        }
        
        try:
            resp = requests.post(url, headers=betfair_headers, json=payload, timeout=10)
            resp.raise_for_status()
            market_data = resp.json()
            
            # Parse results
            for market in market_data:
                market_id = market.get('marketId')
                status = market.get('status')
                
                for runner in market.get('runners', []):
                    selection_id = str(runner.get('selectionId'))
                    runner_status = runner.get('status', '')
                    
                    all_results.append({
                        'market_id': market_id,
                        'selection_id': selection_id,
                        'market_status': status,
                        'runner_status': runner_status,
                        'is_winner': runner_status == 'WINNER',
                        'is_placed': runner_status in ['WINNER', 'PLACED'],
                        'last_price': runner.get('lastPriceTraded', 0)
                    })
        except Exception as e:
            print(f"Error fetching batch: {e}")
            continue
    
    # Match picks with results
    picks_with_results = []
    wins = 0
    places = 0
    losses = 0
    pending = 0
    total_stake = 0
    total_return = 0
    
    for pick in picks:
        pick_market_id = str(pick.get('market_id', ''))
        pick_selection_id = str(pick.get('selection_id', ''))
        stake = float(pick.get('stake', 2.0))
        odds = float(pick.get('odds', 0))
        bet_type = pick.get('bet_type', 'WIN').upper()
        
        # Find matching result
        result = next((r for r in all_results 
                      if r['market_id'] == pick_market_id 
                      and r['selection_id'] == pick_selection_id), None)
        
        pick_result = pick.copy()
        
        if result:
            pick_result['result'] = result
            market_status = result['market_status']
            
            if market_status in ['CLOSED', 'SETTLED']:
                if result['is_winner']:
                    wins += 1
                    pick_result['outcome'] = 'WON'
                    if bet_type == 'WIN':
                        total_return += stake * odds
                    else:  # EW
                        ew_fraction = float(pick.get('ew_fraction', 0.2))
                        total_return += (stake/2) * odds + (stake/2) * (1 + (odds-1) * ew_fraction)
                elif result['is_placed'] and bet_type == 'EW':
                    places += 1
                    pick_result['outcome'] = 'PLACED'
                    ew_fraction = float(pick.get('ew_fraction', 0.2))
                    total_return += (stake/2) * (1 + (odds-1) * ew_fraction)
                else:
                    losses += 1
                    pick_result['outcome'] = 'LOST'
            else:
                pending += 1
                pick_result['outcome'] = 'PENDING'
        else:
            pending += 1
            pick_result['outcome'] = 'NO_RESULT'
        
        total_stake += stake
        picks_with_results.append(pick_result)
    
    profit = total_return - total_stake
    roi = (profit / total_stake * 100) if total_stake > 0 else 0
    
    summary = {
        'total_picks': len(picks),
        'wins': wins,
        'places': places,
        'losses': losses,
        'pending': pending,
        'total_stake': round(total_stake, 2),
        'total_return': round(total_return, 2),
        'profit': round(profit, 2),
        'roi': round(roi, 1),
        'strike_rate': round((wins / (wins + losses) * 100) if (wins + losses) > 0 else 0, 1)
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'success': True,
            'date': today,
            'summary': summary,
            'picks': picks_with_results,
            'debug_timestamp': datetime.now().isoformat(),
            'total_picks_today': len(positive_roi_picks)
        })
    }

def trigger_workflow(headers):
    """Trigger the betting workflow Lambda to generate new picks"""
    import boto3
    
    lambda_client = boto3.client('lambda', region_name='eu-west-1')
    
    try:
        # Invoke the workflow Lambda asynchronously
        response = lambda_client.invoke(
            FunctionName='betting-workflow',
            InvocationType='Event',  # Async invocation
            Payload=json.dumps({
                'source': 'api-trigger',
                'trigger': 'manual-refresh'
            })
        )
        
        return {
            'statusCode': 202,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Workflow triggered successfully',
                'status': 'processing',
                'info': 'New picks will be generated in ~60-90 seconds. Refresh picks to see updates.'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'message': 'Failed to trigger workflow. Make sure betting-workflow Lambda exists and API has invoke permissions.'
            })
        }

