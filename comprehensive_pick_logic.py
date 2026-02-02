"""
COMPREHENSIVE PICK LOGIC - Always use this for all picks
Integrates ALL learnings:
1. Sweet spot (3-9 odds)
2. Optimal odds position (near average winner odds)
3. Form analysis (wins + consistency)
4. Course-specific performance
5. Horse history from database
6. Trainer analysis
"""

import json
import boto3
from decimal import Decimal
from datetime import datetime

def analyze_horse_comprehensive(horse_data, course, avg_winner_odds=4.65, course_winners_today=0):
    """
    Comprehensive scoring system for horses
    Returns score and breakdown
    """
    name = horse_data.get('name')
    odds = horse_data.get('odds', 0)
    form = horse_data.get('form', '')
    trainer = horse_data.get('trainer', '')
    
    score = 0
    breakdown = {}
    reasons = []
    
    # 1. SWEET SPOT CHECK (Required - return 0 if not in range)
    if not (3.0 <= odds <= 9.0):
        return 0, {}, ["Outside sweet spot range"]
    
    score += 30
    breakdown['sweet_spot'] = 30
    reasons.append(f"Sweet spot (3-9 odds): 30pts")
    
    # 2. OPTIMAL ODDS POSITION
    odds_distance = abs(odds - avg_winner_odds)
    if odds_distance < 1.0:
        score += 20
        breakdown['optimal_odds'] = 20
        reasons.append(f"Near optimal odds ({avg_winner_odds}): 20pts")
    elif odds_distance < 2.0:
        score += 10
        breakdown['optimal_odds'] = 10
        reasons.append(f"Good odds position: 10pts")
    else:
        breakdown['optimal_odds'] = 0
    
    # 3. FORM ANALYSIS
    wins = form.count('1')
    places = form.count('2') + form.count('3')
    recent_win = form.split('-')[-1] == '1' if '-' in form else False
    
    # Recent win bonus
    if recent_win:
        score += 25
        breakdown['recent_win'] = 25
        reasons.append("Recent win (last race): 25pts")
    else:
        breakdown['recent_win'] = 0
    
    # Total wins
    win_points = wins * 5
    score += win_points
    breakdown['total_wins'] = win_points
    if wins > 0:
        reasons.append(f"{wins} total wins: {win_points}pts")
    
    # Consistency (places)
    place_points = places * 2
    score += place_points
    breakdown['consistency'] = place_points
    if places > 0:
        reasons.append(f"{places} places (2nd/3rd): {place_points}pts")
    
    # 4. COURSE BONUS
    if course_winners_today > 0:
        course_bonus = 10
        score += course_bonus
        breakdown['course_performance'] = course_bonus
        reasons.append(f"{course} validated ({course_winners_today} today): {course_bonus}pts")
    else:
        breakdown['course_performance'] = 0
    
    # 5. DATABASE HISTORY
    db = boto3.resource('dynamodb', region_name='eu-west-1')
    table = db.Table('SureBetBets')
    
    try:
        response = table.scan(
            FilterExpression='horse = :name',
            ExpressionAttributeValues={':name': name}
        )
        history = response.get('Items', [])
        history_wins = sum(1 for r in history if r.get('outcome') == 'win')
        history_losses = sum(1 for r in history if r.get('outcome') == 'loss')
        
        if history_wins > 0:
            score += 15
            breakdown['database_history'] = 15
            win_rate = (history_wins / (history_wins + history_losses) * 100) if (history_wins + history_losses) > 0 else 0
            reasons.append(f"Past wins in database ({history_wins}W-{history_losses}L = {win_rate:.0f}%): 15pts")
        else:
            breakdown['database_history'] = 0
    except:
        breakdown['database_history'] = 0
    
    return score, breakdown, reasons


