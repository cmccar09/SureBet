#!/usr/bin/env python3
"""
Fetch greyhound race results from GBGB API and update database
Alternative to Betfair when authentication issues occur
"""
import json
import requests
import boto3
from datetime import datetime, timedelta
from collections import defaultdict

# AWS DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')

GBGB_API = "https://api.gbgb.org.uk/api/results"

print("=" * 70)
print("GBGB GREYHOUND RESULTS FETCHER")
print("=" * 70)

# Step 1: Get pending greyhound bets from database
print("\n[1/3] Loading pending greyhound bets from database...")
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
            # Only greyhounds without results
            if (not item.get('actual_result') and 
                item.get('race_type') == 'greyhound' and
                item.get('course') and
                item.get('race_time')):
                pending_bets.append(item)
                
    except Exception as e:
        print(f"  [ERROR] Database query failed for {date_str}: {e}")

print(f"  Found {len(pending_bets)} pending greyhound bets")

if not pending_bets:
    print("\n[OK] No pending greyhound bets")
    exit(0)

# Group by venue and date
races = defaultdict(list)
for bet in pending_bets:
    venue = bet.get('course', '').strip()
    race_time = bet.get('race_time', '')
    
    # Extract date and time
    if 'T' in race_time:
        race_date = race_time.split('T')[0]
        time_part = race_time.split('T')[1][:5]  # HH:MM
    else:
        race_date = bet.get('bet_date')
        time_part = race_time[:5] if len(race_time) >= 5 else ''
    
    key = (venue, race_date, time_part)
    races[key].append(bet)

print(f"  {len(races)} unique races")

# Step 2: Fetch results from GBGB API
print("\n[2/3] Fetching race results from GBGB API...")

updated_count = 0
no_results_count = 0

for i, ((venue, race_date, race_time), bets) in enumerate(races.items(), 1):
    print(f"\n  [{i}/{len(races)}] {venue} - {race_date} {race_time}")
    
    # Query GBGB API for this venue/date
    try:
        # Try exact venue name first
        params = {
            'track': venue,
            'date': race_date
        }
        
        response = requests.get(GBGB_API, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"    [ERROR] HTTP {response.status_code}")
            no_results_count += len(bets)
            continue
        
        data = response.json()
        
        if not data or 'results' not in data:
            print(f"    [NO DATA] No results found for this venue/date")
            no_results_count += len(bets)
            continue
        
        # Find matching race by time
        matching_race = None
        for race_result in data['results']:
            result_time = race_result.get('time', '')[:5]  # HH:MM
            if result_time == race_time:
                matching_race = race_result
                break
        
        if not matching_race:
            # Try finding by race distance or grade
            for bet in bets:
                distance = bet.get('distance', '')
                for race_result in data['results']:
                    if str(race_result.get('distance', '')) == str(distance):
                        matching_race = race_result
                        break
                if matching_race:
                    break
        
        if not matching_race:
            print(f"    [NO MATCH] No race found for time {race_time}")
            no_results_count += len(bets)
            continue
        
        # Extract finishing positions
        runners = matching_race.get('runners', [])
        if not runners:
            print(f"    [NO RUNNERS] Race has no runner data")
            no_results_count += len(bets)
            continue
        
        # Build position mapping
        positions = {}
        for runner in runners:
            dog_name = runner.get('dog_name', '').strip().upper()
            position = runner.get('position', 0)
            trap = runner.get('trap', 0)
            positions[dog_name] = position
            positions[f"TRAP{trap}"] = position
        
        print(f"    Race finished: {len(runners)} runners")
        
        # Update each bet
        for bet in bets:
            dog_name = bet.get('horse', '').strip().upper()  # 'horse' field stores greyhound name
            trap = bet.get('trap_number', '')
            
            # Try to find position
            position = None
            if dog_name in positions:
                position = positions[dog_name]
            elif trap and f"TRAP{trap}" in positions:
                position = positions[f"TRAP{trap}"]
            
            if position is None:
                print(f"    [SKIP] {dog_name}: Not found in results")
                no_results_count += 1
                continue
            
            # Determine result
            if position == 1:
                result = 'WON'
            elif position <= 3:  # Each-way places typically 1-3 for greyhounds
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
                        ':pos': int(position)
                    }
                )
                
                print(f"    [OK] {dog_name} (T{trap}): P{position} = {result}")
                updated_count += 1
                
            except Exception as e:
                print(f"    [ERROR] DB update failed for {dog_name}: {e}")
                no_results_count += 1
        
    except requests.exceptions.RequestException as e:
        print(f"    [ERROR] API request failed: {str(e)[:60]}")
        no_results_count += len(bets)
    except Exception as e:
        print(f"    [ERROR] Processing failed: {str(e)[:60]}")
        no_results_count += len(bets)

# Step 3: Summary
print("\n" + "=" * 70)
print(f"RESULTS:")
print(f"  Updated: {updated_count}/{len(pending_bets)} bets")
print(f"  No results: {no_results_count}/{len(pending_bets)} bets")
print(f"  Success rate: {(updated_count/len(pending_bets)*100):.1f}%")
print("=" * 70)

if updated_count > 0:
    print("\n[TIP] Run generate_learning_insights.py to analyze performance")
