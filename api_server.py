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
        
        # Filter to only show races that haven't started yet
        now = datetime.now().isoformat()
        future_items = [item for item in items if item.get('race_time', '') >= now or item.get('race_time', '').startswith(today)]
        
        future_items.sort(key=lambda x: x.get('race_time', ''))
        
        return jsonify({
            'success': True,
            'picks': future_items,
            'count': len(future_items),
            'date': today
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
        
        picks = response.get('Items', [])
        picks = [decimal_to_float(item) for item in picks]
        
        # Filter: show only items with show_in_ui=True explicitly set
        picks = [item for item in picks 
                 if item.get('course') and item.get('course') != 'Unknown' 
                 and item.get('horse') and item.get('horse') != 'Unknown'
                 and item.get('show_in_ui') == True]
        
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
        
        return jsonify({
            'success': True,
            'date': today,
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
            'picks': picks
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

if __name__ == '__main__':
    print("="*60)
    print("Betting Picks API Server")
    print("="*60)
    print("API Endpoints:")
    print("  - http://localhost:5001/api/picks        (all picks)")
    print("  - http://localhost:5001/api/picks/today  (future picks only)")
    print("  - http://localhost:5001/api/results/today (all today + summary)")
    print("  - http://localhost:5001/api/health       (health check)")
    print("="*60)
    print("\nStarting server on http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=False)
