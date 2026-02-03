"""
Update Today's Results - UI Picks Only with 4-Tier Grading Validation

This script:
1. Fetches results for UI picks only (show_in_ui=True)
2. Validates 4-tier grading matches score thresholds
3. Updates BettingPerformance table with results
4. Generates performance report

4-TIER GRADING SYSTEM:
- EXCELLENT: 75+ points (Green)       - 2.0x stake
- GOOD:      60-74 points (Light amber) - 1.5x stake
- FAIR:      45-59 points (Dark amber)  - 1.0x stake
- POOR:      <45 points (Red)         - 0.5x stake
"""

import boto3
import requests
import json
from datetime import datetime
from decimal import Decimal

def validate_4tier_grading(score, grade):
    """Validate that grade matches score threshold"""
    if score >= 75:
        return grade == 'EXCELLENT'
    elif score >= 60:
        return grade == 'GOOD'
    elif score >= 45:
        return grade == 'FAIR'
    else:
        return grade == 'POOR'

def get_todays_ui_picks():
    """Fetch only UI picks for today"""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('SureBetBets')
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    response = table.scan(
        FilterExpression='#dt = :date AND show_in_ui = :show',
        ExpressionAttributeNames={'#dt': 'date'},
        ExpressionAttributeValues={
            ':date': today,
            ':show': True
        }
    )
    
    picks = response.get('Items', [])
    
    # Validate 4-tier grading
    validated_picks = []
    for pick in picks:
        score = float(pick.get('combined_confidence', 0))
        grade = pick.get('confidence_grade', 'UNKNOWN')
        
        is_valid = validate_4tier_grading(score, grade)
        
        pick['grading_valid'] = is_valid
        validated_picks.append(pick)
    
    return validated_picks

def fetch_race_results(market_id):
    """Fetch results from Betfair for a specific market"""
    try:
        # Load credentials
        with open('betfair-creds.json', 'r') as f:
            creds = json.load(f)
        
        app_key = creds['app_key']
        session_token = creds['session_token']
        
        headers = {
            'X-Application': app_key,
            'X-Authentication': session_token,
            'Content-Type': 'application/json'
        }
        
        api_url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/"
        
        payload = {
            "marketIds": [market_id],
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS"]
            }
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                market = data[0]
                
                if market.get('status') == 'CLOSED':
                    # Race finished - get results
                    runners = market.get('runners', [])
                    
                    results = {}
                    for runner in runners:
                        selection_id = runner.get('selectionId')
                        status = runner.get('status')
                        
                        if status == 'WINNER':
                            results[selection_id] = 'WON'
                        elif status == 'PLACED':
                            results[selection_id] = 'PLACED'
                        elif status == 'LOSER':
                            results[selection_id] = 'LOST'
                    
                    return results
        
        return None
        
    except Exception as e:
        print(f"  Error fetching results for {market_id}: {str(e)}")
        return None

