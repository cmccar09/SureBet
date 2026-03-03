"""
Simple API server to fetch betting picks from DynamoDB
Runs locally to provide data to React frontend
"""

from flask import Flask, jsonify
from flask_cors import CORS
import boto3
from datetime import datetime
from decimal import Decimal

app = Flask(__name__)
CORS(app)  # Allow React app to call this API

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

def get_system_run_times():
    """Get last run and next run times from scheduled task or estimates"""
    try:
        import subprocess
        import platform
        
        if platform.system() == 'Windows':
            # Get scheduled task info
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-ScheduledTask -TaskName "BettingWorkflow_AutoLearning" -ErrorAction SilentlyContinue | Get-ScheduledTaskInfo | Select-Object -Property LastRunTime, NextRunTime | ConvertTo-Json'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                import json
                task_info = json.loads(result.stdout)
                last_run = task_info.get('LastRunTime', '')
                next_run = task_info.get('NextRunTime', '')
                
                if last_run and next_run:
                    return {
                        'last_run': last_run,
                        'next_run': next_run
                    }
    except Exception as e:
        print(f"Could not get task info: {e}")
    
    # Fallback: estimate based on 8:00 AM daily schedule
    from datetime import timedelta
    now = datetime.now()
    today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
    
    if now < today_8am:
        # Before today's run
        last_run = (today_8am - timedelta(days=1)).isoformat()
        next_run = today_8am.isoformat()
    else:
        # After today's run
        last_run = today_8am.isoformat()
        next_run = (today_8am + timedelta(days=1)).isoformat()
    
    return {
        'last_run': last_run,
        'next_run': next_run
    }

def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj

@app.route('/api/picks', methods=['GET'])
def get_picks():
    """Get all picks from DynamoDB"""
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        # Convert Decimals to floats
        items = [decimal_to_float(item) for item in items]
        
        # Sort by timestamp descending
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'picks': items,
            'count': len(items)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/picks/today', methods=['GET'])
