"""
Weather-based Going Inference with Seasonal Adjustments
Check recent rainfall + seasonal patterns to estimate ground conditions
"""
import requests
from datetime import datetime, timedelta

# Track locations (approximate coordinates)
TRACK_LOCATIONS = {
    'Carlisle': {'lat': 54.89, 'lon': -2.94, 'surface': 'turf'},
    'Taunton': {'lat': 51.02, 'lon': -3.10, 'surface': 'turf'},
    'Fairyhouse': {'lat': 53.47, 'lon': -6.45, 'surface': 'turf'},
    'Wolverhampton': {'lat': 52.59, 'lon': -2.13, 'surface': 'all-weather'},
    'Kempton': {'lat': 51.42, 'lon': -0.34, 'surface': 'all-weather'},
    'Punchestown': {'lat': 53.19, 'lon': -6.63, 'surface': 'turf'},
}

# Seasonal going bias (UK/Ireland climate)
# Winter months = wetter/softer, Summer = drier/firmer
SEASONAL_ADJUSTMENTS = {
    1: -5,   # January - Very wet
    2: -5,   # February - Wet
    3: -3,   # March - Wet
    4: -2,   # April - Transitional
    5: 0,    # May - Mild
    6: +2,   # June - Drier
    7: +5,   # July - Dry/Firm
    8: +5,   # August - Dry/Firm
    9: +2,   # September - Drier
    10: -2,  # October - Wetter
    11: -3,  # November - Wet
    12: -5,  # December - Very wet
}

def get_recent_rainfall(lat, lon, days=3):
    """
    Get rainfall data for last N days using Open-Meteo API (free, no key needed)
    Returns total rainfall in mm
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'daily': 'precipitation_sum',
        'timezone': 'Europe/London'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'daily' in data and 'precipitation_sum' in data['daily']:
            rainfall = data['daily']['precipitation_sum']
            total_rain = sum([r for r in rainfall if r is not None])
            return total_rain
        
    except Exception as e:
        print(f"  ⚠️ Weather API error: {e}")
    
    return None

def infer_going(rainfall_mm, surface_type='turf', month=None):
    """
    Infer going conditions from rainfall + seasonal factors
    
    Turf going categories:
    - Heavy: 20+ mm in last 3 days
    - Soft: 10-20 mm
    - Good to Soft: 5-10 mm  
    - Good: 2-5 mm
    - Good to Firm: 0-2 mm
    - Firm: No rain + sunny
    
    All-weather: Consistent surface, rainfall doesn't matter
    
    Seasonal adjustments:
    - Winter (Dec-Feb): -5 (softer ground typical)
    - Spring (Mar-Apr): -3 to -2 (transitional)
    - Summer (Jul-Aug): +5 (firmer ground typical)
    - Autumn (Sep-Nov): +2 to -3 (variable)
    """
    if surface_type == 'all-weather':
        return 'Standard (All-Weather)', 0, 'All-weather surface'  # No adjustment needed
    
    if rainfall_mm is None:
        return 'Unknown', 0, 'No weather data'
    
    # Get current month if not provided
    if month is None:
        month = datetime.now().month
    
    # Base going from rainfall
    if rainfall_mm >= 20:
        base_going = 'Heavy'
        base_adjustment = -10
    elif rainfall_mm >= 10:
        base_going = 'Soft'
        base_adjustment = -5
    elif rainfall_mm >= 5:
        base_going = 'Good to Soft'
        base_adjustment = -2
    elif rainfall_mm >= 2:
        base_going = 'Good'
        base_adjustment = +5
    else:
        base_going = 'Good to Firm'
        base_adjustment = +10
    
    # Apply seasonal factor (more conservative than base)
    seasonal_bias = SEASONAL_ADJUSTMENTS.get(month, 0)
    
    # Final adjustment is weighted average (70% rainfall, 30% seasonal)
    final_adjustment = int(base_adjustment * 0.7 + seasonal_bias * 0.3)
    
    # Determine final going description
    if final_adjustment <= -8:
        final_going = 'Heavy'
    elif final_adjustment <= -4:
        final_going = 'Soft'
    elif final_adjustment <= -1:
        final_going = 'Good to Soft'
    elif final_adjustment <= 3:
        final_going = 'Good'
    else:
        final_going = 'Good to Firm'
    
    # Explanation
    month_name = datetime(2000, month, 1).strftime('%B')
    if seasonal_bias < 0:
        explanation = f"{month_name} typical: softer ({seasonal_bias:+d})"
    elif seasonal_bias > 0:
        explanation = f"{month_name} typical: firmer ({seasonal_bias:+d})"
    else:
        explanation = f"{month_name}: neutral"
    
    return final_going, final_adjustment, explanation

def check_all_tracks_going(tracks=None):
    """Check going for all tracks or specified list with seasonal adjustments"""
    if tracks is None:
        tracks = list(TRACK_LOCATIONS.keys())
    
    results = {}
    current_month = datetime.now().month
    month_name = datetime.now().strftime('%B')
    seasonal_bias = SEASONAL_ADJUSTMENTS.get(current_month, 0)
    
    print(f"\n{'='*80}")
    print(f"WEATHER-BASED GOING INFERENCE (3-Day Rainfall + Seasonal Factor)")
    print(f"Current Month: {month_name} (Seasonal Bias: {seasonal_bias:+d})")
    print(f"{'='*80}\n")
    
    for track in tracks:
        if track not in TRACK_LOCATIONS:
            print(f"  ⚠️ {track} - Location unknown, skipping")
            continue
        
        location = TRACK_LOCATIONS[track]
        surface = location['surface']
        
        print(f"Checking {track} ({surface})...")
        
        rainfall = get_recent_rainfall(location['lat'], location['lon'])
        
        if rainfall is not None:
            going, adjustment, explanation = infer_going(rainfall, surface, current_month)
            results[track] = {
                'going': going,
                'rainfall_mm': rainfall,
                'adjustment': adjustment,
                'surface': surface,
                'seasonal_explanation': explanation
            }
            
            emoji = "🌧️" if rainfall > 10 else "☁️" if rainfall > 2 else "☀️"
            adj_text = f"+{adjustment}" if adjustment > 0 else str(adjustment) if adjustment < 0 else "±0"
            
            print(f"  {emoji} Rainfall: {rainfall:.1f}mm → Going: {going} (Score: {adj_text})")
            print(f"     {explanation}")
        else:
            results[track] = {
                'going': 'Unknown',
                'rainfall_mm': None,
                'adjustment': 0,
                'surface': surface
            }
            print(f"  ⚠️ Unable to fetch weather data")
        print()
    
    print(f"{'='*80}\n")
    return results

if __name__ == "__main__":
    # Test with today's tracks
    tracks = ['Carlisle', 'Taunton', 'Fairyhouse', 'Wolverhampton']
    going_data = check_all_tracks_going(tracks)
    
    print("Summary:")
    for track, data in going_data.items():
        print(f"  {track:20} {data['going']:25} Adjustment: {data['adjustment']:+3}")
