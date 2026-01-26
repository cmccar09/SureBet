import json

# Load results
with open('results.json', 'r') as f:
    data = json.load(f)

print("\n=== SEDGEFIELD 15:10 RACE RESULTS ===\n")

# Handle both formats
races = data if isinstance(data, list) else data.get('results', [])

# Find the race
for race in races:
    start_time = race.get('start_time', '')
    venue = race.get('venue', '')
    
    if '15:10' in start_time or 'T15:10' in start_time:
        print(f"Race: {race.get('market_name', 'Unknown')} @ {venue}")
        print(f"Time: {start_time}\n")
        
        # Get our picks
        our_picks = ['Celestial Reign', 'Fromheretoeternity']
        
        # Show all finishers
        for result in race.get('results', []):
            runner = result.get('runner_name', 'Unknown')
            position = result.get('position', 'N/A')
            
            marker = ""
            if runner in our_picks:
                marker = " ← OUR PICK"
            
            print(f"Position {position}: {runner}{marker}")