def update_pick_result(pick, result):
    """Update pick with result in both tables"""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    bets_table = dynamodb.Table('SureBetBets')
    perf_table = dynamodb.Table('BettingPerformance')
    
    # Update SureBetBets
    try:
        bets_table.update_item(
            Key={
                'id': pick['id'],
                'date': pick['date']
            },
            UpdateExpression='SET result = :result, updated_at = :updated',
            ExpressionAttributeValues={
                ':result': result,
                ':updated': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        print(f"  Error updating SureBetBets: {str(e)}")
    
    # Add to BettingPerformance
    try:
        perf_table.put_item(Item={
            'id': f"{pick['id']}_result",
            'date': pick['date'],
            'horse': pick['horse'],
            'course': pick.get('course', 'Unknown'),
            'race_time': pick.get('race_time', ''),
            'confidence': Decimal(str(pick.get('combined_confidence', 0))),
            'confidence_grade': pick.get('confidence_grade', 'UNKNOWN'),
            'odds': Decimal(str(pick.get('odds', 0))),
            'result': result,
            'grading_valid': pick.get('grading_valid', False),
            'created_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"  Error updating BettingPerformance: {str(e)}")

def generate_results_report(picks_with_results):
    """Generate comprehensive results report"""
    print("\n" + "="*80)
    print("TODAY'S RESULTS - UI PICKS ONLY (4-TIER GRADING VALIDATION)")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total picks: {len(picks_with_results)}")
    
    # Stats by result
    won = sum(1 for p in picks_with_results if p.get('result') == 'WON')
    placed = sum(1 for p in picks_with_results if p.get('result') == 'PLACED')
    lost = sum(1 for p in picks_with_results if p.get('result') == 'LOST')
    pending = sum(1 for p in picks_with_results if not p.get('result'))
    
    print(f"\nWON: {won} | PLACED: {placed} | LOST: {lost} | PENDING: {pending}")
    
    # Stats by grade
    print("\n" + "="*80)
    print("PERFORMANCE BY GRADE")
    print("="*80)
    
    for grade in ['EXCELLENT', 'GOOD', 'FAIR', 'POOR']:
        grade_picks = [p for p in picks_with_results if p.get('confidence_grade') == grade]
        
        if grade_picks:
            g_won = sum(1 for p in grade_picks if p.get('result') == 'WON')
            g_placed = sum(1 for p in grade_picks if p.get('result') == 'PLACED')
            g_total = len([p for p in grade_picks if p.get('result')])
            
            win_rate = (g_won / g_total * 100) if g_total > 0 else 0
            place_rate = ((g_won + g_placed) / g_total * 100) if g_total > 0 else 0
            
            print(f"\n{grade}:")
            print(f"  Total: {len(grade_picks)} | Won: {g_won} | Placed: {g_placed}")
            print(f"  Win Rate: {win_rate:.1f}% | Place Rate: {place_rate:.1f}%")
    
    # Detailed results
    print("\n" + "="*80)
    print("DETAILED RESULTS")
    print("="*80)
    
    for pick in picks_with_results:
        score = float(pick.get('combined_confidence', 0))
        grade = pick.get('confidence_grade', 'UNKNOWN')
        result = pick.get('result', 'PENDING')
        odds = float(pick.get('odds', 0))
        
        validation = "[OK]" if pick.get('grading_valid') else "[FAIL]"
        
        print(f"\n{pick['horse']:30} {score:5.1f}/100 {grade:10} {validation}")
        print(f"  {pick.get('course', 'Unknown'):20} {pick.get('race_time', '')}")
        print(f"  Odds: {odds:.2f} | Result: {result}")

def main():
    """Main workflow"""
    print("\n" + "="*80)
    print("FETCHING RESULTS - UI PICKS ONLY")
    print("="*80)
    
    # Get UI picks
    picks = get_todays_ui_picks()
    
    if not picks:
        print("\nNo UI picks found for today")
        return
    
    print(f"\nFound {len(picks)} UI picks")
    
    # Validate all have correct 4-tier grading
    invalid = [p for p in picks if not p.get('grading_valid')]
    if invalid:
        print(f"\nWARNING: {len(invalid)} picks have invalid grading")
        print("Run: python calculate_all_confidence_scores.py")
    
    # Group by market
    markets = {}
    for pick in picks:
        market_id = pick.get('market_id')
        if market_id:
            if market_id not in markets:
                markets[market_id] = []
            markets[market_id].append(pick)
    
    print(f"Checking {len(markets)} markets for results...")
    
    # Fetch results
    picks_with_results = []
    
    for market_id, market_picks in markets.items():
        print(f"\n  Market: {market_id}")
        
        results = fetch_race_results(market_id)
        
        if results:
            print(f"    Results found: {len(results)} runners")
            
            for pick in market_picks:
                selection_id = pick.get('selection_id')
                
                if selection_id in results:
                    result = results[selection_id]
                    pick['result'] = result
                    
                    print(f"    {pick['horse']}: {result}")
                    
                    # Update database
                    update_pick_result(pick, result)
                
                picks_with_results.append(pick)
        else:
            print(f"    Race not finished yet")
            picks_with_results.extend(market_picks)
    
    # Generate report
    generate_results_report(picks_with_results)
    
    print("\n" + "="*80)
    print("RESULTS UPDATE COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
