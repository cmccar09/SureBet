# SureBet Lambda: fetch odds, call Claude 4.5, store bets in DynamoDB

import os
import json
import boto3
import datetime
import requests

# Import automated betting modules
try:
    from betfair_odds_fetcher import get_live_betfair_races
    from betfair_cert_auth import authenticate_with_certificate, get_betfair_cert_from_secrets
    BETTING_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Betting modules not available: {e}")
    BETTING_MODULES_AVAILABLE = False

# Learning data
def get_latest_performance():
    """Get latest learning insights to adjust strategy"""
    try:
        learning_table_name = os.environ.get('LEARNING_TABLE', 'BettingPerformance')
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(learning_table_name)
        
        response = table.query(
            KeyConditionExpression='period = :period',
            ExpressionAttributeValues={':period': 'last_7_days'},
            ScanIndexForward=False,
            Limit=1
        )
        
        items = response.get('Items', [])
        if items:
            item = items[0]
            insights_data = json.loads(item.get('insights', '{}'))
            analysis_data = json.loads(item.get('analysis', '{}'))
            return {
                'roi': float(item.get('overall_roi', 0)),
                'win_rate': float(item.get('overall_win_rate', 0)),
                'insights': insights_data,
                'analysis': analysis_data,
                'loss_patterns': insights_data.get('loss_patterns', []),
                'recommendations': insights_data.get('recommendations', [])
            }
    except Exception as e:
        print(f"Could not fetch learning data: {e}")
    
    return None

