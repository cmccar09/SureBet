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
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
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
    """Get today's picks only"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        response = table.scan(
            FilterExpression='#d = :today',
            ExpressionAttributeNames={'#d': 'date'},
            ExpressionAttributeValues={':today': today}
        )
        
        items = response.get('Items', [])
        items = [decimal_to_float(item) for item in items]
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'picks': items,
            'count': len(items),
            'date': today
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
    print("  - http://localhost:5001/api/picks/today  (today only)")
    print("  - http://localhost:5001/api/health       (health check)")
    print("="*60)
    print("\nStarting server on http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
