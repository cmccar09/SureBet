# SureBet Lambda: fetch odds, call Claude 4.5, store bets in DynamoDB

import os
import json
import boto3
import datetime
import requests

# Import automated betting modules
try:
    from paddy_power_betting import auto_place_bets, determine_bet_type, calculate_stake
    from betfair_odds_fetcher import get_live_betfair_races
    BETTING_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Betting modules not available: {e}")
    BETTING_MODULES_AVAILABLE = False

# Learning Configuration
ENABLE_LEARNING = os.environ.get('ENABLE_LEARNING', 'true').lower() == 'true'
ALLOW_MULTIPLE_HORSES_PER_RACE = os.environ.get('ALLOW_MULTIPLE_HORSES', 'true').lower() == 'true'

# --- Free Odds API integration ---
def fetch_betfair_odds(sport='horse_racing'):
    """
    Fetch live odds from Betfair for various sports
    Filters events to optimal betting window (15 mins - 24 hours)
    Supports: horse_racing, darts, cricket, rugby, football
    Priority: Free sources with timing analysis > Mock Data
    """
    # Try Betfair API with automated session refresh
    if BETTING_MODULES_AVAILABLE:
        print(f"Fetching live Betfair odds ({sport})...")
        from betfair_odds_fetcher import get_live_betfair_events
        try:
            events = get_live_betfair_events(sport)
            if events:
                print(f"Successfully fetched {len(events)} Betfair events in betting window")
                return events
            else:
                print(f"No Betfair events found for {sport}, using mock data...")
        except Exception as e:
            print(f"Betfair fetch error: {e}")
            print("Falling back to mock data...")
    
    # Realistic mock data - simulates actual events for different sports
    print(f"Using realistic mock data for {sport}")
    now = datetime.datetime.utcnow()
    import random
    
    # Sport-specific mock data
    if sport == 'horse_racing':
        courses = ["Cheltenham", "Ascot", "Newmarket", "Kempton Park", "Leopardstown", "The Curragh"]
        prefixes = ["Royal", "Golden", "Thunder", "Speed", "Lucky", "Silver", "Dark", "Noble", "Mighty", "Swift"]
        suffixes = ["Flash", "Arrow", "Bolt", "Demon", "Strike", "Star", "King", "Spirit", "Dream", "Runner"]
    elif sport == 'darts':
        courses = ["Alexandra Palace", "Winter Gardens", "Ally Pally"]
        prefixes = ["Michael", "Peter", "Gary", "Phil", "James", "Rob", "Luke", "Gerwyn", "Nathan", "Danny"]
        suffixes = ["Smith", "Wright", "Anderson", "Taylor", "Wade", "Cross", "Humphries", "Price", "Aspinall", "Noppert"]
    elif sport == 'cricket':
        courses = ["Lord's", "The Oval", "Old Trafford", "Edgbaston", "Headingley"]
        prefixes = ["England", "Australia", "India", "Pakistan", "New Zealand", "South Africa"]
        suffixes = ["Warriors", "Knights", "Riders", "Royals", "Super Kings", "Indians"]
    elif sport == 'rugby':
        courses = ["Twickenham", "Murrayfield", "Principality Stadium", "Aviva Stadium"]
        prefixes = ["England", "Ireland", "Wales", "Scotland", "France", "Italy"]
        suffixes = ["", "XV", "Rugby"]
    else:  # football
        courses = ["Premier League", "Championship", "La Liga", "Serie A", "Bundesliga"]
        prefixes = ["Arsenal", "Man United", "Liverpool", "Chelsea", "Man City", "Tottenham", "Newcastle", "Brighton"]
        suffixes = ["", "FC", "United"]
    
    events = []
    event_times = [35, 50, 75, 105, 145]  # Mix of optimal and early timings
    
    for i, mins in enumerate(event_times[:3]):  # Generate 3 events
        num_selections = random.randint(2, 8) if sport == 'horse_racing' else random.randint(2, 3)
        selections = []
        
        for j in range(num_selections):
            name = f"{random.choice(prefixes)} {random.choice(suffixes)}" if suffixes[0] else random.choice(prefixes)
            odds = round(random.uniform(1.5 if sport != 'horse_racing' else 2.5, 12.0), 2)
            selections.append({
                "name": name.strip(),
                "selectionId": 10000 + (i * 100) + j,
                "odds": odds
            })
        
        # Calculate timing
        if mins > 120:
            timing_quality = "TOO_EARLY"
            confidence_adj = 0.7
            advice = "Event is >2 hours away, reducing confidence by 30%"
        elif mins >= 90:
            timing_quality = "EARLY"
            confidence_adj = 0.85
            advice = "Slightly early - odds may still fluctuate"
        elif mins >= 30:
            timing_quality = "OPTIMAL"
            confidence_adj = 1.0
            advice = "Optimal betting window (30-90 mins before event)"
        else:
            timing_quality = "GOOD"
            confidence_adj = 0.9
            advice = "Good timing - odds are settling"
        
        event = {
            "market_id": f"1.{234567 + i}",
            "event_time": (now + datetime.timedelta(minutes=mins)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "venue": random.choice(courses),
            "sport": sport,
            "selections": selections,
            "timing": {
                "minutes_to_event": mins,
                "timing_quality": timing_quality,
                "confidence_adjustment": confidence_adj,
                "timing_advice": advice
            }
        }
        
        # Add special markets for darts, rugby, and cricket
        if sport == 'darts':
            event["markets"] = {
                "Match Odds": {
                    "market_id": f"1.{234567 + i}",
                    "selections": selections
                },
                "Total 180s Over/Under 3.5": {
                    "market_id": f"1.{234600 + i}",
                    "selections": [
                        {"name": "Over 3.5", "odds": round(random.uniform(1.8, 2.3), 2)},
                        {"name": "Under 3.5", "odds": round(random.uniform(1.7, 2.2), 2)}
                    ]
                },
                "Total 180s Over/Under 6.5": {
                    "market_id": f"1.{234700 + i}",
                    "selections": [
                        {"name": "Over 6.5", "odds": round(random.uniform(2.5, 4.0), 2)},
                        {"name": "Under 6.5", "odds": round(random.uniform(1.3, 1.6), 2)}
                    ]
                },
                "Correct Score": {
                    "market_id": f"1.{234800 + i}",
                    "selections": [
                        {"name": "3-0", "odds": round(random.uniform(4.0, 7.0), 2)},
                        {"name": "3-1", "odds": round(random.uniform(4.0, 6.0), 2)},
                        {"name": "3-2", "odds": round(random.uniform(4.5, 7.0), 2)},
                        {"name": "0-3", "odds": round(random.uniform(5.0, 10.0), 2)},
                        {"name": "1-3", "odds": round(random.uniform(5.0, 8.0), 2)},
                        {"name": "2-3", "odds": round(random.uniform(5.0, 9.0), 2)}
                    ]
                }
            }
        elif sport == 'rugby':
            event["markets"] = {
                "Match Odds": {
                    "market_id": f"1.{234567 + i}",
                    "selections": selections
                },
                "Total Points Over/Under 45.5": {
                    "market_id": f"1.{234600 + i}",
                    "selections": [
                        {"name": "Over 45.5", "odds": round(random.uniform(1.8, 2.2), 2)},
                        {"name": "Under 45.5", "odds": round(random.uniform(1.7, 2.1), 2)}
                    ]
                },
                "Handicap": {
                    "market_id": f"1.{234700 + i}",
                    "selections": [
                        {"name": f"{selections[0]['name']} -7.5", "odds": round(random.uniform(1.8, 2.3), 2)},
                        {"name": f"{selections[1]['name'] if len(selections) > 1 else 'Team 2'} +7.5", "odds": round(random.uniform(1.7, 2.2), 2)}
                    ]
                },
                "First Try Scorer": {
                    "market_id": f"1.{234800 + i}",
                    "selections": [
                        {"name": "Player A", "odds": round(random.uniform(5.0, 9.0), 2)},
                        {"name": "Player B", "odds": round(random.uniform(6.0, 10.0), 2)},
                        {"name": "Player C", "odds": round(random.uniform(7.0, 12.0), 2)},
                        {"name": "Player D", "odds": round(random.uniform(8.0, 15.0), 2)}
                    ]
                },
                "Winning Margin": {
                    "market_id": f"1.{234900 + i}",
                    "selections": [
                        {"name": "1-12 Points", "odds": round(random.uniform(3.0, 5.0), 2)},
                        {"name": "13+ Points", "odds": round(random.uniform(3.5, 6.0), 2)},
                        {"name": "Draw", "odds": round(random.uniform(15.0, 25.0), 2)}
                    ]
                }
            }
        elif sport == 'cricket':
            event["markets"] = {
                "Match Odds": {
                    "market_id": f"1.{234567 + i}",
                    "selections": selections
                },
                "Total Runs Over/Under 280.5": {
                    "market_id": f"1.{234600 + i}",
                    "selections": [
                        {"name": "Over 280.5", "odds": round(random.uniform(1.8, 2.3), 2)},
                        {"name": "Under 280.5", "odds": round(random.uniform(1.7, 2.2), 2)}
                    ]
                },
                "Top Batsman": {
                    "market_id": f"1.{234700 + i}",
                    "selections": [
                        {"name": "Batsman A", "odds": round(random.uniform(4.0, 7.0), 2)},
                        {"name": "Batsman B", "odds": round(random.uniform(5.0, 8.0), 2)},
                        {"name": "Batsman C", "odds": round(random.uniform(6.0, 10.0), 2)},
                        {"name": "Batsman D", "odds": round(random.uniform(7.0, 12.0), 2)}
                    ]
                },
                "Top Bowler": {
                    "market_id": f"1.{234800 + i}",
                    "selections": [
                        {"name": "Bowler A", "odds": round(random.uniform(4.5, 8.0), 2)},
                        {"name": "Bowler B", "odds": round(random.uniform(5.5, 9.0), 2)},
                        {"name": "Bowler C", "odds": round(random.uniform(6.5, 11.0), 2)}
                    ]
                },
                "Method of Dismissal - 1st Wicket": {
                    "market_id": f"1.{234900 + i}",
                    "selections": [
                        {"name": "Caught", "odds": round(random.uniform(2.0, 3.0), 2)},
                        {"name": "Bowled", "odds": round(random.uniform(3.5, 5.0), 2)},
                        {"name": "LBW", "odds": round(random.uniform(4.0, 6.0), 2)},
                        {"name": "Run Out", "odds": round(random.uniform(6.0, 10.0), 2)}
                    ]
                }
            }
        
        events.append(event)
    
    return events

    # List UK/IRE horse racing markets in next 24 hours
    now = datetime.datetime.utcnow()
    to_time = now + datetime.timedelta(hours=24)
    market_filter = {
        "filter": {
            "eventTypeIds": ["7"],  # Horse Racing
            "marketCountries": ["GB", "IE"],
            "marketTypeCodes": ["WIN"],
            "marketStartTime": {
                "from": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": to_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        },
        "maxResults": "100",
        "marketProjection": ["RUNNER_METADATA", "MARKET_START_TIME", "EVENT"]
    }
    headers = {
        "X-Application": BETFAIR_APP_KEY,
        "X-Authentication": BETFAIR_SESSION,
        "Content-Type": "application/json"
    }
    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/"
    resp = requests.post(url, headers=headers, data=json.dumps(market_filter))
    if resp.status_code != 200:
        raise Exception(f"Betfair API error: {resp.status_code} {resp.text}")
    markets = resp.json()
    # For each market, get odds (listMarketBook)
    market_ids = [m["marketId"] for m in markets]
    if not market_ids:
        return []
    book_req = {
        "marketIds": market_ids,
        "priceProjection": {"priceData": ["EX_BEST_OFFERS"]}
    }
    book_url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/"
    book_resp = requests.post(book_url, headers=headers, data=json.dumps(book_req))
    if book_resp.status_code != 200:
        raise Exception(f"Betfair API error: {book_resp.status_code} {book_resp.text}")
    books = {b["marketId"]: b for b in book_resp.json()}
    # Structure output
    races = []
    for m in markets:
        market_id = m["marketId"]
        event = m.get("event", {})
        course = event.get("venue", "")
        race_time = m.get("marketStartTime", "")
        runners = []
        book = books.get(market_id, {})
        for r in m.get("runners", []):
            sel_id = r["selectionId"]
            name = r["runnerName"]
            # Find best back price
            best_back = None
            if book and "runners" in book:
                for br in book["runners"]:
                    if br["selectionId"] == sel_id:
                        offers = br.get("ex", {}).get("availableToBack", [])
                        if offers:
                            best_back = offers[0]["price"]
                        break
            runners.append({"name": name, "selectionId": sel_id, "odds": best_back})
        races.append({
            "market_id": market_id,
            "race_time": race_time,
            "course": course,
            "runners": runners
        })
    return races

def fetch_past_performance():
    """
    Fetch recent bets from DynamoDB to learn from past performance.
    Returns analysis of what worked and what didn't.
    """
    try:
        table_name = os.environ.get("SUREBET_DDB_TABLE", "SureBetBets")
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        
        # Get bets from last 7 days
        seven_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        response = table.scan(
            FilterExpression="#d >= :start_date AND attribute_exists(outcome)",
            ExpressionAttributeNames={"#d": "date"},
            ExpressionAttributeValues={":start_date": seven_days_ago}
        )
        
        bets_with_outcomes = response.get('Items', [])
        
        if not bets_with_outcomes:
            return None
        
        # Analyze performance
        total_bets = len(bets_with_outcomes)
        won = sum(1 for b in bets_with_outcomes if b.get('outcome') == 'won')
        placed = sum(1 for b in bets_with_outcomes if b.get('outcome') in ['placed', 'won'])
        lost = sum(1 for b in bets_with_outcomes if b.get('outcome') == 'lost')
        
        # Analyze patterns in losses
        loss_patterns = []
        for bet in bets_with_outcomes:
            if bet.get('outcome') == 'lost':
                loss_patterns.append({
                    'horse': bet.get('horse'),
                    'odds': float(bet.get('odds', 0)),
                    'confidence': float(bet.get('confidence', 0)),
                    'bet_type': bet.get('bet_type'),
                    'why_lost': bet.get('learning_notes', 'No analysis available')
                })
        
        # Analyze patterns in wins
        win_patterns = []
        for bet in bets_with_outcomes:
            if bet.get('outcome') == 'won':
                win_patterns.append({
                    'horse': bet.get('horse'),
                    'odds': float(bet.get('odds', 0)),
                    'confidence': float(bet.get('confidence', 0)),
                    'bet_type': bet.get('bet_type'),
                    'actual_position': bet.get('actual_position', 1)
                })
        
        analysis = {
            'total_bets': total_bets,
            'won': won,
            'placed': placed,
            'lost': lost,
            'win_rate': round(won / total_bets * 100, 1) if total_bets > 0 else 0,
            'place_rate': round(placed / total_bets * 100, 1) if total_bets > 0 else 0,
            'loss_patterns': loss_patterns[:5],  # Top 5 recent losses
            'win_patterns': win_patterns[:5],  # Top 5 recent wins
            'avg_losing_odds': round(sum(p['odds'] for p in loss_patterns) / len(loss_patterns), 2) if loss_patterns else 0,
            'avg_winning_odds': round(sum(p['odds'] for p in win_patterns) / len(win_patterns), 2) if win_patterns else 0,
            'last_updated': datetime.datetime.utcnow().isoformat()
        }
        
        return analysis
        
    except Exception as e:
        print(f"Error fetching past performance: {e}")
        return None

def update_bet_outcome(bet_id, outcome, actual_position, learning_notes):
    """
    Update a bet in DynamoDB with race results for continuous learning.
    Called manually or via automated result fetching.
    """
    try:
        table_name = os.environ.get("SUREBET_DDB_TABLE", "SureBetBets")
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        
        table.update_item(
            Key={'bet_id': bet_id},
            UpdateExpression="SET outcome = :outcome, actual_position = :pos, learning_notes = :notes, feedback_processed = :processed",
            ExpressionAttributeValues={
                ':outcome': outcome,
                ':pos': actual_position,
                ':notes': learning_notes,
                ':processed': True
            }
        )
        print(f"Updated bet {bet_id} with outcome: {outcome}")
        return True
    except Exception as e:
        print(f"Error updating bet outcome: {e}")
        return False

def filter_multiple_horses_per_race(predictions):
    """
    Allow multiple horses from the same race if one is Win and another is Each Way.
    Returns filtered list maintaining best Win and best Each Way per race.
    """
    if not ALLOW_MULTIPLE_HORSES_PER_RACE:
        # Original behavior: one horse per race
        race_map = {}
        for pred in predictions:
            race_key = f"{pred.get('race_time')}_{pred.get('course')}"
            if race_key not in race_map:
                race_map[race_key] = pred
            elif pred.get('confidence', 0) > race_map[race_key].get('confidence', 0):
                race_map[race_key] = pred
        return list(race_map.values())
    
    # New behavior: Allow Win + Each Way from same race
    race_selections = {}
    
    for pred in predictions:
        race_key = f"{pred.get('race_time')}_{pred.get('course')}"
        bet_type = pred.get('bet_type', 'WIN')
        

        if race_key not in race_selections:
            race_selections[race_key] = {'WIN': None, 'EACH_WAY': None}
        
        current = race_selections[race_key].get(bet_type)
        if current is None or pred.get('confidence', 0) > current.get('confidence', 0):
            race_selections[race_key][bet_type] = pred
    
    # Flatten to list
    result = []
    for race_key, selections in race_selections.items():
        if selections['WIN']:
            result.append(selections['WIN'])
        if selections['EACH_WAY']:
            result.append(selections['EACH_WAY'])
    
    return result

def call_claude_4_5(prompt, races, past_performance=None):
    """
    Calls AWS Bedrock Claude to select value bets from races/odds.
    """
    print(f"[DEBUG] call_claude_4_5 called with {len(races)} events")
    import json
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # Build context string for prompt - handle both race and event formats
    context_lines = []
    for r in races:
        # Support both horse racing format (race_time, course, runners) and sports format (event_time, venue, selections)
        event_time = r.get('race_time') or r.get('event_time', '')
        venue = r.get('course') or r.get('venue', '')
        selections = r.get('runners') or r.get('selections', [])
        
        context_lines.append(f"Event: {event_time} at {venue}")
        
        # Check if this is a multi-market event (darts special markets)
        if 'markets' in r:
            for market_name, market_data in r['markets'].items():
                context_lines.append(f"  Market: {market_name}")
                for sel in market_data.get('selections', []):
                    context_lines.append(f"    {sel['name']} (odds: {sel['odds']})")
        else:
            # Single market (standard format)
            for sel in selections:
                context_lines.append(f"  {sel['name']} (odds: {sel['odds']})")
        
        context_lines.append("")  # Blank line between events
    
    context_str = "\n".join(context_lines)
    
    # Add learning context if available
    learning_context = ""
    if past_performance:
        learning_context = f"""

PAST PERFORMANCE LEARNING (Last 7 Days):
- Total Bets: {past_performance['total_bets']}
- Win Rate: {past_performance['win_rate']}%
- Place Rate: {past_performance['place_rate']}%
- Average Winning Odds: {past_performance['avg_winning_odds']}
- Average Losing Odds: {past_performance['avg_losing_odds']}

RECENT LOSSES TO AVOID:
""" + "\n".join([f"- {loss['horse']} at {loss['odds']} ({loss['bet_type']}): {loss['why_lost']}" 
                      for loss in past_performance.get('loss_patterns', [])[:3]])
        
        learning_context += """

RECENT WINS TO EMULATE:
""" + "\n".join([f"- {win['horse']} at {win['odds']} ({win['bet_type']}) - Position {win.get('actual_position', 1)}" 
                      for win in past_performance.get('win_patterns', [])[:3]])
        
        learning_context += "\n\nAdjust your selections based on these patterns. Avoid similar characteristics to recent losses."
    
    full_prompt = prompt + learning_context + "\n\n" + context_str + "\n\nReturn a JSON array of bet objects."
    
    # Prepare request for Claude 3.5 Sonnet via Bedrock
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "temperature": 0.2,
        "system": "You are a meticulous racing quant generating calibrated per-runner probabilities. Always return valid JSON array.",
        "messages": [
            {
                "role": "user",
                "content": full_prompt
            }
        ]
    })
    
    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',  # Claude 3.5 Sonnet v1 (works with on-demand)
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Parse Claude's response - handle text before JSON
        try:
            # Try direct parsing first
            bets = json.loads(content)
            if not isinstance(bets, list):
                bets = [bets]
        except Exception as e:
            # Claude may have added explanation text - extract JSON array
            print(f"Initial parse failed, extracting JSON from text: {e}")
            try:
                # Find JSON array in content
                start = content.find('[')
                end = content.rfind(']') + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                    bets = json.loads(json_str)
                    print(f"Extracted JSON successfully: {len(bets)} bets")
                else:
                    print(f"No JSON array found in content")
                    bets = []
            except Exception as e2:
                print(f"Failed to extract JSON: {e2}")
                print(f"Raw content: {content}")
                bets = []
        
        return bets
        
    except Exception as e:
        print(f"Bedrock API error: {str(e)}")
        raise Exception(f"Bedrock API error: {str(e)}")

def store_bets_in_dynamodb(bets, prompt, model_response):
    from decimal import Decimal
    
    def convert_floats(obj):
        """Convert float values to Decimal for DynamoDB"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: convert_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_floats(item) for item in obj]
        return obj
    
    table_name = os.environ.get("SUREBET_DDB_TABLE", "SureBetBets")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    
    for bet in bets:
        bet_id = f"{bet.get('race_time','')}_{bet.get('horse','')}"
        # Convert all floats to Decimals
        bet_converted = convert_floats(bet)
        item = {
            "bet_id": bet_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
            "bet": bet_converted,
            "prompt": prompt,
            "model_response": convert_floats(model_response),
            # Expanded schema for audit/review:
            "race_time": bet.get("race_time"),
            "course": bet.get("course"),
            "horse": bet.get("horse"),
            "bet_type": bet.get("bet_type"),
            "odds": convert_floats(bet.get("odds")),
            "p_win": convert_floats(bet.get("p_win")),
            "ev": convert_floats(bet.get("ev")),
            "why_now": bet.get("why_now"),
            "confidence": convert_floats(bet.get("confidence", 50)),
            "roi": convert_floats(bet.get("roi", bet.get("ev", 0))),
            "recommendation": bet.get("recommendation", "CONSIDER"),
            "audit": {
                "created_by": "lambda",
                "created_at": datetime.datetime.utcnow().isoformat(),
                "status": "pending_outcome"
            },
            # Learning fields (to be updated after race)
            "outcome": None,  # Will be: "won", "lost", "placed", "did_not_run"
            "actual_position": None,
            "learning_notes": None,
            "feedback_processed": False
        }
        table.put_item(Item=item)
        print(f"Stored bet: {bet_id}")

def lambda_handler(event, context):
    try:
        print("Lambda execution started")
        
        # Check for manual outcome updates
        if event.get('action') == 'update_outcome':
            bet_id = event.get('bet_id')
            outcome = event.get('outcome')  # 'won', 'lost', 'placed'
            position = event.get('actual_position')
            notes = event.get('learning_notes', '')
            
            success = update_bet_outcome(bet_id, outcome, position, notes)
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
                },
                "body": json.dumps({"success": success, "message": f"Updated {bet_id}"})
            }
        
        # 1. Fetch past performance for learning
        past_performance = None
        if ENABLE_LEARNING:
            print("Fetching past performance for learning...")
            past_performance = fetch_past_performance()
            if past_performance:
                print(f"Learning from {past_performance['total_bets']} past bets (Win rate: {past_performance['win_rate']}%)")
        
        # Get sport from query parameters (default to horse_racing)
        sport = 'horse_racing'
        if event.get('queryStringParameters'):
            sport = event['queryStringParameters'].get('sport', 'horse_racing')
        print(f"Sport selected: {sport}")
        
        # 2. Fetch latest odds
        print(f"Fetching Betfair odds for {sport}...")
        events = fetch_betfair_odds(sport)
        print(f"[DEBUG] Found {len(events)} events")
        for i, e in enumerate(events[:2]):
            print(f"[DEBUG] Event {i}: {e}")

        # 3. Build prompt with timing strategy context (sport-specific)
        sport_labels = {
            'horse_racing': {'event': 'race', 'selection': 'horse', 'venue': 'course'},
            'darts': {'event': 'match', 'selection': 'player', 'venue': 'venue'},
            'cricket': {'event': 'match', 'selection': 'team', 'venue': 'ground'},
            'rugby': {'event': 'match', 'selection': 'team', 'venue': 'stadium'},
            'football': {'event': 'match', 'selection': 'team', 'venue': 'stadium'}
        }
        labels = sport_labels.get(sport, sport_labels['horse_racing'])
        sport_name = sport.replace('_', ' ').title()
        
        # Add sport-specific market instructions
        special_market_info = ""
        if sport == 'darts':
            special_market_info = (
                "\n\nDARTS SPECIAL MARKETS AVAILABLE:\n"
                "Each darts match includes multiple betting markets:\n"
                "1. Match Odds - Winner of the match\n"
                "2. Total 180s Over/Under 3.5 - Total maximums in the match\n"
                "3. Total 180s Over/Under 6.5 - Higher total for high-scoring matches\n"
                "4. Correct Score - Exact set score (e.g., 3-1, 3-2)\n\n"
                "ANALYZE ALL MARKETS for each match and identify the best value bets across all market types.\n"
                "Consider:\n"
                "- Player form and checkout percentages for Match Odds\n"
                "- Player 180 averages for Total 180s markets\n"
                "- Head-to-head history for Correct Score\n"
                "- Market odds relationships (e.g., if favorite is strong for 3-0, check those odds)\n\n"
                "For special markets, set bet_type to the market name (e.g., 'Total 180s Over 3.5', 'Correct Score 3-1')\n"
                "and selection to the specific outcome (e.g., 'Over 3.5', '3-1').\n"
            )
        elif sport == 'rugby':
            special_market_info = (
                "\n\nRUGBY SPECIAL MARKETS AVAILABLE:\n"
                "Each rugby match includes multiple betting markets:\n"
                "1. Match Odds - Winner of the match\n"
                "2. Total Points Over/Under 45.5 - Combined score\n"
                "3. Handicap - Points spread betting\n"
                "4. First Try Scorer - Player to score first try\n"
                "5. Winning Margin - Margin of victory\n\n"
                "ANALYZE ALL MARKETS for each match and identify the best value bets.\n"
                "Consider:\n"
                "- Team form and attacking/defensive stats for Match Odds\n"
                "- Average points per game for Over/Under markets\n"
                "- Head-to-head records for Handicap betting\n"
                "- Player positions and try-scoring records for First Try Scorer\n"
                "- Home advantage and historical margins for Winning Margin\n\n"
                "For special markets, set bet_type to the market name (e.g., 'Total Points Over 45.5', 'First Try Scorer')\n"
                "and selection to the specific outcome (e.g., 'Over 45.5', 'Player A').\n"
            )
        elif sport == 'cricket':
            special_market_info = (
                "\n\nCRICKET SPECIAL MARKETS AVAILABLE:\n"
                "Each cricket match includes multiple betting markets:\n"
                "1. Match Odds - Winner of the match\n"
                "2. Total Runs Over/Under 280.5 - Combined runs in match/innings\n"
                "3. Top Batsman - Highest run scorer for a team\n"
                "4. Top Bowler - Most wickets taken\n"
                "5. Method of Dismissal - How 1st wicket falls\n\n"
                "ANALYZE ALL MARKETS for each match and identify the best value bets.\n"
                "Consider:\n"
                "- Team batting/bowling strength and pitch conditions for Match Odds\n"
                "- Recent scoring trends and venue history for Total Runs\n"
                "- Batting order and current form for Top Batsman\n"
                "- Bowling attack strength and conditions for Top Bowler\n"
                "- Pitch characteristics and opening bowler quality for Method of Dismissal\n\n"
                "For special markets, set bet_type to the market name (e.g., 'Top Batsman', 'Method of Dismissal')\n"
                "and selection to the specific outcome (e.g., 'Batsman A', 'Caught').\n"
            )
        
        prompt = (
            f"{sport_name} Value Betting Analysis (UK & IRE, 24h Window):\n\n"
            f"TIMING STRATEGY: Optimal betting window is 30-90 minutes before {labels['event']} start.\n"
            f"- Events >2 hours away: Odds too volatile, reduce confidence by 30%\n"
            f"- Events 30-90 mins away: OPTIMAL - full confidence\n"
            f"- Events 15-30 mins away: Good window - slight confidence reduction (10%)\n"
            f"- Events <15 mins away: Too late - market efficient, minimal value\n"
            f"{special_market_info}"
            f"MULTI-HORSE STRATEGY (Horse Racing only): You can select up to 2 horses from the SAME race if:\n"
            f"- One is a WIN bet (high confidence, best value)\n"
            f"- One is an EACH WAY bet (good odds but slightly lower confidence for win, good place chance)\n"
            f"- They complement each other (e.g., favorite for WIN, outsider for EACH_WAY)\n\n"
            f"Evaluate all provided {labels['event']}s and return your Top 5-8 best opportunities.\n\n"
            "For each prediction, include:\n"
            f"- event_time, venue, selection, bet_type, odds\n"
            "- p_win: probability of winning (0-1 decimal)\n"
            "- ev: expected value as decimal (e.g., 0.15 for 15% ROI)\n"
            "- roi: expected return on investment percentage\n"
            f"- confidence: score 0-100 (adjusted for {labels['event']} timing as above)\n"
            "- why_now: brief explanation including timing factor\n"
            "- recommendation: 'BET' if ROI ≥ 15% and confidence ≥ 70 and in optimal window, 'CONSIDER' if ROI ≥ 10% or confidence ≥ 60, otherwise 'AVOID'\n\n"
            "Return a JSON array with 5-8 objects (can include 2 from same race if Win+EachWay) sorted by adjusted confidence.\n"
            f"Consider {labels['event']} timing in your confidence scores and recommendations.\n"
        )

        # 4. Call Claude 4.5 with prompt, context, and learning
        print("[DEBUG] Calling Claude AI...")
        print(f"[DEBUG] Events structure: {events[0] if events else 'None'}")
        all_predictions = call_claude_4_5(prompt, events, past_performance)
        print(f"Claude returned {len(all_predictions)} predictions")
        
        # 5. Enhance predictions with timing analysis
        for pred in all_predictions:
            # Find matching event for timing data
            event_timing = None
            for event in events:
                if event.get('venue') == pred.get('venue'):
                    event_timing = event.get('timing', {})
                    break
            
            if event_timing:
                pred['timing'] = event_timing
                pred['minutes_to_event'] = event_timing.get('minutes_to_event', 0)
                pred['timing_advice'] = event_timing.get('timing_advice', '')
                pred['should_bet_now'] = event_timing.get('should_bet_now', False)
                
                # Adjust recommendation based on timing
                if not event_timing.get('should_bet_now', False):
                    pred['recommendation'] = 'AVOID'
                    pred['why_now'] = f"TIMING: {event_timing.get('timing_advice')}. {pred.get('why_now', '')}"
            
            # Ensure recommendation field exists
            if 'recommendation' not in pred:
                roi = pred.get('roi', pred.get('ev', 0))
                confidence = pred.get('confidence', 0)
                timing_ok = pred.get('should_bet_now', True)
                
                if roi >= 15 and confidence >= 70 and timing_ok:
                    pred['recommendation'] = 'BET'
                elif (roi >= 10 or confidence >= 60) and timing_ok:
                    pred['recommendation'] = 'CONSIDER'
                else:
                    pred['recommendation'] = 'AVOID'
        
        # 6. Filter for multi-horse strategy (allow Win + Each Way from same race)
        bets = filter_multiple_horses_per_race(all_predictions)
        print(f"After multi-horse filtering: {len(bets)} bets selected")

        # 7. Store bets in DynamoDB
        print("Storing bets in DynamoDB...")
        store_bets_in_dynamodb(bets, prompt, bets)

        # 8. Automated betting (if enabled)
        betting_results = None
        auto_betting_enabled = os.environ.get('ENABLE_AUTO_BETTING', 'false').lower() == 'true'
        
        if auto_betting_enabled and BETTING_MODULES_AVAILABLE:
            print("🎰 Auto-betting enabled - placing bets...")
            try:
                betting_results = auto_place_bets(bets)
                print(f"Betting results: {json.dumps(betting_results, default=str)}")
            except Exception as e:
                print(f"Auto-betting error: {e}")
                betting_results = {'error': str(e)}
        elif auto_betting_enabled:
            print("⚠️ Auto-betting enabled but modules not available")
            betting_results = {'error': 'Betting modules not installed'}
        else:
            print("ℹ️ Auto-betting disabled (dry-run mode)")
            # Show what WOULD be placed
            if BETTING_MODULES_AVAILABLE:
                dry_run_bets = []
                for bet in bets:
                    bet_type, reason = determine_bet_type(bet)
                    stake = calculate_stake(bet.get('confidence', 0), bet.get('odds', 0))
                    dry_run_bets.append({
                        'horse': bet.get('horse'),
                        'bet_type': bet_type,
                        'stake': stake,
                        'reason': reason
                    })
                betting_results = {
                    'dry_run': True,
                    'would_place': dry_run_bets,
                    'message': 'Set ENABLE_AUTO_BETTING=true to place real bets'
                }

        # 9. Return bets to frontend with learning stats
        print("Returning response")
        response_body = {
            "bets": bets, 
            "event_count": len(events), 
            "sport": sport
        }
        if betting_results:
            response_body['betting_results'] = betting_results
        if past_performance:
            response_body['learning_stats'] = {
                'win_rate': past_performance['win_rate'],
                'place_rate': past_performance['place_rate'],
                'total_bets': past_performance['total_bets'],
                'learning_enabled': True
            }
        
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
            },
            "body": json.dumps(response_body)
        }
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
            },
            "body": json.dumps({"error": str(e)})
        }


