"""
COMPREHENSIVE PICK LOGIC - Always use this for all picks
Integrates ALL learnings:
1. Sweet spot (3-9 odds)
2. Optimal odds position (near average winner odds)
3. Form analysis (wins + consistency)
4. Course-specific performance
5. Horse history from database
6. Trainer analysis
7. Weather & going conditions
"""

import json
import boto3
from decimal import Decimal
from datetime import datetime
from weather_going_inference import check_all_tracks_going
from track_daily_insights import get_track_insights

# Default weights (fallback if DynamoDB not available)
# ADJUSTED 2026-02-04: Reduced odds bonuses, added trainer & favorite corrections
DEFAULT_WEIGHTS = {
    'sweet_spot': 20,  # Reduced from 30 - favorites winning despite lower scores
    'optimal_odds': 15,  # Reduced from 20 - less weight on odds positioning
    'recent_win': 25,
    'total_wins': 5,
    'consistency': 2,
    'course_bonus': 10,
    'database_history': 15,
    'going_suitability': 8,
    'track_pattern_bonus': 10,  # Bonus based on what's winning today at this track
    'trainer_reputation': 15,  # NEW: Elite trainers (Mullins, Elliott, Henderson)
    'favorite_correction': 10  # NEW: Short odds + elite trainer bonus
}

# Cache for weights (reload every 5 minutes)
_weights_cache = {'weights': None, 'timestamp': None}

# Cache for going conditions (reload every hour)
_going_cache = {'going_data': None, 'timestamp': None}

def get_dynamic_weights():
    """Load current weights from DynamoDB (auto-adjusted by learning system)"""
    global _weights_cache
    
    # Check cache (5 minute TTL)
    if _weights_cache['weights'] and _weights_cache['timestamp']:
        age = (datetime.now() - _weights_cache['timestamp']).total_seconds()
        if age < 300:  # 5 minutes
            return _weights_cache['weights']
    
    try:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('SureBetBets')
        
        response = table.get_item(
            Key={
                'bet_id': 'SYSTEM_WEIGHTS',
                'bet_date': 'CONFIG'
            }
        )
        
        if 'Item' in response:
            weights = response['Item'].get('weights', {})
            # Convert Decimal to float
            weights_dict = {k: float(v) for k, v in weights.items()}
            
            # Update cache
            _weights_cache['weights'] = weights_dict
            _weights_cache['timestamp'] = datetime.now()
            
            return weights_dict
        else:
            return DEFAULT_WEIGHTS.copy()
    except Exception as e:
        print(f"Warning: Could not load dynamic weights, using defaults: {e}")
        return DEFAULT_WEIGHTS.copy()


def get_going_conditions():
    """Get current going conditions for all tracks (cached for 1 hour)"""
    global _going_cache
    
    # Check cache (1 hour TTL)
    if _going_cache['going_data'] and _going_cache['timestamp']:
        age = (datetime.now() - _going_cache['timestamp']).total_seconds()
        if age < 3600:  # 1 hour
            return _going_cache['going_data']
    
    try:
        # Get going data (prioritizes official declarations)
        going_data = check_all_tracks_going(use_official=True)
        
        # Update cache
        _going_cache['going_data'] = going_data
        _going_cache['timestamp'] = datetime.now()
        
        return going_data
    except Exception as e:
        print(f"Warning: Could not load going conditions: {e}")
        return {}