def get_today_picks():
    """Get today's RECOMMENDED picks only (excludes training data, analyses, and learning records)"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get ONLY actual betting picks (exclude training, analyses, and learning records)
        response = table.query(
            KeyConditionExpression='bet_date = :today',
            FilterExpression='(attribute_not_exists(is_learning_pick) OR is_learning_pick = :not_learning) AND attribute_not_exists(analysis_type) AND attribute_not_exists(learning_type) AND attribute_exists(course) AND attribute_exists(horse)',
            ExpressionAttributeValues={
                ':today': today,
                ':not_learning': False
            }
        )
        
        items = response.get('Items', [])
        items = [decimal_to_float(item) for item in items]
        
        # Filter: show only items with show_in_ui=True explicitly set
        items = [item for item in items 
                 if item.get('course') and item.get('course') != 'Unknown' 
                 and item.get('horse') and item.get('horse') != 'Unknown'
                 and item.get('show_in_ui') == True]
        
        # Filter for HIGH confidence picks only
        # Require comprehensive_score >= 75 AND combined_confidence >= 55 (not POOR)
        high_confidence_items = []
        for item in items:
            comp_score = float(item.get('comprehensive_score') or item.get('analysis_score') or 0)
            comb_conf  = float(item.get('combined_confidence') or 0)
            # Accept if comprehensive_score passes threshold;
            # but reject if combined_confidence explicitly marks this as POOR (<55)
            if comp_score >= 75 and (comb_conf == 0 or comb_conf >= 55):
                high_confidence_items.append(item)
        items = high_confidence_items
        
        # Filter to only show races that haven't started yet
        now = datetime.now().isoformat()
        future_items = [item for item in items if item.get('race_time', '') >= now or item.get('race_time', '').startswith(today)]
        
        # Sort by comprehensive score (highest first)
        for item in future_items:
            comp_score = item.get('comprehensive_score') or item.get('analysis_score') or 0
            item['_sort_score'] = float(comp_score)
        future_items.sort(key=lambda x: x.get('_sort_score', 0), reverse=True)
        
        # Limit to maximum 10 picks per day
        future_items = future_items[:10]
        
        # Remove temporary sort field
        for item in future_items:
            item.pop('_sort_score', None)

        # ONE PICK PER RACE: keep only the highest-scoring pick per race
        seen_races = {}
        for pick in future_items:
            race_key = (pick.get('course', ''), pick.get('race_time', ''))
            existing = seen_races.get(race_key)
            if not existing or float(pick.get('comprehensive_score', 0)) > float(existing.get('comprehensive_score', 0)):
                seen_races[race_key] = pick
        future_items = list(seen_races.values())
        future_items.sort(key=lambda x: x.get('race_time', ''))

        # Calculate next_best_score for each pick (to show competition level)
        for pick in future_items:
            pick_course = pick.get('course', '')
            pick_race_time = pick.get('race_time', '')
            pick_score = float(pick.get('comprehensive_score', 0))
            
            # Find all horses in the same race (from all items, not just UI picks)
            same_race_horses = [
                item for item in items 
                if item.get('course') == pick_course 
                and item.get('race_time') == pick_race_time
                and item.get('horse') != pick.get('horse')  # Exclude self
                and item.get('comprehensive_score')  # Has a score
            ]
            
            # Find the next best score
            if same_race_horses:
                scores = [float(h.get('comprehensive_score', 0)) for h in same_race_horses]
                scores.sort(reverse=True)
                pick['next_best_score'] = scores[0] if scores else 0
                pick['score_gap'] = pick_score - (scores[0] if scores else 0)
            else:
                pick['next_best_score'] = 0
                pick['score_gap'] = 0
        
        # Get system run times
        run_times = get_system_run_times()
        
        return jsonify({
            'success': True,
            'picks': future_items,
            'count': len(future_items),
            'date': today,
            'last_run': run_times['last_run'],
            'next_run': run_times['next_run'],
            'message': f"System runs daily at 8:00 AM. {len(future_items)} picks available for today."
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/results/today', methods=['GET'])
def get_today_results():
    """Get today's RECOMMENDED PICKS with results summary (excludes training, analyses, and learning records)"""
    try:
        from datetime import datetime, timedelta
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Query BOTH today and yesterday (since picks may have yesterday's bet_date but today's race times)
        all_picks = []
        for date in [today, yesterday]:
            response = table.query(
                KeyConditionExpression='bet_date = :date',
                FilterExpression='(attribute_not_exists(is_learning_pick) OR is_learning_pick = :not_learning) AND attribute_not_exists(analysis_type) AND attribute_not_exists(learning_type) AND attribute_exists(course) AND attribute_exists(horse)',
                ExpressionAttributeValues={
                    ':date': date,
                    ':not_learning': False
                }
            )
            all_picks.extend(response.get('Items', []))
        
        picks = all_picks
        picks = [decimal_to_float(item) for item in picks]
        
        # Filter to only show races with today's date in race_time
        picks = [item for item in picks 
                 if item.get('race_time', '').startswith(today)]
        
        # Filter: show only items with show_in_ui=True explicitly set
        # If show_in_ui is True, display it regardless of score (the score filter was already applied when setting show_in_ui)
        picks = [item for item in picks 
                 if item.get('course') and item.get('course') != 'Unknown' 
                 and item.get('horse') and item.get('horse') != 'Unknown'
                 and item.get('show_in_ui') == True]
        
        # Don't filter by time - show ALL today's picks (past and future)
        # This is the RESULTS page, not the upcoming picks page
        
        # Sort by comprehensive score (highest first) and limit to 10 per day
        for item in picks:
            comp_score = item.get('comprehensive_score') or item.get('analysis_score') or 0
            item['_sort_score'] = float(comp_score)
        picks.sort(key=lambda x: x.get('_sort_score', 0), reverse=True)
        picks = picks[:10]  # Maximum 10 picks per day
        
        # Remove temporary sort field
        for item in picks:
            item.pop('_sort_score', None)
        
        # Calculate summary stats from outcomes
        wins = sum(1 for p in picks if p.get('outcome') == 'win')
        places = sum(1 for p in picks if p.get('outcome') == 'placed')
        losses = sum(1 for p in picks if p.get('outcome') == 'loss')
        pending = sum(1 for p in picks if p.get('outcome') in [None, 'pending'])
        
        total_stake = sum(float(p.get('stake', 0)) for p in picks)
        
        # Calculate returns
        total_return = 0
        for p in picks:
            outcome = p.get('outcome', '').lower() if p.get('outcome') else None
            stake = float(p.get('stake', 0))
            odds = float(p.get('odds', 0))
            
            if outcome == 'win':
                bet_type = p.get('bet_type', 'WIN').upper()
                if bet_type == 'WIN':
                    total_return += stake * odds
                else:  # EW
                    ew_fraction = float(p.get('ew_fraction', 0.2))
                    total_return += (stake/2) * odds + (stake/2) * (1 + (odds-1) * ew_fraction)
            elif outcome == 'placed':
                ew_fraction = float(p.get('ew_fraction', 0.2))
                total_return += (stake/2) * (1 + (odds-1) * ew_fraction)
        
        profit = total_return - total_stake
        roi = (profit / total_stake * 100) if total_stake > 0 else 0
        strike_rate = (wins / len(picks) * 100) if picks else 0
        
        # Sort picks by race time
        picks.sort(key=lambda x: x.get('race_time', ''))
        
        # Get learning/all races data (like Wolverhampton)
        learning_response = table.query(
            KeyConditionExpression='bet_date = :today',
            FilterExpression='is_learning_pick = :learning AND attribute_exists(course) AND attribute_exists(horse)',
            ExpressionAttributeValues={
                ':today': today,
                ':learning': True
            }
        )
        
        learning_picks = learning_response.get('Items', [])
        learning_picks = [decimal_to_float(item) for item in learning_picks]
        
        # Group learning picks by course
        from collections import defaultdict
        learning_by_course = defaultdict(list)
        for pick in learning_picks:
            course = pick.get('course', 'Unknown')
            learning_by_course[course].append(pick)
        
        # Sort each course's horses by odds
        for course in learning_by_course:
            learning_by_course[course].sort(key=lambda x: float(x.get('odds', 999)))
        
        # Get system run times
        run_times = get_system_run_times()
        
        return jsonify({
            'success': True,
            'date': today,
            'last_run': run_times['last_run'],
            'next_run': run_times['next_run'],
            'message': f"Next picks will be generated at 8:00 AM tomorrow." if len(picks) == 0 else f"{len(picks)} picks for today.",
            'summary': {
                'total_picks': len(picks),
                'wins': wins,
                'places': places,
                'losses': losses,
                'pending': pending,
                'total_stake': round(total_stake, 2),
                'total_return': round(total_return, 2),
                'profit': round(profit, 2),
                'roi': round(roi, 2),
                'strike_rate': round(strike_rate, 2)
            },
            'picks': picks,
            'all_races': dict(learning_by_course)  # All races data grouped by course
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'betting-picks-api',
        'timestamp': datetime.now().isoformat()
    })