# --- Free Odds API integration ---
def fetch_betfair_odds():
    """
    Fetch live horse racing odds using Betfair certificate authentication
    Filters races to optimal betting window (15 mins - 24 hours)
    """
    # Try Betfair API with certificate authentication
    if BETTING_MODULES_AVAILABLE:
        try:
            print("Fetching live Betfair odds using certificate authentication...")
            
            # Get credentials from environment
            username = os.environ.get('BETFAIR_USERNAME')
            password = os.environ.get('BETFAIR_PASSWORD')
            app_key = os.environ.get('BETFAIR_APP_KEY')
            
            if not all([username, password, app_key]):
                print("ERROR: Missing Betfair credentials in environment variables")
                print(f"BETFAIR_USERNAME: {'✓' if username else '✗'}")
                print(f"BETFAIR_PASSWORD: {'✓' if password else '✗'}")
                print(f"BETFAIR_APP_KEY: {'✓' if app_key else '✗'}")
                return []
            
            # Authenticate and fetch races
            session_token = authenticate_with_certificate(username, password, app_key)
            if not session_token:
                print("ERROR: Betfair authentication failed")
                return []
            
            # Store session token in environment for betfair_odds_fetcher
            os.environ['BETFAIR_SESSION_TOKEN'] = session_token
            
            races = get_live_betfair_races()
            if races:
                print(f"✓ Successfully fetched {len(races)} real Betfair races")
                return races
            else:
                print("WARNING: No races found in betting window")
                return []
        except Exception as e:
            print(f"ERROR: Betfair fetch failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # No mock data fallback - return empty if Betfair fails
    print("ERROR: Betting modules not available - cannot fetch races")
    return []

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

def call_claude_4_5(prompt, races, performance_data=None):
    """
    Calls AWS Bedrock Claude Sonnet 4.5 to select value bets from races/odds.
    Uses boto3 with your AWS credentials (no API key needed).
    Incorporates learning insights if available.
    """
    import json
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # Build context string for prompt
    context_str = "\n".join([
        f"Race: {r['race_time']} {r['course']}\n" +
        "\n".join([f"  {runner['name']} (odds: {runner['odds']})" for runner in r['runners']])
        for r in races
    ])
    
    # Add performance insights if available with ACTIONABLE ADJUSTMENTS
    learning_context = ""
    confidence_adjustment = 0  # Will reduce if overconfident
    roi_threshold_adjustment = 0  # Will increase if too many losses
    
    if performance_data:
        insights = performance_data.get('insights', {})
        loss_patterns = performance_data.get('loss_patterns', [])
        recommendations = performance_data.get('recommendations', [])
        roi = performance_data.get('roi', 0)
        
        learning_context = f"\n\n=== LEARNING FROM RECENT PERFORMANCE ===\n"
        learning_context += f"Last 7 days ROI: {roi:.1f}%\n"
        
        # Critical loss patterns (teach Claude what went wrong)
        if loss_patterns:
            learning_context += "\n🔴 LOSS PATTERNS DETECTED (Learn from these mistakes):\n"
            for pattern in loss_patterns:
                learning_context += f"  • {pattern}\n"
        
        if insights.get('strengths'):
            learning_context += "\n✅ What's working (double down on these):\n"
            for strength in insights['strengths']:
                learning_context += f"  ✓ {strength}\n"
        
        if insights.get('weaknesses'):
            learning_context += "\n⚠️ What's failing (avoid these patterns):\n"
            for weakness in insights['weaknesses']:
                learning_context += f"  ⚠ {weakness}\n"
        
        if recommendations:
            learning_context += "\n🎯 APPLY THESE CHANGES NOW:\n"
            for rec in recommendations:
                learning_context += f"  → {rec}\n"
                
                # Auto-adjust based on recommendations
                if 'Reduce ALL confidence' in rec or 'overconfident' in rec:
                    confidence_adjustment = -15  # Reduce confidence by 15%
                elif 'Reduce confidence on favorites' in rec:
                    learning_context += "     (For odds <3.0, reduce confidence by 20%)\n"
                
                if 'require 20%+ ROI' in rec or 'Tighten' in rec:
                    roi_threshold_adjustment = 5  # Increase ROI requirement by 5%
        
        learning_context += f"\n💡 CALIBRATION ADJUSTMENTS THIS RUN:\n"
        if confidence_adjustment != 0:
            learning_context += f"  • All confidence scores adjusted by {confidence_adjustment:+d}%\n"
        if roi_threshold_adjustment != 0:
            learning_context += f"  • ROI threshold increased by {roi_threshold_adjustment:+d}%\n"
        
        learning_context += "\nUse these lessons to make BETTER selections than last time.\n"
    
    full_prompt = prompt + learning_context + "\n\n" + context_str + "\n\nReturn a JSON array of bet objects."
    
    # Prepare request for Claude 3.5 Sonnet via Bedrock
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "temperature": 0.2,
        "system": "You are a meticulous racing quant generating calibrated per-runner probabilities. Learn from past performance to improve selections. Always return valid JSON array.",
        "messages": [
            {
                "role": "user",
                "content": full_prompt
            }
        ]
    })
    
    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',  # Claude 3.5 Sonnet
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