def get_comprehensive_pick(race_data, course_stats=None):
    """
    Get best pick from race using comprehensive analysis
    
    course_stats: {'avg_winner_odds': 4.65, 'winners_today': 4}
    """
    if course_stats is None:
        course_stats = {'avg_winner_odds': 4.65, 'winners_today': 0}
    
    course = race_data.get('venue') or race_data.get('course')
    runners = race_data.get('runners', [])
    
    analyzed_horses = []
    
    for runner in runners:
        score, breakdown, reasons = analyze_horse_comprehensive(
            runner, 
            course,
            avg_winner_odds=course_stats.get('avg_winner_odds', 4.65),
            course_winners_today=course_stats.get('winners_today', 0)
        )
        
        if score > 0:  # Only include horses in sweet spot
            analyzed_horses.append({
                'horse': runner,
                'score': score,
                'breakdown': breakdown,
                'reasons': reasons
            })
    
    if not analyzed_horses:
        return None
    
    # Sort by score
    analyzed_horses.sort(key=lambda x: x['score'], reverse=True)
    
    return analyzed_horses[0]


def format_pick_for_database(pick_data, race_data):
    """Format comprehensive pick for DynamoDB"""
    horse = pick_data['horse']
    race_time = race_data.get('start_time', '')
    course = race_data.get('venue') or race_data.get('course')
    score = pick_data['score']
    
    # Determine confidence level based on score
    if score >= 90:
        confidence_level = "VERY_HIGH"
    elif score >= 75:
        confidence_level = "HIGH"
    elif score >= 60:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"
    
    # Only show HIGH and VERY HIGH confidence picks on UI
    show_on_ui = (score >= 75)
    
    # Create bet_id
    bet_id = f"{race_time}_" + course + "_" + horse.get('name', '').replace(' ', '_')
    
    return {
        'bet_id': bet_id,
        'bet_date': datetime.now().strftime('%Y-%m-%d'),
        'course': course,
        'horse': horse.get('name'),
        'odds': Decimal(str(horse.get('odds', 0))),
        'race_time': race_time,
        'sport': 'Horse Racing',
        'race_type': race_data.get('market_name', 'Unknown'),
        'confidence': Decimal(str(score)),
        'confidence_level': confidence_level,
        'show_in_ui': show_on_ui,
        
        # Comprehensive analysis
        'analysis_method': 'COMPREHENSIVE',
        'analysis_score': Decimal(str(score)),
        'comprehensive_score': Decimal(str(score)),
        'form': horse.get('form', ''),
        'trainer': horse.get('trainer', ''),
        'selection_id': str(horse.get('selectionId', '')),
        
        'reasoning': f"Comprehensive analysis ({score}pts - {confidence_level}): " + ", ".join(pick_data['reasons'][:3]),
        'why_selected': pick_data['reasons'],
        'analysis_breakdown': {k: int(v) for k, v in pick_data['breakdown'].items()},
        
        'tags': ['comprehensive_analysis', 'sweet_spot', confidence_level.lower()],
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'source': 'comprehensive_learnings'
    }


if __name__ == "__main__":
    # Test with Wolverhampton 19:00
    with open('response_horses.json', 'r') as f:
        data = json.load(f)
    
    wolv_19 = None
    for race in data['races']:
        if race.get('venue') == 'Wolverhampton' and '19:00' in race.get('start_time', ''):
            wolv_19 = race
            break
    
    if wolv_19:
        # Wolverhampton stats from today
        wolverhampton_stats = {
            'avg_winner_odds': 4.65,  # Average of 10 winners today
            'winners_today': 4  # 4/4 Wolverhampton today
        }
        
        best_pick = get_comprehensive_pick(wolv_19, wolverhampton_stats)
        
        if best_pick:
            print("\n" + "="*80)
            print("COMPREHENSIVE PICK LOGIC - TEST")
            print("="*80)
            print(f"\n🏆 BEST PICK: {best_pick['horse']['name']} @ {best_pick['horse']['odds']}")
            print(f"Score: {best_pick['score']}")
            print(f"Form: {best_pick['horse']['form']}")
            print(f"Trainer: {best_pick['horse']['trainer']}")
            print(f"\nScoring Breakdown:")
            for key, value in best_pick['breakdown'].items():
                print(f"  {key}: {value}pts")
            print(f"\nReasons:")
            for reason in best_pick['reasons']:
                print(f"  ✓ {reason}")
            print("="*80)