# ============================================================================
# CHELTENHAM FESTIVAL 2026 API ENDPOINTS
# ============================================================================

@app.route('/api/cheltenham/races', methods=['GET'])
def get_cheltenham_races():
    """Get all Cheltenham Festival 2026 races"""
    try:
        cheltenham_table = dynamodb.Table('CheltenhamFestival2026')
        response = cheltenham_table.scan()
        items = response.get('Items', [])
        
        # Filter to get race info only (not individual horses)
        races = [item for item in items if item.get('horseId') == 'RACE_INFO']
        races = [decimal_to_float(item) for item in races]
        
        # Group by day
        days = {}
        for race in races:
            day = race.get('festivalDay', 'Unknown')
            if day not in days:
                days[day] = []
            days[day].append(race)
        
        # Sort races within each day by time
        for day in days:
            days[day].sort(key=lambda x: x.get('raceTime', '00:00'))
        
        return jsonify({
            'success': True,
            'days': days,
            'totalRaces': len(races)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cheltenham/races/<race_id>', methods=['GET'])
def get_cheltenham_race(race_id):
    """Get specific race with all horses and research"""
    try:
        cheltenham_table = dynamodb.Table('CheltenhamFestival2026')
        response = cheltenham_table.query(
            KeyConditionExpression='raceId = :raceId',
            ExpressionAttributeValues={':raceId': race_id}
        )
        
        items = response.get('Items', [])
        items = [decimal_to_float(item) for item in items]
        
        # Separate race info from horses
        race_info = next((item for item in items if item.get('horseId') == 'RACE_INFO'), None)
        horses = [item for item in items if item.get('horseId') != 'RACE_INFO']
        
        # Sort horses by confidence rank (highest first)
        horses.sort(key=lambda x: x.get('confidenceRank', 0), reverse=True)
        
        return jsonify({
            'success': True,
            'race': race_info,
            'horses': horses,
            'totalHorses': len(horses)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cheltenham/races/<race_id>/horses', methods=['POST'])
def update_cheltenham_horse(race_id):
    """Add or update horse research for a specific race"""
    from flask import request
    
    try:
        data = request.json
        cheltenham_table = dynamodb.Table('CheltenhamFestival2026')
        
        horse_name = data.get('horseName', '')
        if not horse_name:
            return jsonify({
                'success': False,
                'error': 'Horse name is required'
            }), 400
        
        # Create horse ID with timestamp for tracking updates
        horse_id = f"{horse_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        item = {
            'raceId': race_id,
            'horseId': horse_id,
            'horseName': horse_name,
            'festivalDay': data.get('festivalDay', ''),
            'confidenceRank': decimal_to_float(data.get('confidenceRank', 0)),
            'currentOdds': data.get('currentOdds', 'N/A'),
            'trainer': data.get('trainer', ''),
            'jockey': data.get('jockey', ''),
            'form': data.get('form', ''),
            'researchNotes': data.get('researchNotes', []),
            'lastUpdated': datetime.now().isoformat(),
            'analysis': data.get('analysis', {}),
            'betRecommendation': data.get('betRecommendation', 'HOLD')
        }
        
        cheltenham_table.put_item(Item=item)
        
        return jsonify({
            'success': True,
            'horseId': horse_id,
            'message': f'Updated {horse_name} successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cheltenham/research/<race_id>', methods=['POST'])
def add_cheltenham_research(race_id):
    """Add research notes to a specific race"""
    from flask import request
    
    try:
        data = request.json
        cheltenham_table = dynamodb.Table('CheltenhamFestival2026')
        
        # Get current race info
        response = cheltenham_table.get_item(
            Key={'raceId': race_id, 'horseId': 'RACE_INFO'}
        )
        
        race_item = response.get('Item', {})
        
        # Add new research note
        notes = race_item.get('researchNotes', [])
        notes.append({
            'timestamp': datetime.now().isoformat(),
            'note': data.get('note', ''),
            'type': data.get('type', 'GENERAL')
        })
        
        # Update race
        cheltenham_table.update_item(
            Key={'raceId': race_id, 'horseId': 'RACE_INFO'},
            UpdateExpression='SET researchNotes = :notes, lastUpdated = :updated',
            ExpressionAttributeValues={
                ':notes': notes,
                ':updated': datetime.now().isoformat()
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Research note added successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cheltenham/picks', methods=['GET'])
def get_cheltenham_picks():
    """
    Return today's top pick for every 2026 Cheltenham race, including
    whether the pick changed from yesterday's saved pick.

    Query params:
      ?date=YYYY-MM-DD   override today's date (for testing)
    """
    from flask import request as flask_request
    from datetime import datetime as dt, timedelta

    try:
        target_date = flask_request.args.get('date', dt.now().strftime('%Y-%m-%d'))
        yesterday   = (dt.strptime(target_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        picks_table = dynamodb.Table('CheltenhamPicks')

        # Fetch today
        today_resp = picks_table.scan(
            FilterExpression='pick_date = :d',
            ExpressionAttributeValues={':d': target_date}
        )
        today_items = {item['race_name']: decimal_to_float(item)
                       for item in today_resp.get('Items', [])}

        # Fetch yesterday (for context if today has no saves yet)
        yest_resp = picks_table.scan(
            FilterExpression='pick_date = :d',
            ExpressionAttributeValues={':d': yesterday}
        )
        yest_items = {item['race_name']: decimal_to_float(item)
                      for item in yest_resp.get('Items', [])}

        # Build response grouped by festival day
        days = {}
        all_picks = list(today_items.values()) or list(yest_items.values())

        for item in all_picks:
            day = item.get('day', 'Unknown')
            if day not in days:
                days[day] = []
            days[day].append({
                'race_name':      item.get('race_name', ''),
                'day':            item.get('day', ''),
                'race_time':      item.get('race_time', ''),
                'grade':          item.get('grade', ''),
                'distance':       item.get('distance', ''),
                'horse':          item.get('horse', ''),
                'trainer':        item.get('trainer', ''),
                'jockey':         item.get('jockey', ''),
                'odds':           item.get('odds', ''),
                'score':          item.get('score', 0),
                'tier':           item.get('tier', ''),
                'value_rating':   item.get('value_rating', 0),
                'second_score':   item.get('second_score', 0),
                'score_gap':      item.get('score_gap', 0),
                'confidence':     item.get('confidence', ''),
                'reasons':        item.get('reasons', []),
                'warnings':       item.get('warnings', []),
                'pick_changed':   item.get('pick_changed', False),
                'previous_horse': item.get('previous_horse', ''),
                'previous_odds':  item.get('previous_odds', ''),
                'change_reason':  item.get('change_reason', ''),
                'pick_date':      item.get('pick_date', target_date),
                'all_horses':     item.get('all_horses', []),
            })

        # Sort each day's picks by grade / race name
        day_order = [
            'Tuesday_10_March',
            'Wednesday_11_March',
            'Thursday_12_March',
            'Friday_13_March',
        ]
        ordered_days = {d: days[d] for d in day_order if d in days}
        for d in days:
            if d not in ordered_days:
                ordered_days[d] = days[d]

        total_changes = sum(1 for p in all_picks if p.get('pick_changed'))

        return jsonify({
            'success':      True,
            'pick_date':    target_date,
            'days':         ordered_days,
            'total_picks':  len(all_picks),
            'total_changes': total_changes,
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error':   str(e)
        }), 500


@app.route('/api/cheltenham/picks/save', methods=['POST'])
def save_cheltenham_picks_api():
    """Trigger a fresh pick-save run (calls save_cheltenham_picks logic)"""
    try:
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, 'save_cheltenham_picks.py'],
            capture_output=True, text=True, cwd='.', timeout=120
        )
        success = result.returncode == 0
        return jsonify({
            'success': success,
            'output':  result.stdout[-3000:] if result.stdout else '',
            'errors':  result.stderr[-1000:] if result.stderr else '',
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("="*60)
    print("Betting Picks API Server")
    print("="*60)
    print("API Endpoints:")
    print("  - http://localhost:5001/api/picks        (all picks)")
    print("  - http://localhost:5001/api/picks/today  (future picks only)")
    print("  - http://localhost:5001/api/results/today (all today + summary)")
    print("  - http://localhost:5001/api/health       (health check)")
    print("\nCheltenham Festival 2026:")
    print("  - http://localhost:5001/api/cheltenham/races")
    print("  - http://localhost:5001/api/cheltenham/races/<race_id>")
    print("  - http://localhost:5001/api/cheltenham/picks         (today's picks)")
    print("  - http://localhost:5001/api/cheltenham/picks/save    (trigger save)")
    print("="*60)
    print("\nStarting server on http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=False)
