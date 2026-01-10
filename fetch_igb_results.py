#!/usr/bin/env python3
"""
fetch_igb_results.py
Scrapes Irish Greyhound Board (IGB) results for past performance data
Collects winning times, trap positions, and track bias information
"""

import requests
from bs4 import BeautifulSoup
import json
import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

# Irish greyhound tracks
IRISH_TRACKS = {
    'shelbourne': 'Shelbourne Park',
    'cork': 'Cork',
    'limerick': 'Limerick',
    'galway': 'Galway',
    'dundalk': 'Dundalk',
    'tralee': 'Tralee',
    'kilkenny': 'Kilkenny',
    'mullingar': 'Mullingar',
    'clonmel': 'Clonmel',
    'thurles': 'Thurles',
    'longford': 'Longford',
    'youghal': 'Youghal'
}

def fetch_igb_race_results(date_str):
    """
    Fetch IGB race results for a specific date
    
    Args:
        date_str: Date in YYYY-MM-DD format
    
    Returns:
        List of race results
    """
    results = []
    
    # IGB website structure (this is an example - actual structure may vary)
    # You may need to inspect the actual website to get the correct URLs
    base_url = "https://www.igb.ie"
    
    try:
        # Try to fetch results page
        # Note: IGB website structure may require different approach
        # This is a template that needs to be adjusted based on actual site
        
        results_url = f"{base_url}/racing/results"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(results_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Parse race results (structure depends on actual website)
        # This is a placeholder - needs actual HTML structure
        race_cards = soup.find_all('div', class_='race-result')
        
        for card in race_cards:
            try:
                race_info = {
                    'date': date_str,
                    'track': extract_track_name(card),
                    'race_time': extract_race_time(card),
                    'distance': extract_distance(card),
                    'winners': extract_race_winners(card),
                    'trap_times': extract_trap_times(card)
                }
                results.append(race_info)
            except Exception as e:
                print(f"Error parsing race card: {e}", file=sys.stderr)
                continue
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IGB results: {e}", file=sys.stderr)
        # Fallback: Try alternative source or return empty
        pass
    
    return results

def extract_track_name(card_element):
    """Extract track name from race card HTML"""
    # Placeholder - adjust based on actual HTML structure
    track_elem = card_element.find('span', class_='track-name')
    return track_elem.text.strip() if track_elem else 'Unknown'

def extract_race_time(card_element):
    """Extract race time from card"""
    time_elem = card_element.find('span', class_='race-time')
    return time_elem.text.strip() if time_elem else None

def extract_distance(card_element):
    """Extract race distance"""
    dist_elem = card_element.find('span', class_='distance')
    return dist_elem.text.strip() if dist_elem else '525m'

def extract_race_winners(card_element):
    """Extract winning dog information"""
    winners = []
    
    # Find results table (adjust selectors based on actual HTML)
    results_table = card_element.find('table', class_='results')
    if results_table:
        rows = results_table.find_all('tr')[1:]  # Skip header
        
        for row in rows[:3]:  # Top 3 finishers
            cells = row.find_all('td')
            if len(cells) >= 4:
                winner = {
                    'position': cells[0].text.strip(),
                    'trap': cells[1].text.strip(),
                    'dog_name': cells[2].text.strip(),
                    'time': cells[3].text.strip()
                }
                winners.append(winner)
    
    return winners

def extract_trap_times(card_element):
    """Extract all trap times for bias analysis"""
    trap_times = {}
    
    results_table = card_element.find('table', class_='results')
    if results_table:
        rows = results_table.find_all('tr')[1:]
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                trap = cells[1].text.strip()
                time = cells[3].text.strip()
                trap_times[trap] = time
    
    return trap_times

def analyze_track_bias(results):
    """
    Analyze trap bias from historical results
    
    Returns:
        Dictionary with trap win percentages per track
    """
    trap_wins = defaultdict(lambda: defaultdict(int))
    trap_counts = defaultdict(int)
    
    for race in results:
        track = race.get('track', 'Unknown')
        winners = race.get('winners', [])
        
        if winners and len(winners) > 0:
            winning_trap = winners[0].get('trap', '')
            if winning_trap:
                trap_wins[track][winning_trap] += 1
                trap_counts[track] += 1
    
    # Calculate percentages
    bias_analysis = {}
    for track, traps in trap_wins.items():
        total = trap_counts[track]
        bias_analysis[track] = {
            trap: round((count / total) * 100, 1)
            for trap, count in traps.items()
        }
    
    return bias_analysis

def fetch_results_for_days(days=7):
    """Fetch results for the last N days"""
    all_results = []
    
    for i in range(days):
        date = datetime.now() - timedelta(days=i+1)
        date_str = date.strftime('%Y-%m-%d')
        
        print(f"Fetching results for {date_str}...")
        results = fetch_igb_race_results(date_str)
        all_results.extend(results)
    
    return all_results

def main():
    parser = argparse.ArgumentParser(description="Fetch Irish Greyhound Board results")
    parser.add_argument('--days', type=int, default=7,
                        help='Number of days of historical results to fetch (default: 7)')
    parser.add_argument('--out', type=str, default='igb_results.json',
                        help='Output JSON file (default: igb_results.json)')
    parser.add_argument('--analyze-bias', action='store_true',
                        help='Analyze and output trap bias statistics')
    
    args = parser.parse_args()
    
    print(f"Fetching IGB results for last {args.days} days...")
    results = fetch_results_for_days(args.days)
    
    print(f"Fetched {len(results)} race results")
    
    # Analyze trap bias if requested
    if args.analyze_bias:
        print("\nAnalyzing trap bias...")
        bias_analysis = analyze_track_bias(results)
        
        print("\n=== TRAP BIAS ANALYSIS ===")
        for track, traps in bias_analysis.items():
            print(f"\n{track}:")
            for trap, percentage in sorted(traps.items()):
                print(f"  Trap {trap}: {percentage}% wins")
    
    # Save results
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'days_analyzed': args.days,
        'total_races': len(results),
        'results': results
    }
    
    if args.analyze_bias:
        output_data['trap_bias'] = analyze_track_bias(results)
    
    with open(args.out, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✓ Results saved to {args.out}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
