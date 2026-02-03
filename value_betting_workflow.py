"""
WORKFLOW 2: Value Betting System
Runs 11am-7pm on 30min cycles
Looks for high-confidence VALUE bets using optimized logic
Only HIGH confidence picks (score >= 75) appear on UI
"""

import subprocess
import time
from datetime import datetime, timedelta


def is_within_trading_hours():
    """Check if current time is between 11am and 7pm"""
    now = datetime.now()
    start_hour = 11
    end_hour = 19  # 7pm
    
    return start_hour <= now.hour < end_hour


def fetch_races():
    """Fetch current race data"""
    print("\n📥 Fetching race data from Betfair...")
    result = subprocess.run(
        ['python', 'betfair_odds_fetcher.py'],
        capture_output=True,
        text=True,
        timeout=300
    )
    print("   ✓ Race data fetched")
    return result.returncode == 0


def analyze_and_generate_picks():
    """Analyze races with optimized logic and generate HIGH confidence picks"""
    print("\n🔍 Analyzing races for value bets (using learned weights)...")
    result = subprocess.run(
        ['python', 'analyze_all_races_comprehensive.py'],
        capture_output=True,
        text=True,
        timeout=600
    )
    
    # Parse output to show high-confidence picks
    lines = result.stdout.split('\n')
    for line in lines:
        if 'HIGH CONFIDENCE' in line or 'show_in_ui' in line or 'Score:' in line:
            print(line)
    
    return result.returncode == 0


def run_value_betting():
    """Main value betting loop - 11am to 7pm, every 30 minutes"""
    
    print("\n" + "="*80)
    print("VALUE BETTING SYSTEM STARTED")
    print("Trading Hours: 11:00 AM - 7:00 PM")
    print("Cycle Frequency: Every 30 minutes")
    print("Purpose: Find high-confidence value bets")
    print("UI Visibility: Only picks with score >= 75")
    print("="*80)
    
    cycle_count = 0
    
    while True:
        if not is_within_trading_hours():
            now = datetime.now()
            if now.hour < 11:
                wait_until = now.replace(hour=11, minute=0, second=0, microsecond=0)
                wait_seconds = (wait_until - now).total_seconds()
                print(f"\n⏰ Before trading hours. Waiting until 11:00 AM ({wait_seconds//60:.0f} minutes)")
                time.sleep(min(wait_seconds, 1800))
                continue
            else:
                print(f"\n🌙 Trading hours ended (7:00 PM). Stopping for today.")
                break
        
        cycle_count += 1
        print(f"\n{'='*80}")
        print(f"VALUE BETTING CYCLE #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        try:
            # Step 1: Fetch races
            fetch_races()
            
            # Step 2: Analyze and generate HIGH confidence picks
            analyze_and_generate_picks()
            
            # Wait 30 minutes
            next_run = datetime.now() + timedelta(minutes=30)
            print(f"\n⏳ Betting cycle complete. Next run at {next_run.strftime('%H:%M:%S')}")
            print(f"   Picks with score >= 75 are now visible on UI")
            print(f"   Sleeping for 30 minutes...")
            time.sleep(1800)
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Betting system stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Error in betting cycle: {str(e)}")
            import traceback
            traceback.print_exc()
            print("\n⏳ Waiting 5 minutes before retry...")
            time.sleep(300)
    
    print("\n" + "="*80)
    print("VALUE BETTING SYSTEM STOPPED")
    print(f"Total cycles completed: {cycle_count}")
    print("="*80)


if __name__ == "__main__":
    run_value_betting()