def store_bets_in_dynamodb(bets, prompt, model_response, races=None):
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
    
    # Delete old picks from today to prevent accumulation
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    try:
        print(f"Cleaning up old picks from {today}...")
        response = table.query(
            KeyConditionExpression='bet_date = :date',
            ExpressionAttributeValues={':date': today}
        )
        old_items = response.get('Items', [])
        for item in old_items:
            table.delete_item(Key={'bet_date': item['bet_date'], 'bet_id': item['bet_id']})
        print(f"Deleted {len(old_items)} old picks")
    except Exception as e:
        print(f"Error cleaning old picks: {e}")
    
    # Build lookup for market_id by course
    market_id_lookup = {}
    if races:
        for race in races:
            course = race.get('course', '')
            market_id = race.get('market_id', '')
            if course and market_id:
                market_id_lookup[course] = market_id
    
    for bet in bets:
        # Normalize field names (handle both old and new formats from Claude)
        horse = bet.get("horse") or bet.get("selection") or "Unknown"
        course = bet.get("course") or bet.get("venue") or "Unknown"
        race_time = bet.get("race_time") or bet.get("event_time") or ""
        
        bet_id = f"{race_time}_{horse}".replace(" ", "_").replace(":", "")
        if not bet_id or bet_id == "__":
            timestamp_slug = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            bet_id = f"bet_{timestamp_slug}_{bet.get('selection_id', '')}"
        
        # Calculate decision metrics
        p_win = float(bet.get("p_win", 0))
        p_place = float(bet.get("p_place", p_win * 2.5))
        odds = float(bet.get("odds", 0))
        confidence = float(bet.get("confidence", 50))
        roi = float(bet.get("roi", bet.get("ev", 0)))
        bet_type = bet.get("bet_type", "WIN")
        
        # Combined Confidence (0-100) - weighted combination of all signals
        edge_component = min(20, (roi / 50) * 20) if roi > 0 else 0  # 0-20 points
        win_component = min(40, p_win * 40)  # 0-40 points
        place_component = min(20, p_place * 20)  # 0-20 points
        consistency_component = min(20, (confidence / 100) * 20)  # 0-20 points
        
        combined_confidence = round(edge_component + win_component + place_component + consistency_component, 1)
        
        # Confidence Grade
        if combined_confidence >= 75:
            conf_grade = "VERY HIGH"
            conf_color = "darkgreen"
        elif combined_confidence >= 60:
            conf_grade = "HIGH"
            conf_color = "green"
        elif combined_confidence >= 45:
            conf_grade = "MODERATE"
            conf_color = "orange"
        else:
            conf_grade = "LOW"
            conf_color = "red"
        
        # Decision Score (0-100) - overall bet quality
        roi_score = min(40, (roi / 50) * 40) if roi > 0 else 0
        ev_score = min(30, (roi / 10) * 30) if roi > 0 else 0
        confidence_weight = (confidence / 100) * 20
        place_weight = (p_place * 10) if bet_type == 'EW' or bet_type == 'EACH_WAY' else (p_win * 10)
        
        decision_score = round(roi_score + ev_score + confidence_weight + place_weight, 1)
        
        # Decision Rating
        if decision_score >= 70:
            decision_rating = "DO IT"
            rating_color = "green"
        elif decision_score >= 45:
            decision_rating = "RISKY"
            rating_color = "orange"
        else:
            decision_rating = "NOT GREAT"
            rating_color = "red"
        
        # Track performance only for MODERATE RISK or better (exclude RISKY and NOT GREAT)
        # MODERATE = combined_confidence >= 45, or decision_rating = DO IT
        track_performance = (combined_confidence >= 45 or decision_rating == "DO IT")
        
        # Convert all floats to Decimals
        bet_converted = convert_floats(bet)
        bet_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        
        # Get market_id if available
        market_id = market_id_lookup.get(course, '')
        
        item = {
            "bet_id": bet_id,
            "bet_date": bet_date,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "date": bet_date,  # Keep for backwards compatibility
            "bet": bet_converted,
            "prompt": prompt,
            "model_response": convert_floats(model_response),
            # Expanded schema for audit/review:
            "race_time": race_time,
            "course": course,
            "horse": horse,
            "bet_type": bet_type,
            "odds": convert_floats(odds),
            "p_win": convert_floats(p_win),
            "p_place": convert_floats(p_place),
            "ev": convert_floats(bet.get("ev", roi)),
            "why_now": bet.get("why_now"),
            "confidence": convert_floats(confidence),
            "roi": convert_floats(roi),
            "recommendation": bet.get("recommendation", "CONSIDER"),
            # Betfair metadata
            "market_id": market_id,  # Betfair market ID for result fetching
            # Performance tracking
            "track_performance": track_performance,  # Only track MODERATE RISK or better
            # Decision metrics
            "decision_score": convert_floats(decision_score),
            "decision_rating": decision_rating,
            "rating_color": rating_color,
            "combined_confidence": convert_floats(combined_confidence),
            "confidence_grade": conf_grade,
            "confidence_color": conf_color,
            "confidence_breakdown": {
                "edge_component": convert_floats(edge_component),
                "win_component": convert_floats(win_component),
                "place_component": convert_floats(place_component),
                "consistency_component": convert_floats(consistency_component)
            },
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
        
        # 1. Fetch latest performance data for learning
        print("Fetching learning insights...")
        performance_data = get_latest_performance()
        if performance_data:
            print(f"✓ Using performance insights (ROI: {performance_data['roi']:.1f}%)")
        else:
            print("No learning data available yet")
        
        # 2. Fetch latest odds
        print("Fetching Betfair odds...")
        races = fetch_betfair_odds()
        print(f"Found {len(races)} races")

        # 3. Build prompt with timing strategy context
        prompt = (
            "Horse Racing Value Betting Analysis (UK & IRE, 24h Window):\n\n"
            "TIMING STRATEGY: Optimal betting window is 30-90 minutes before race start.\n"
            "- Races >2 hours away: Odds too volatile, reduce confidence by 30%\n"
            "- Races 30-90 mins away: OPTIMAL - full confidence\n"
            "- Races 15-30 mins away: Good window - slight confidence reduction (10%)\n"
            "- Races <15 mins away: Too late - market efficient, minimal value\n\n"
            "Evaluate all provided races and ALWAYS return your Top 5 best opportunities.\n\n"
            "For each prediction, include:\n"
            "- race_time, course, horse, bet_type, odds\n"
            "- p_win: probability of winning (0-1 decimal)\n"
            "- ev: expected value as decimal (e.g., 0.15 for 15% ROI)\n"
            "- roi: expected return on investment percentage\n"
            "- confidence: score 0-100 (adjusted for race timing as above)\n"
            "- why_now: brief explanation including timing factor\n"
            "- recommendation: 'BET' if ROI ≥ 15% and confidence ≥ 70 and in optimal window, 'CONSIDER' if ROI ≥ 10% or confidence ≥ 60, otherwise 'AVOID'\n\n"
            "Return a JSON array with exactly 5 objects sorted by adjusted confidence.\n"
            "Consider race timing in your confidence scores and recommendations.\n"
        )

        # 4. Call Claude 4.5 with prompt, context, and learning insights
        print("Calling Claude AI...")
        all_predictions = call_claude_4_5(prompt, races, performance_data)
        print(f"Claude returned {len(all_predictions)} predictions")
        
        # 5. Enhance predictions with timing analysis
        for pred in all_predictions:
            # Find matching race for timing data
            race_timing = None
            for race in races:
                if race.get('venue') == pred.get('course'):
                    race_timing = race.get('timing', {})
                    break
            
            if race_timing:
                pred['timing'] = race_timing
                pred['minutes_to_race'] = race_timing.get('minutes_to_race', 0)
                pred['timing_advice'] = race_timing.get('timing_advice', '')
                pred['should_bet_now'] = race_timing.get('should_bet_now', False)
                
                # Adjust recommendation based on timing
                if not race_timing.get('should_bet_now', False):
                    pred['recommendation'] = 'AVOID'
                    pred['why_now'] = f"TIMING: {race_timing.get('timing_advice')}. {pred.get('why_now', '')}"
            
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
        
        bets = all_predictions

        # 5. Store bets in DynamoDB
        print("Storing bets in DynamoDB...")
        store_bets_in_dynamodb(bets, prompt, bets, races)

        # 5. Automated betting (if enabled)
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
            # No dry-run bet display since we removed betting modules
            betting_results = {
                'dry_run': True,
                'message': 'Auto-betting disabled - predictions stored in DynamoDB only'
            }

        # 6. Return bets to frontend
        print("Returning response")
        response_body = {"bets": bets, "race_count": len(races)}
        if betting_results:
            response_body['betting_results'] = betting_results
        
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
