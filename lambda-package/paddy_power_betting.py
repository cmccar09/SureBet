"""
Paddy Power Automated Betting Module
Handles automated bet placement based on AI predictions
"""

import boto3
import requests
import json
from datetime import datetime

def get_credentials():
    """Retrieve Paddy Power credentials from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    
    try:
        response = client.get_secret_value(SecretId='paddypower/credentials')
        secret = json.loads(response['SecretString'])
        return secret['username'], secret['password']
    except Exception as e:
        print(f"Error retrieving credentials: {e}")
        return None, None

def login_paddy_power(username, password):
    """
    Login to Paddy Power and get session token
    Note: This is a placeholder - actual API may differ
    Paddy Power may not have a public API - may need web scraping
    """
    # Paddy Power doesn't have an official public API
    # This would require either:
    # 1. Using their mobile app API (reverse engineered)
    # 2. Web scraping with Selenium (not recommended for Lambda)
    # 3. Using Betfair API (Paddy Power owned by Flutter/Betfair)
    
    session_url = "https://www.paddypower.com/api/login"
    
    payload = {
        "username": username,
        "password": password
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    try:
        response = requests.post(session_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('sessionToken')
        else:
            print(f"Login failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def place_win_bet(session_token, selection_id, stake, odds):
    """
    Place a win bet on Paddy Power
    
    Args:
        session_token: Active session token
        selection_id: Horse/selection ID
        stake: Bet amount (max 10 EUR)
        odds: Current odds
    """
    bet_url = "https://www.paddypower.com/api/place-bet"
    
    payload = {
        "betType": "WIN",
        "selectionId": selection_id,
        "stake": min(stake, 10.0),  # Max 10 EUR
        "odds": odds,
        "priceType": "SP"  # Starting Price or Fixed
    }
    
    headers = {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(bet_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            bet_data = response.json()
            return {
                'success': True,
                'bet_id': bet_data.get('betId'),
                'stake': stake,
                'odds': odds,
                'potential_return': stake * odds
            }
        else:
            return {
                'success': False,
                'error': f"Bet placement failed: {response.status_code}"
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def place_each_way_bet(session_token, selection_id, stake, odds, place_terms):
    """
    Place an each-way bet (win + place)
    
    Args:
        session_token: Active session token
        selection_id: Horse/selection ID
        stake: Bet amount per part (total = stake * 2, max 10 EUR total)
        odds: Current win odds
        place_terms: Place odds (usually 1/4 or 1/5 of win odds)
    """
    max_stake_per_part = 5.0  # 5 EUR win + 5 EUR place = 10 EUR total
    stake = min(stake, max_stake_per_part)
    
    bet_url = "https://www.paddypower.com/api/place-bet"
    
    payload = {
        "betType": "EACH_WAY",
        "selectionId": selection_id,
        "stake": stake,  # Stake per part
        "odds": odds,
        "placeTerms": place_terms,
        "priceType": "SP"
    }
    
    headers = {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(bet_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            bet_data = response.json()
            return {
                'success': True,
                'bet_id': bet_data.get('betId'),
                'stake_total': stake * 2,
                'win_stake': stake,
                'place_stake': stake,
                'win_odds': odds,
                'place_odds': place_terms,
                'potential_win_return': stake * odds,
                'potential_place_return': stake * place_terms
            }
        else:
            return {
                'success': False,
                'error': f"Each-way bet failed: {response.status_code}"
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def determine_bet_type(prediction):
    """
    Determine whether to place win or each-way bet based on AI prediction
    
    Rules:
    - High confidence (>80%) and short odds (<5.0): WIN bet
    - Medium confidence (60-80%) or longer odds: EACH WAY bet
    - Low confidence (<60%): Skip bet
    """
    confidence = prediction.get('confidence', 0)
    odds = prediction.get('odds', 0)
    
    if confidence < 60:
        return 'SKIP', 'Confidence too low'
    
    if confidence > 80 and odds < 5.0:
        return 'WIN', 'High confidence, short odds'
    
    return 'EACH_WAY', 'Medium confidence or longer odds - safer with place coverage'

def calculate_stake(confidence, odds, max_stake=10.0):
    """
    Calculate bet stake based on confidence and odds
    Uses Kelly Criterion adjusted for safety
    
    Args:
        confidence: AI confidence percentage (60-100)
        odds: Decimal odds
        max_stake: Maximum allowed stake (10 EUR)
    """
    # Convert confidence to probability
    probability = confidence / 100.0
    
    # Kelly Criterion: f = (bp - q) / b
    # where b = odds - 1, p = probability, q = 1 - p
    b = odds - 1
    p = probability
    q = 1 - p
    
    if b <= 0:
        return 0
    
    kelly_fraction = (b * p - q) / b
    
    # Use 25% Kelly for safety (fractional Kelly)
    safe_kelly = kelly_fraction * 0.25
    
    # Calculate stake (assuming 100 EUR bankroll base)
    bankroll = 100.0
    stake = bankroll * safe_kelly
    
    # Apply limits
    stake = max(2.0, min(stake, max_stake))  # Min 2 EUR, Max 10 EUR
    
    return round(stake, 2)

def auto_place_bets(predictions):
    """
    Automatically place bets based on AI predictions
    
    Args:
        predictions: List of betting predictions from Claude
    
    Returns:
        List of bet placement results
    """
    # Get credentials
    username, password = get_credentials()
    if not username:
        return {'error': 'Failed to retrieve credentials'}
    
    # Login
    session_token = login_paddy_power(username, password)
    if not session_token:
        return {'error': 'Failed to login to Paddy Power'}
    
    results = []
    total_staked = 0.0
    max_total_stake = 50.0  # Daily limit: 50 EUR
    
    for pred in predictions:
        if total_staked >= max_total_stake:
            results.append({
                'horse': pred.get('horse'),
                'status': 'SKIPPED',
                'reason': 'Daily stake limit reached'
            })
            continue
        
        # Determine bet type
        bet_type, reason = determine_bet_type(pred)
        
        if bet_type == 'SKIP':
            results.append({
                'horse': pred.get('horse'),
                'status': 'SKIPPED',
                'reason': reason
            })
            continue
        
        # Calculate stake
        stake = calculate_stake(
            pred.get('confidence', 0),
            pred.get('odds', 0)
        )
        
        # Check daily limit
        bet_cost = stake if bet_type == 'WIN' else stake * 2
        if total_staked + bet_cost > max_total_stake:
            stake = (max_total_stake - total_staked) / (1 if bet_type == 'WIN' else 2)
            stake = round(stake, 2)
        
        # Place bet
        if bet_type == 'WIN':
            result = place_win_bet(
                session_token,
                pred.get('selection_id'),
                stake,
                pred.get('odds')
            )
        else:  # EACH_WAY
            place_terms = pred.get('odds') * 0.25  # Assume 1/4 place terms
            result = place_each_way_bet(
                session_token,
                pred.get('selection_id'),
                stake,
                pred.get('odds'),
                place_terms
            )
        
        result['horse'] = pred.get('horse')
        result['course'] = pred.get('course')
        result['bet_type'] = bet_type
        results.append(result)
        
        if result.get('success'):
            total_staked += result.get('stake_total', result.get('stake', 0))
    
    return {
        'total_bets': len([r for r in results if r.get('success')]),
        'total_staked': total_staked,
        'bets': results
    }