def analyze_horse_comprehensive(horse_data, course, avg_winner_odds=4.65, course_winners_today=0):
    """
    Comprehensive scoring system for horses
    Returns score and breakdown
    """
    name = horse_data.get('name')
    odds = horse_data.get('odds', 0)
    form = horse_data.get('form', '')
    trainer = horse_data.get('trainer', '')
    
    # Load dynamic weights (auto-adjusted by learning system)
    weights = get_dynamic_weights()
    
    # Load going conditions
    going_data = get_going_conditions()
    
    # Load track insights from earlier races today
    track_insights = get_track_insights(course)
    
    score = 0
    breakdown = {}
    reasons = []
    
    # 1. SWEET SPOT CHECK (Required - return 0 if not in range)
    if not (3.0 <= odds <= 9.0):
        return 0, {}, ["Outside sweet spot range"]
    
    sweet_spot_pts = int(weights['sweet_spot'])
    score += sweet_spot_pts
    breakdown['sweet_spot'] = sweet_spot_pts
    reasons.append(f"Sweet spot (3-9 odds): {sweet_spot_pts}pts")
    
    # 2. OPTIMAL ODDS POSITION
    odds_distance = abs(odds - avg_winner_odds)
    if odds_distance < 1.0:
        optimal_pts = int(weights['optimal_odds'])
        score += optimal_pts
        breakdown['optimal_odds'] = optimal_pts
        reasons.append(f"Near optimal odds ({avg_winner_odds}): {optimal_pts}pts")
    elif odds_distance < 2.0:
        optimal_pts = int(weights['optimal_odds'] / 2)
        score += optimal_pts
        breakdown['optimal_odds'] = optimal_pts
        reasons.append(f"Good odds position: {optimal_pts}pts")
    else:
        breakdown['optimal_odds'] = 0
    
    # 3. FORM ANALYSIS
    wins = form.count('1')
    places = form.count('2') + form.count('3')
    recent_win = form.split('-')[-1] == '1' if '-' in form else False
    
    # Recent win bonus
    recent_win_pts = int(weights['recent_win'])
    if recent_win:
        score += recent_win_pts
        breakdown['recent_win'] = recent_win_pts
        reasons.append(f"Recent win (last race): {recent_win_pts}pts")
    else:
        breakdown['recent_win'] = 0
    
    # Total wins
    win_pts_each = int(weights['total_wins'])
    win_points = wins * win_pts_each
    score += win_points
    breakdown['total_wins'] = win_points
    if wins > 0:
        reasons.append(f"{wins} total wins: {win_points}pts")
    
    # Consistency (places)
    place_pts_each = int(weights['consistency'])
    place_points = places * place_pts_each
    score += place_points
    breakdown['consistency'] = place_points
    if places > 0:
        reasons.append(f"{places} places (2nd/3rd): {place_points}pts")
    
    # 4. COURSE BONUS
    course_bonus_pts = int(weights['course_bonus'])
    if course_winners_today > 0:
        score += course_bonus_pts
        breakdown['course_performance'] = course_bonus_pts
        reasons.append(f"{course} validated ({course_winners_today} today): {course_bonus_pts}pts")
    else:
        breakdown['course_performance'] = 0
    
    # 5. GOING CONDITIONS (Weather & Track)
    going_suitability_pts = int(weights.get('going_suitability', 8))
    if course in going_data:
        going_info = going_data[course]
        going_adjustment = going_info.get('adjustment', 0)
        going_description = going_info.get('going', 'Unknown')
        
        # Apply going adjustment (negative for soft/heavy, positive for firm)
        # Horses with good form on similar going get bonus
        if going_adjustment != 0:
            # Simple heuristic: horses with recent wins likely suited to conditions
            if recent_win and abs(going_adjustment) <= 5:
                # Recent winner gets bonus in moderate conditions
                score += going_suitability_pts
                breakdown['going_suitability'] = going_suitability_pts
                reasons.append(f"Suited to {going_description}: {going_suitability_pts}pts")
            elif abs(going_adjustment) > 5:
                # Extreme conditions (Heavy/Firm) - cautious approach
                # Only give bonus if form shows versatility (multiple wins)
                if wins >= 2:
                    bonus_pts = going_suitability_pts // 2
                    score += bonus_pts
                    breakdown['going_suitability'] = bonus_pts
                    reasons.append(f"Proven in varied going ({going_description}): {bonus_pts}pts")
                else:
                    breakdown['going_suitability'] = 0
            else:
                breakdown['going_suitability'] = 0
        else:
            breakdown['going_suitability'] = 0
    else:
        breakdown['going_suitability'] = 0
    
    # 6. DATABASE HISTORY
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
    
    # 7. TRACK PATTERN BONUS (Learning from today's earlier races at this track)
    if track_insights['has_data'] and track_insights.get('suggested_boost'):
        pattern_bonus = 0
        
        for factor, boost_amount in track_insights['suggested_boost'].items():
            # Apply boost only if this horse scored in that factor
            if breakdown.get(factor, 0) > 0:
                pattern_bonus += boost_amount
        
        if pattern_bonus > 0:
            max_pattern_bonus = int(weights.get('track_pattern_bonus', 10))
            pattern_bonus = min(pattern_bonus, max_pattern_bonus)  # Cap at max
            score += pattern_bonus
            breakdown['track_pattern_bonus'] = pattern_bonus
            
            pattern_name = track_insights.get('dominant_pattern', 'pattern')
            races_analyzed = track_insights.get('races_analyzed', 0)
            reasons.append(f"Matches {pattern_name} (from {races_analyzed} races today): +{pattern_bonus}pts")
        else:
            breakdown['track_pattern_bonus'] = 0
    else:
        breakdown['track_pattern_bonus'] = 0
    
    # 8. TRAINER REPUTATION BONUS (NEW - learned from today's losses)
    elite_trainers = [
        'W P Mullins', 'W. P. Mullins', 'Willie Mullins', 'W Mullins',
        'Gordon Elliott', 'G Elliott',
        'Nicky Henderson', 'N Henderson',
        'Paul Nicholls', 'P Nicholls',
        'Dan Skelton', 'D Skelton',
        'Henry De Bromhead', 'H De Bromhead'
    ]
    
    trainer_bonus = 0
    if trainer:
        trainer_str = str(trainer)
        for elite in elite_trainers:
            if elite.lower() in trainer_str.lower():
                trainer_bonus = int(weights.get('trainer_reputation', 15))
                score += trainer_bonus
                breakdown['trainer_reputation'] = trainer_bonus
                reasons.append(f"Elite trainer ({trainer}): +{trainer_bonus}pts")
                break
    
    if trainer_bonus == 0:
        breakdown['trainer_reputation'] = 0
    
    # 9. FAVORITE CORRECTION (NEW - short odds + elite trainer)
    favorite_bonus = 0
    if odds < 3.0 and trainer_bonus > 0:
        # Market favorite with elite trainer - likely correct pricing
        favorite_bonus = int(weights.get('favorite_correction', 10))
        score += favorite_bonus
        breakdown['favorite_correction'] = favorite_bonus
        reasons.append(f"Favorite + elite trainer: +{favorite_bonus}pts")
    else:
        breakdown['favorite_correction'] = 0
    
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
