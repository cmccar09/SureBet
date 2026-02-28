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
8. CHELTENHAM FESTIVAL SPECIFIC LOGIC (March 10-13, 2026)
"""

import json
import boto3
from decimal import Decimal
from datetime import datetime
from weather_going_inference import check_all_tracks_going
from track_daily_insights import get_track_insights

# Import Cheltenham analyzer when at Cheltenham
try:
    from cheltenham_analyzer import (
        TRAINER_STATS, 
        JOCKEY_STATS,
        analyze_form_string,
        analyze_trainer_jockey
    )
    CHELTENHAM_AVAILABLE = True
except ImportError:
    CHELTENHAM_AVAILABLE = False

# Default weights (fallback if DynamoDB not available)
# ADJUSTED 2026-02-05: Further increased trainer + favorite bonuses after validation
# ENHANCED 2026-02-06: Added jockey, weight, age, distance factors for deeper analysis
# ADJUSTED 2026-02-14: Reduced favorite bias, added novice race penalty, bounce-back detection
# ADJUSTED 2026-02-26: Reduced recent_win 25->15 (learning: 'poor form' horses outperform 3.6% vs 0.6%)
#                       sweet_spot now favours 5/1-7/1 range (best odds bucket +£25.20 P/L)
DEFAULT_WEIGHTS = {
    'sweet_spot': 20,  # Best performance at 5/1-7/1 odds (£25.20 P/L); 3/1-4/1 loses money (-£11.95)
    'optimal_odds': 15,  # Reduced from 20 - less weight on odds positioning
    'recent_win': 15,  # REDUCED from 25: Learning shows 'poor form' horses win more (3.6% vs 0.6%)
    'total_wins': 5,
    'consistency': 2,
    'course_bonus': 10,
    'database_history': 15,
    'going_suitability': 14,  # RAISED from 8: Ground is CRITICAL in Feb UK/Ireland NH racing
    'track_pattern_bonus': 10,  # Bonus based on what's winning today at this track
    'trainer_reputation': 25,  # INCREASED from 20: Elite trainers are THE critical factor
    'favorite_correction': 12,  # REDUCED from 20: Ascot 13:15 lesson - favorites can fail
    'jockey_quality': 15,  # NEW: Top jockeys increase win probability
    'weight_penalty': 10,  # NEW: Heavy weights reduce chances in handicaps
    'age_bonus': 10,  # NEW: Peak age horses (4-7 years) perform better
    'distance_suitability': 12,  # NEW: Distance matching horse's strengths
    'novice_race_penalty': 15,  # NEW: Novice races are less predictable
    'bounce_back_bonus': 12,  # NEW: Horses recovering from poor run (e.g., 2-6-1)
    'short_form_improvement': 10,  # NEW: Limited form in novice = potential improvement
    'aw_low_class_penalty': 35,  # NEW: AW Class 5/6 handicaps are highly unpredictable (Dandy Khan lesson)
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


def is_cheltenham_festival(course, race_date=None):
    """
    Detect if this is a Cheltenham Festival race
    Festival dates: March 10-13, 2026
    """
    if not race_date:
        race_date = datetime.now()
    
    # Cheltenham venue check
    if 'cheltenham' not in course.lower():
        return False
    
    # Date range check (March 10-13, 2026)
    if isinstance(race_date, str):
        try:
            race_date = datetime.fromisoformat(race_date.replace('Z', '+00:00'))
        except:
            race_date = datetime.now()
    
    # Festival dates
    festival_start = datetime(2026, 3, 10)
    festival_end = datetime(2026, 3, 13, 23, 59)
    
    return festival_start <= race_date.replace(tzinfo=None) <= festival_end


def apply_cheltenham_scoring(horse_data, race_name=''):
    """
    Apply Cheltenham Festival specific scoring based on historical analysis
    Returns additional points to add to comprehensive score
    
    Historical patterns (2021-2025):
    - Willie Mullins: 32% Championship strike rate
    - Irish trained: 72.7% of winners
    - Previous Festival winners: 27.3% edge
    - Favorites win 40.9% of Championships
    - Form patterns '111' or '1111' critical
    """
    if not CHELTENHAM_AVAILABLE:
        return 0, []
    
    trainer = horse_data.get('trainer', '')
    jockey = horse_data.get('jockey', '')
    form = horse_data.get('form', '')
    odds = horse_data.get('odds', 99)
    
    bonus_points = 0
    cheltenham_reasons = []
    
    # 1. TRAINER BONUS (MOST CRITICAL)
    if trainer in TRAINER_STATS:
        stats = TRAINER_STATS[trainer]
        championship_wins = stats.get('championship_wins', 0)
        weight_multiplier = stats.get('weight_multiplier', 1.0)
        
        # Base trainer bonus
        trainer_bonus = int((weight_multiplier - 1.0) * 30)
        bonus_points += trainer_bonus
        
        if championship_wins >= 5:
            cheltenham_reasons.append(f"🏆 ELITE: {trainer} ({championship_wins} Championship wins) +{trainer_bonus}pts")
        elif championship_wins >= 3:
            cheltenham_reasons.append(f"⭐ {trainer} ({championship_wins} Championships) +{trainer_bonus}pts")
        elif championship_wins >= 1:
            cheltenham_reasons.append(f"✅ {trainer} (Championship winner) +{trainer_bonus}pts")
        
        # Irish trained bonus (72.7% of winners)
        if stats.get('irish_trained', False):
            irish_bonus = 15
            bonus_points += irish_bonus
            cheltenham_reasons.append(f"🇮🇪 Irish trained (73% of winners) +{irish_bonus}pts")
        
        # Race specialty match
        specialties = stats.get('specialties', [])
        if race_name and any(s.lower() in race_name.lower() for s in specialties):
            specialty_bonus = 20
            bonus_points += specialty_bonus
            cheltenham_reasons.append(f"🎯 Race specialist ({trainer}) +{specialty_bonus}pts")
    
    # 2. JOCKEY BONUS
    if jockey in JOCKEY_STATS:
        stats = JOCKEY_STATS[jockey]
        championship_wins = stats.get('championship_wins', 0)
        
        if championship_wins >= 5:
            jockey_bonus = 15
            bonus_points += jockey_bonus
            cheltenham_reasons.append(f"🏆 Elite jockey: {jockey} ({championship_wins} wins) +{jockey_bonus}pts")
        elif championship_wins >= 3:
            jockey_bonus = 10
            bonus_points += jockey_bonus
            cheltenham_reasons.append(f"⭐ {jockey} ({championship_wins} Championships) +{jockey_bonus}pts")
        elif championship_wins >= 1:
            jockey_bonus = 5
            bonus_points += jockey_bonus
            cheltenham_reasons.append(f"✅ {jockey} (Championship exp) +{jockey_bonus}pts")
        
        # Trainer-Jockey combo bonus
        pairs_with = stats.get('pairs_with', '')
        combo_bonus = stats.get('combo_bonus', 0)
        if pairs_with and pairs_with.lower() in trainer.lower() and combo_bonus > 0:
            bonus_points += combo_bonus
            cheltenham_reasons.append(f"🤝 PROVEN COMBO: {trainer}/{jockey} +{combo_bonus}pts")
    
    # 3. FORM PATTERN BONUS ('111' or '1111' critical)
    if '1111' in form:
        form_bonus = 20
        bonus_points += form_bonus
        cheltenham_reasons.append(f"📊 ELITE FORM '1111' (Championship pattern) +{form_bonus}pts")
    elif '111' in form:
        form_bonus = 15
        bonus_points += form_bonus
        cheltenham_reasons.append(f"📊 STRONG FORM '111' (Championship pattern) +{form_bonus}pts")
    elif '11' in form:
        form_bonus = 10
        bonus_points += form_bonus
        cheltenham_reasons.append(f"📊 Winning streak '11' +{form_bonus}pts")
    
    # 4. FAVORITE BONUS (40.9% win rate - but don't over-rely)
    if odds < 3.0:
        favorite_bonus = 7  # REDUCED from 10 - Ascot 13:15 lesson
        bonus_points += favorite_bonus
        cheltenham_reasons.append(f"💰 Favorite (41% Championship win rate) +{favorite_bonus}pts")
    
    return bonus_points, cheltenham_reasons


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
    
    # 1. SWEET SPOT CHECK (Graduated - give points based on odds)
    sweet_spot_pts = 0
    if 3.0 <= odds <= 9.0:
        # Full points in sweet spot
        sweet_spot_pts = int(weights['sweet_spot'])
        reasons.append(f"Sweet spot (3-9 odds): {sweet_spot_pts}pts")
    elif 2.0 <= odds < 3.0:
        # Partial points for short odds
        sweet_spot_pts = int(weights['sweet_spot'] * 0.6)
        reasons.append(f"Short odds (2-3): {sweet_spot_pts}pts")
    elif 1.5 <= odds < 2.0:
        # Lower points for very short odds
        sweet_spot_pts = int(weights['sweet_spot'] * 0.4)
        reasons.append(f"Very short odds (1.5-2): {sweet_spot_pts}pts")
    elif odds < 1.5:
        # Minimal points for heavy favorites
        sweet_spot_pts = int(weights['sweet_spot'] * 0.2)
        reasons.append(f"Heavy favorite (<1.5): {sweet_spot_pts}pts")
    elif 9.0 < odds <= 15.0:
        # Partial points for medium outsiders
        sweet_spot_pts = int(weights['sweet_spot'] * 0.5)
        reasons.append(f"Medium outsider (9-15): {sweet_spot_pts}pts")
    elif odds > 15.0:
        # Minimal points for long shots
        sweet_spot_pts = int(weights['sweet_spot'] * 0.2)
        reasons.append(f"Long shot (>15): {sweet_spot_pts}pts")
    
    score += sweet_spot_pts
    breakdown['sweet_spot'] = sweet_spot_pts
    
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
    
    # 4.5. CLAIMING JOCKEY BONUS (NEW 2026-02-20)
    # Claiming jockeys (indicated by numbers in brackets like (5), (7)) get weight allowances
    # In Heavy/Soft going, reduced weight is a significant advantage
    jockey = horse_data.get('jockey', '')
    claiming_allowance = 0
    if '(' in jockey and ')' in jockey:
        try:
            # Extract claiming allowance: "Toby McCain-Mitchell(5)" -> 5
            claiming_str = jockey.split('(')[1].split(')')[0]
            claiming_allowance = int(claiming_str)
        except:
            claiming_allowance = 0
    
    if claiming_allowance > 0 and course in going_data:
        going_desc = going_data[course].get('going', 'Unknown')
        if 'Heavy' in going_desc or 'Soft' in going_desc:
            # In testing ground, weight allowance is crucial
            claiming_bonus = claiming_allowance * 2  # 5lb claim = 10pts bonus
            score += claiming_bonus
            breakdown['claiming_jockey'] = claiming_bonus
            reasons.append(f"Claiming {claiming_allowance}lb in {going_desc}: {claiming_bonus}pts")
        else:
            # Moderate bonus in normal conditions
            claiming_bonus = claiming_allowance
            score += claiming_bonus
            breakdown['claiming_jockey'] = claiming_bonus
            reasons.append(f"Claiming {claiming_allowance}lb allowance: {claiming_bonus}pts")
    else:
        breakdown['claiming_jockey'] = 0
    
    # 5. GOING CONDITIONS - Proper horse suitability assessment
    # February UK/Ireland: Soft/Heavy ground is the norm - this is a MAJOR differentiator
    # A horse that can't handle soft simply has little chance; proven soft-ground performers
    # get a significant edge over rivals who prefer quicker ground.
    base_going_pts = int(weights.get('going_suitability', 14))
    
    if course in going_data:
        going_info = going_data[course]
        going_adjustment = going_info.get('adjustment', 0)
        going_description = going_info.get('going', 'Unknown')
        is_soft_ground = 'Heavy' in going_description or 'Soft' in going_description
        is_extreme = abs(going_adjustment) >= 5  # Heavy/Soft or very firm
        is_all_weather = going_info.get('surface', '') == 'all-weather' or 'Standard' in going_description
        
        # Double weight in extreme conditions (absolutely critical discriminator)
        going_suitability_pts = base_going_pts * 2 if is_extreme else base_going_pts
        
        if is_all_weather:
            # All-weather: ground irrelevant, give neutral bonus for all runners
            going_suitability_pts = base_going_pts // 2
            score += going_suitability_pts
            breakdown['going_suitability'] = going_suitability_pts
            reasons.append(f"All-weather (going neutral): +{going_suitability_pts}pts")
        else:
            # Check horse going preference from data (explicit field if available)
            going_pref = str(horse_data.get('going_preference', horse_data.get('goes_on', ''))).lower()
            
            # Infer suitability from preference field or form
            suited = False
            if going_pref and going_pref not in ['', 'none', 'unknown', 'n/a']:
                # Explicit preference known
                if is_soft_ground and any(g in going_pref for g in ['soft', 'heavy', 'any', 'all']):
                    suited = True
                elif not is_soft_ground and any(g in going_pref for g in ['firm', 'good', 'fast', 'any', 'all']):
                    suited = True
            
            if not suited:
                # Form-based proxy:
                # 3+ wins = proven versatile performer (adapts to most going)
                # 2 wins + extreme going = give benefit of doubt
                # Recent win in similar conditions = suited
                if wins >= 3:
                    suited = True   # Multiple wins across varied conditions = adaptable
                elif wins >= 2 and not is_extreme:
                    suited = True   # Consistent performer in moderate conditions
                elif wins >= 1 and is_soft_ground and 'Heavy' not in going_description:
                    suited = True   # Has won before, moderate soft = probably handles it
            
            if suited:
                score += going_suitability_pts
                breakdown['going_suitability'] = going_suitability_pts
                reasons.append(f"Proven/suited to {going_description}: +{going_suitability_pts}pts")
            elif is_extreme and wins == 0:
                # No wins at all in extreme going = flag risk
                penalty = base_going_pts
                score -= penalty
                breakdown['going_suitability'] = -penalty
                reasons.append(f"No wins - unproven in {going_description}: -{penalty}pts")
            elif is_extreme and wins <= 1:
                # Limited form in extreme going = smaller risk flag
                penalty = base_going_pts // 2
                score -= penalty
                breakdown['going_suitability'] = -penalty
                reasons.append(f"Limited wins - questionable in {going_description}: -{penalty}pts")
            else:
                breakdown['going_suitability'] = 0
    else:
        # Track not in going data - use seasonal default (Feb = probably soft)
        current_month = datetime.now().month
        if current_month in [1, 2, 3, 11, 12]:  # Winter months
            # Soft is likely - only reward horses with multiple wins
            if wins >= 2:
                default_pts = base_going_pts // 2
                score += default_pts
                breakdown['going_suitability'] = default_pts
                reasons.append(f"Consistent form (going prob. soft in {datetime.now().strftime('%B')}): +{default_pts}pts")
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
    
    # 8. TRAINER REPUTATION BONUS (Comprehensive UK + Irish trainers)
    # Elite jockeys for jockey quality analysis (added below)
    elite_jockeys = [
        # Irish Champion Jockeys
        'Paul Townend', 'P Townend', 'P. Townend',
        'Jack Kennedy', 'J Kennedy', 'J. Kennedy',
        'Rachael Blackmore', 'R Blackmore', 'R. Blackmore',
        'Mark Walsh', 'M Walsh', 'M. Walsh',
        'Davy Russell', 'D Russell', 'D. Russell',
        'Patrick Mullins', 'P Mullins', 'Mr P. Mullins', 'Mr P Mullins',
        'Danny Mullins', 'D Mullins', 'D. Mullins',
        # UK Champion Jockeys (National Hunt)
        'Harry Cobden', 'H Cobden', 'H. Cobden',
        'Nico de Boinville', 'N de Boinville', 'N. de Boinville',
        'Harry Skelton', 'H Skelton', 'H. Skelton',
        'Sam Twiston-Davies', 'S Twiston-Davies', 'S. Twiston-Davies',
        'Bryony Frost', 'B Frost', 'B. Frost',
        'Tom Scudamore', 'T Scudamore', 'T. Scudamore',
        'Aidan Coleman', 'A Coleman', 'A. Coleman',
        # UK Flat Racing Champions
        'William Buick', 'W Buick', 'W. Buick',
        'Frankie Dettori', 'F Dettori', 'F. Dettori',
        'Ryan Moore', 'R Moore', 'R. Moore',
        'Oisin Murphy', 'O Murphy', 'O. Murphy',
        'Jim Crowley', 'J Crowley', 'J. Crowley',
        'Tom Marquand', 'T Marquand', 'T. Marquand',
        'Hollie Doyle', 'H Doyle', 'H. Doyle'
    ]
    
    elite_trainers = [
        # Irish Champions
        'W P Mullins', 'W. P. Mullins', 'Willie Mullins', 'W Mullins',
        'Gordon Elliott', 'G Elliott', 'G. Elliott',
        'Henry De Bromhead', 'H De Bromhead', 'H. De Bromhead',
        'Gavin Cromwell', 'G Cromwell', 'Gavin Patrick Cromwell',
        'J P Dempsey', 'J. P. Dempsey', 'John P Dempsey',
        'Don Browne', 'D Browne',
        'John Patrick Ryan', 'J P Ryan',
        'Michael Winters', 'M Winters',
        # UK Champions - Established
        'Nicky Henderson', 'N Henderson',
        'Paul Nicholls', 'P Nicholls',
        'Dan Skelton', 'D Skelton',
        'Tim Easterby', 'T Easterby',
        # UK National Hunt - Winners from today's validation
        'Donald McCain', 'D McCain', 'Donald Mccain',
        'Harry Fry', 'H Fry',
        'Emma Lavelle', 'E Lavelle',
        'David Pipe', 'D Pipe',
        'Lucy Wadham', 'L Wadham',
        'Neil King', 'N King',
        'Alan King', 'A King',
        'Neil Mulholland', 'N Mulholland',
        # UK All-Weather & Flat - Winners from validation
        'Michael Dods', 'M Dods',
        'Tony Carroll', 'T Carroll', 'A W Carroll',
        'David Barron', 'T D Barron', 'T. D. Barron', 'David & Nicola Barron', 'Nicola Barron',
        # UK National Hunt - Other Established Trainers
        'Warren Greatrex', 'W Greatrex',
        'Charlie Longsdon', 'C Longsdon',
        'Fergal O Brien', 'F O Brien', 'Fergal Obrien', "Fergal O'Brien",
        'Olly Murphy', 'O Murphy',
        'Kim Bailey', 'K Bailey',
        'Colin Tizzard', 'C Tizzard',
        'Philip Hobbs', 'P Hobbs',
        'Venetia Williams', 'V Williams',
        'Jonjo O Neill', 'J O Neill', 'Jonjo Oneill', "Jonjo O'Neill", "A.J. O'Neill", "AJ O'Neill"
    ]
    
    trainer_bonus = 0
    if trainer:
        trainer_str = str(trainer)
        for elite in elite_trainers:
            if elite.lower() in trainer_str.lower():
                trainer_bonus = int(weights.get('trainer_reputation', 15))
                
                # CRITICAL FIX: David Pipe penalty in Heavy/Soft (Feb 20 lesson)
                # Both River Run Free (93) and Itseemslikeit (107) LOST today
                if any(x in trainer_str for x in ['David Pipe', 'D Pipe', 'D. Pipe']):
                    going_desc = going_data.get(course, {}).get('going', '')
                    if 'Heavy' in going_desc or 'Soft' in going_desc:
                        penalty = 15  # Remove 60% of trainer bonus in Heavy/Soft
                        trainer_bonus -= penalty
                        if trainer_bonus < 5:
                            trainer_bonus = 5  # Minimum 5pts
                        reasons.append(f"David Pipe Heavy/Soft record: -{penalty}pts penalty")
                
                score += trainer_bonus
                breakdown['trainer_reputation'] = trainer_bonus
                reasons.append(f"Elite trainer ({trainer}): +{trainer_bonus}pts")
                break
    
    if trainer_bonus == 0:
        breakdown['trainer_reputation'] = 0
    
    # 9. FAVORITE CORRECTION (Elite trainer boost for all odds ranges)
    favorite_bonus = 0
    if trainer_bonus > 0:
        # Elite trainer gets boost regardless of odds
        if odds < 2.0:
            # Heavy favorite with elite trainer
            favorite_bonus = int(weights.get('favorite_correction', 10) * 1.5)
            
            # David Pipe penalty for favorites in Heavy/Soft (Feb 20 lesson)
            if any(x in str(trainer) for x in ['David Pipe', 'D Pipe', 'D. Pipe']):
                going_desc = going_data.get(course, {}).get('going', '')
                if 'Heavy' in going_desc or 'Soft' in going_desc:
                    favorite_bonus = int(favorite_bonus * 0.4)  # 60% reduction
                    reasons.append(f"David Pipe favorite in Heavy/Soft: reduced to +{favorite_bonus}pts")
                else:
                    reasons.append(f"Heavy favorite + elite trainer: +{favorite_bonus}pts")
            else:
                reasons.append(f"Heavy favorite + elite trainer: +{favorite_bonus}pts")
        elif odds < 4.0:
            # Short odds with elite trainer
            favorite_bonus = int(weights.get('favorite_correction', 10))
            
            # David Pipe penalty in Heavy/Soft
            if any(x in str(trainer) for x in ['David Pipe', 'D Pipe', 'D. Pipe']):
                going_desc = going_data.get(course, {}).get('going', '')
                if 'Heavy' in going_desc or 'Soft' in going_desc:
                    favorite_bonus = int(favorite_bonus * 0.5)  # 50% reduction
                    reasons.append(f"David Pipe Heavy/Soft: reduced to +{favorite_bonus}pts")
                else:
                    reasons.append(f"Elite trainer bonus: +{favorite_bonus}pts")
            else:
                reasons.append(f"Elite trainer bonus: +{favorite_bonus}pts")
        else:
            # Any odds with elite trainer gets smaller boost
            favorite_bonus = int(weights.get('favorite_correction', 10) * 0.5)
            reasons.append(f"Elite trainer (underdog): +{favorite_bonus}pts")
        
        score += favorite_bonus
        breakdown['favorite_correction'] = favorite_bonus
    else:
        breakdown['favorite_correction'] = 0
    
    # 10. JOCKEY QUALITY (NEW - Elite jockeys boost)
    jockey_quality_pts = int(weights.get('jockey_quality', 15))
    jockey_name = horse_data.get('jockey', '')
    is_elite_jockey = False
    
    if jockey_name:
        jockey_lower = jockey_name.lower()
        for elite in elite_jockeys:
            if elite.lower() in jockey_lower:
                is_elite_jockey = True
                score += jockey_quality_pts
                breakdown['jockey_quality'] = jockey_quality_pts
                reasons.append(f"Elite jockey ({jockey_name}): +{jockey_quality_pts}pts")
                break
    
    if not is_elite_jockey:
        breakdown['jockey_quality'] = 0
    
    # 11. NOVICE RACE PENALTY (NEW - Lesson from Ascot 13:15)
    novice_penalty = 0
    race_name = race_data.get('market_name', '') if 'race_data' in locals() else horse_data.get('race_type', '')
    if race_name and any(keyword in race_name.lower() for keyword in ['nov', 'novice', 'maiden']):
        novice_penalty = int(weights.get('novice_race_penalty', 15))
        score -= novice_penalty
        breakdown['novice_penalty'] = -novice_penalty
        reasons.append(f"⚠️ Novice race (less predictable): -{novice_penalty}pts")
    else:
        breakdown['novice_penalty'] = 0

    # 11b. AW LOW CLASS PENALTY (Lesson: 2026-02-28 Lingfield 15:52)
    # Class 5/6 AW handicaps are designed by handicappers to produce unpredictable results.
    # Our scoring rewards form/trainer consistency - exactly what is discounted in these races.
    # Going advantage (our main edge) is also zero on AW Standard.
    # Royal Jet scored 105 (trainer +25, wins +20, form 3111) yet lost to Dandy Khan (42) at 8/1.
    aw_low_class_penalty = 0
    aw_marker = horse_data.get('race_class', horse_data.get('class', ''))
    aw_name_check = str(horse_data.get('race_name', horse_data.get('market_name', race_name))).lower()
    is_low_class = (
        str(aw_marker) in ['5', '6', 'Class 5', 'Class 6'] or
        'class 5' in aw_name_check or 'class 6' in aw_name_check or
        'class5' in aw_name_check or 'class6' in aw_name_check
    )
    # Only apply to AW (going_suitability_pts sourced from is_all_weather check above)
    # We re-derive the AW flag here safely from going_data
    _going_info_for_class = going_data.get(course, {})
    _is_aw_for_class = (
        _going_info_for_class.get('surface', '') == 'all-weather' or
        'Standard' in str(_going_info_for_class.get('going', ''))
    )
    if _is_aw_for_class and is_low_class:
        aw_low_class_penalty = int(weights.get('aw_low_class_penalty', 20))
        score -= aw_low_class_penalty
        breakdown['aw_low_class_penalty'] = -aw_low_class_penalty
        reasons.append(f"AW Class 5/6 (unpredictable handicap): -{aw_low_class_penalty}pts")
    else:
        breakdown['aw_low_class_penalty'] = 0

    # 12. BOUNCE-BACK PATTERN (NEW - Lesson from Ascot 13:15)
    # Detect patterns like 2-6-1 or 2-5-1 showing recovery after poor run
    bounce_back_pts = int(weights.get('bounce_back_bonus', 12))
    if form:
        form_parts = form.split('-')
        if len(form_parts) >= 3:
            try:
                # Check last 3 runs: [good]-[bad]-[better]
                last_3 = form_parts[-3:]
                if (last_3[0] in ['1', '2', '3'] and  # Started well
                    last_3[1] in ['5', '6', '7', '8', '9', '0'] and  # Poor run
                    last_3[2] in ['1', '2', '3']):  # Recovered
                    score += bounce_back_pts
                    breakdown['bounce_back'] = bounce_back_pts
                    reasons.append(f"📈 Bounce-back pattern ({'-'.join(last_3)}): +{bounce_back_pts}pts")
                else:
                    breakdown['bounce_back'] = 0
            except:
                breakdown['bounce_back'] = 0
        else:
            breakdown['bounce_back'] = 0
    else:
        breakdown['bounce_back'] = 0
    
    # 13. SHORT FORM IMPROVEMENT (NEW - Lesson from Ascot 13:15)
    # In novice races, limited form might indicate improving horse
    short_form_pts = int(weights.get('short_form_improvement', 10))
    if novice_penalty < 0 and form:  # Only in novice races
        form_length = len(form.replace('-', ''))
        if form_length <= 3 and '2' in form:  # Very short form with a place
            score += short_form_pts
            breakdown['short_form_improvement'] = short_form_pts
            reasons.append(f"🌟 Limited form in novice (improving?): +{short_form_pts}pts")
        else:
            breakdown['short_form_improvement'] = 0
    else:
        breakdown['short_form_improvement'] = 0
    
    # 14. WEIGHT PENALTY (NEW - for handicap races)
    weight_penalty_pts = int(weights.get('weight_penalty', 10))
    weight_carried = horse_data.get('weight', None)
    
    if weight_carried:
        try:
            # Parse weight (e.g., "10-7" = 10 stone 7 pounds = 147 lbs)
            if isinstance(weight_carried, str) and '-' in weight_carried:
                parts = weight_carried.split('-')
                total_lbs = int(parts[0]) * 14 + int(parts[1])
            else:
                total_lbs = float(weight_carried)
            
            # Penalty for heavy weights (over 150 lbs)
            if total_lbs > 150:
                penalty = min(weight_penalty_pts, (total_lbs - 150) // 2)
                score -= penalty
                breakdown['weight_penalty'] = -penalty
                reasons.append(f"Heavy weight ({weight_carried}): -{penalty}pts")
            else:
                breakdown['weight_penalty'] = 0
        except:
            breakdown['weight_penalty'] = 0
    else:
        breakdown['weight_penalty'] = 0
    
    # 15. AGE BONUS (peak age varies by race type)
    age_bonus_pts = int(weights.get('age_bonus', 10))
    horse_age = horse_data.get('age', None)
    
    if horse_age:
        try:
            age = int(horse_age)
            # National Hunt: peak 6-9 years, Flat: peak 3-5 years
            race_type = str(race_data.get('type', 'flat') if 'race_data' in locals() else 'flat').lower()
            
            if 'hurdle' in race_type or 'chase' in race_type or 'nh' in race_type:
                # National Hunt: peak 6-9
                if 6 <= age <= 9:
                    score += age_bonus_pts
                    breakdown['age_bonus'] = age_bonus_pts
                    reasons.append(f"Peak NH age ({age}yo): +{age_bonus_pts}pts")
                elif age < 5 or age > 11:
                    penalty = age_bonus_pts // 2
                    score -= penalty
                    breakdown['age_bonus'] = -penalty
                    reasons.append(f"Unproven age ({age}yo): -{penalty}pts")
                else:
                    breakdown['age_bonus'] = 0
            else:
                # Flat racing: peak 3-5
                if 3 <= age <= 5:
                    score += age_bonus_pts
                    breakdown['age_bonus'] = age_bonus_pts
                    reasons.append(f"Peak flat age ({age}yo): +{age_bonus_pts}pts")
                elif age > 7:
                    penalty = age_bonus_pts // 2
                    score -= penalty
                    breakdown['age_bonus'] = -penalty
                    reasons.append(f"Veteran ({age}yo): -{penalty}pts")
                else:
                    breakdown['age_bonus'] = 0
        except:
            breakdown['age_bonus'] = 0
    else:
        breakdown['age_bonus'] = 0
    
    # 13. DISTANCE SUITABILITY (NEW - match horse to race distance)
    distance_pts = int(weights.get('distance_suitability', 12))
    # Distance bonus based on wins + form consistency
    if wins >= 2 and recent_win:
        # Proven winner likely at preferred distance
        score += distance_pts
        breakdown['distance_suitability'] = distance_pts
        reasons.append(f"Proven distance performer: +{distance_pts}pts")
    elif wins >= 3:
        # Versatile performer
        bonus = distance_pts // 2
        score += bonus
        breakdown['distance_suitability'] = bonus
        reasons.append(f"Versatile performer: +{bonus}pts")
    else:
        breakdown['distance_suitability'] = 0
    
    # 14. CHELTENHAM FESTIVAL BONUS (CRITICAL FOR SYSTEM SURVIVAL)
    # Apply Championship-specific scoring if at Cheltenham Festival (March 10-13, 2026)
    if is_cheltenham_festival(course):
        race_name = horse_data.get('race_name', '')
        cheltenham_bonus, cheltenham_reasons = apply_cheltenham_scoring(horse_data, race_name)
        
        if cheltenham_bonus > 0:
            score += cheltenham_bonus
            breakdown['cheltenham_festival'] = cheltenham_bonus
            reasons.append(f"\n🏆 CHELTENHAM FESTIVAL BONUS: +{cheltenham_bonus}pts")
            reasons.extend(cheltenham_reasons)
            print(f"\n🏆 CHELTENHAM DETECTED - Applied {cheltenham_bonus} bonus points")
            print("   " + "\n   ".join(cheltenham_reasons))
        else:
            breakdown['cheltenham_festival'] = 0
            reasons.append("⚠️ CHELTENHAM: No elite connections - HIGH RISK")
    else:
        breakdown['cheltenham_festival'] = 0
    
    return score, breakdown, reasons


def get_comprehensive_pick(race_data, course_stats=None):
    """
    Get best pick from race using comprehensive analysis
    SKIP RACE if multiple horses score 85+ (too close to call)
    
    course_stats: {'avg_winner_odds': 4.65, 'winners_today': 4}
    Returns: best_pick dict or None if race should be skipped
    """
    if course_stats is None:
        course_stats = {'avg_winner_odds': 4.65, 'winners_today': 0}
    
    course = race_data.get('venue') or race_data.get('course')
    runners = race_data.get('runners', [])
    
    analyzed_horses = []
    
    # Calculate coverage: % of runners with form data
    total_runners = len(runners)
    runners_with_data = 0
    
    for runner in runners:
        form = runner.get('form', '')
        odds = runner.get('odds', 0)
        
        # Count as having data if has form and odds
        if form and form not in ['N/A', '', None] and odds and float(odds) > 0:
            runners_with_data += 1
        
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
    
    # Calculate coverage percentage
    coverage = (runners_with_data / total_runners * 100) if total_runners > 0 else 0
    
    # Sort by score
    analyzed_horses.sort(key=lambda x: x['score'], reverse=True)
    
    # CHECK: If 2+ horses score 85+, apply tiered logic:
    # - Exactly 2 qualifying: back the TOP scorer (evidence: 14:55 Kelso 28-Feb-26 - top scorer won 14/1)
    # - 3+ qualifying: skip (too unpredictable - 14:30 Doncaster 28-Feb-26 lowest scorer won 5/1)
    recommended_horses = [h for h in analyzed_horses if h['score'] >= 85]
    if len(recommended_horses) >= 3:
        # 3+ qualifiers - too close to call, skip
        print(f"  ⚠️  RACE SKIPPED: {len(recommended_horses)} horses scored 85+ (too close to call)")
        for h in recommended_horses:
            horse_name = h['horse'].get('name', 'Unknown')
            print(f"     - {horse_name}: {h['score']}/100")
        return None
    elif len(recommended_horses) == 2:
        # Exactly 2 qualifiers - back the top scorer, log the competition
        top = recommended_horses[0]
        second = recommended_horses[1]
        top_name = top['horse'].get('name', 'Unknown')
        second_name = second['horse'].get('name', 'Unknown')
        print(f"  2 horses scored 85+: backing top scorer {top_name} ({top['score']}) over {second_name} ({second['score']})")
        # Override analyzed_horses so best_pick below picks the top qualifier
        analyzed_horses = recommended_horses
    
    # Add coverage to the best pick
    best_pick = analyzed_horses[0]
    best_pick['coverage'] = round(coverage, 1)
    best_pick['total_runners'] = total_runners
    best_pick['analyzed_runners'] = runners_with_data
    
    return best_pick


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
    
    # Show only recommended picks on UI
    # LEARNING 2026-02-26: 90-100 = +33% ROI, 80-84 = +8% ROI, 85-89 = -21.8% ROI (BUT tiny sample)
    # 2026-02-28: AW Class 5/6 penalty applied - pushed below 75 threshold automatically
    aw_penalised = float(best_pick.get('breakdown', {}).get('aw_low_class_penalty', 0)) < 0
    show_on_ui = (score >= 85) and not aw_penalised  # AW Class 5/6 never shown regardless of score
    recommended_bet = show_on_ui
    
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
        'recommended_bet': recommended_bet,
        
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
            print(f"\nBEST PICK: {best_pick['horse']['name']} @ {best_pick['horse']['odds']}")
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
