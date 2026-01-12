#!/usr/bin/env python3
"""
Fetch horse racing results from Racing Post (alternative to Betfair)
Uses public results pages instead of API
"""
import json
import requests
import boto3
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import time

# AWS DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

print("=" * 70)
print("RACING POST RESULTS SCRAPER")
print("=" * 70)

# Step 1: Get pending bets from database
print("\n[1/3] Loading pending bets from database...")
pending_bets = []

for i in range(5):  # Last 5 days
    date_str = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
    try:
        response = table.query(
            KeyConditionExpression='bet_date = :date',
            ExpressionAttributeValues={':date': date_str}
        )
        
        items = response.get('Items', [])
        for item in items:
            if not item.get('actual_result') and item.get('course') and item.get('race_time'):
                pending_bets.append(item)
                
    except Exception as e:
        print(f"  [ERROR] Database query failed for {date_str}: {e}")

print(f"  Found {len(pending_bets)} pending bets")

if not pending_bets:
    print("\n[OK] No pending bets")
    exit(0)

# Step 2: Fetch results from Racing Post
print("\n[2/3] Fetching results from Racing Post...")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.9',
    'Referer': 'https://www.racingpost.com/'
}

updated_count = 0
failed_count = 0

# Group by date and venue
from collections import defaultdict
races_by_date_venue = defaultdict(list)

for bet in pending_bets:
    race_time = bet.get('race_time', '')
    if 'T' in race_time:
        date_part = race_time.split('T')[0]
    else:
        date_part = bet.get('bet_date')
    
    venue = bet.get('course', '').strip()
    races_by_date_venue[(date_part, venue)].append(bet)

print(f"  {len(races_by_date_venue)} unique date/venue combinations")

for i, ((date, venue), bets) in enumerate(races_by_date_venue.items(), 1):
    print(f"\n  [{i}/{len(races_by_date_venue)}] {venue} - {date}")
    
    # Convert date format for Racing Post URL
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    rp_date = date_obj.strftime('%Y-%m-%d')
    
    # Clean venue name for URL
    venue_slug = venue.lower().replace(' ', '-').replace("'", '')
    
    # Try Racing Post results page
    url = f"https://www.racingpost.com/results/{rp_date}/{venue_slug}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 406:
            print(f"    [BLOCKED] Racing Post blocking automated access")
            failed_count += len(bets)
            continue
        
        if response.status_code != 200:
            print(f"    [ERROR] HTTP {response.status_code}")
            failed_count += len(bets)
            continue
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find race cards/results
        race_cards = soup.find_all('div', class_=re.compile(r'race.*card|result'))
        
        if not race_cards:
            print(f"    [NO DATA] No race results found on page")
            failed_count += len(bets)
            continue
        
        print(f"    Found {len(race_cards)} races")
        
        # Process each bet for this venue/date
        for bet in bets:
            horse_name = bet.get('horse', '').strip().upper()
            race_time = bet.get('race_time', '')
            
            # Extract time
            if 'T' in race_time:
                time_str = race_time.split('T')[1][:5]  # HH:MM
            else:
                time_str = ''
            
            # Try to find matching race result
            result_found = False
            
            for card in race_cards:
                # Check if horse appears in this race
                horse_links = card.find_all('a', string=re.compile(horse_name, re.I))
                
                if horse_links:
                    # Found the horse - determine position
                    for link in horse_links:
                        parent = link.find_parent('tr') or link.find_parent('div')
                        if parent:
                            # Look for position indicator
                            position_elem = parent.find(class_=re.compile(r'position|place|finish'))
                            if position_elem:
                                pos_text = position_elem.get_text().strip()
                                try:
                                    position = int(re.search(r'\d+', pos_text).group())
                                    
                                    # Determine result
                                    if position == 1:
                                        result = 'WON'
                                    elif position <= 4:  # E/W typically pays 1-4
                                        result = 'PLACED'
                                    else:
                                        result = 'LOST'
                                    
                                    # Update database
                                    try:
                                        table.update_item(
                                            Key={
                                                'bet_date': bet['bet_date'],
                                                'bet_id': bet['bet_id']
                                            },
                                            UpdateExpression='SET actual_result = :result, finishing_position = :pos',
                                            ExpressionAttributeValues={
                                                ':result': result,
                                                ':pos': position
                                            }
                                        )
                                        
                                        print(f"    [OK] {horse_name}: P{position} = {result}")
                                        updated_count += 1
                                        result_found = True
                                        break
                                        
                                    except Exception as e:
                                        print(f"    [ERROR] DB update failed: {e}")
                                        failed_count += 1
                                except:
                                    pass
            
            if not result_found:
                failed_count += 1
        
        time.sleep(2)  # Rate limiting
        
    except Exception as e:
        print(f"    [ERROR] {str(e)[:60]}")
        failed_count += len(bets)

# Step 3: Summary
print("\n" + "=" * 70)
print(f"RESULTS:")
print(f"  Updated: {updated_count}/{len(pending_bets)} bets")
print(f"  Failed: {failed_count}/{len(pending_bets)} bets")
if len(pending_bets) > 0:
    print(f"  Success rate: {(updated_count/len(pending_bets)*100):.1f}%")
print("=" * 70)

if updated_count > 0:
    print("\n[TIP] Run generate_learning_insights.py to analyze performance")
