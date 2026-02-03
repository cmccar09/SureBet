"""
WORKFLOW 1: Background Learning System
Runs 11am-7pm on 30min cycles
Analyzes ALL races, stores ALL horses, learns from winners
Everything saved to database with show_in_ui=False (NOT visible on UI)
"""

import subprocess
import time
from datetime import datetime, timedelta
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('SureBetBets')


def is_within_trading_hours():
    """Check if current time is between 11am and 7pm"""
    now = datetime.now()
    start_hour = 11
    end_hour = 19  # 7pm
    
    return start_hour <= now.hour < end_hour


def check_data_quality():
    """Check data quality before processing"""
    print("\n" + "="*80)
    print("DATA QUALITY CHECK")
    print("="*80)
    
    result = subprocess.run(
        ['python', 'data_quality_monitor.py'],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    # Show critical issues and warnings
    lines = result.stdout.split('\n')
    for line in lines:
        if '🔴' in line or '⚠️' in line or 'CRITICAL' in line or 'WARNING' in line:
            print(line)
    
    return True  # Continue even if issues found (for learning)


def store_all_races_for_learning():
    """Store ALL horses from ALL races - this is LEARNING data, not picks"""
    print("\n" + "="*80)
    print("STORING ALL RACES FOR LEARNING (Background Analysis)")
    print("="*80)
    
    result = subprocess.run(
        ['python', 'complete_race_learning.py', 'store'],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    print(result.stdout)
    return result.returncode == 0


def analyze_winners_and_learn():
    """Compare stored horses with actual winners - learn WHY they won"""
    print("\n" + "="*80)
    print("ANALYZING WINNERS - Learning Patterns")
    print("="*80)
    
    result = subprocess.run(
        ['python', 'complete_race_learning.py', 'learn'],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    print(result.stdout)
    return result.returncode == 0


def fetch_latest_results():
    """Fetch results for completed races"""
    print("\n" + "="*80)
    print("FETCHING RESULTS FOR COMPLETED RACES")
    print("="*80)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    result = subprocess.run(
        ['python', 'betfair_results_fetcher_v2.py', '--date', today],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    print(result.stdout)
    return result.returncode == 0


def auto_adjust_logic():
    """Auto-adjust scoring weights based on what's actually winning"""
    print("\n" + "="*80)
    print("AUTO-ADJUSTING SCORING LOGIC")
    print("="*80)
    
    result = subprocess.run(
        ['python', 'auto_adjust_weights.py'],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    print(result.stdout)
    return result.returncode == 0


def log_learning_cycle(cycle_num, stored_count, learned_count, adjusted):
    """Log this learning cycle to database"""
    today = datetime.now().strftime('%Y-%m-%d')
    timestamp = datetime.now().isoformat()
    
    record = {
        'bet_id': f'LEARNING_CYCLE_{timestamp.replace(":", "").replace("-", "").replace(".", "_")}',
        'bet_date': today,
        'learning_type': 'BACKGROUND_CYCLE',
        'cycle_number': cycle_num,
        'horses_stored': stored_count,
        'winners_analyzed': learned_count,
        'logic_adjusted': adjusted,
        'timestamp': timestamp,
        'show_in_ui': False,
        'is_learning_pick': True
    }
    
    table.put_item(Item=record)
    print(f"\n✓ Learning cycle #{cycle_num} logged to database")


def run_background_learning():
    """Main background learning loop - 11am to 7pm, every 30 minutes"""
    
    print("\n" + "="*80)
    print("BACKGROUND LEARNING SYSTEM STARTED")
    print("Trading Hours: 11:00 AM - 7:00 PM")
    print("Cycle Frequency: Every 30 minutes")
    print("Purpose: Learn from ALL races, improve logic")
    print("UI Visibility: NONE (all data stored in database only)")
    print("="*80)
    
    cycle_count = 0
    
    while True:
        if not is_within_trading_hours():
            now = datetime.now()
            if now.hour < 11:
                wait_until = now.replace(hour=11, minute=0, second=0, microsecond=0)
                wait_seconds = (wait_until - now).total_seconds()
                print(f"\n⏰ Before trading hours. Waiting until 11:00 AM ({wait_seconds//60:.0f} minutes)")
                time.sleep(min(wait_seconds, 1800))  # Sleep max 30 min at a time
                continue
            else:
                print(f"\n🌙 Trading hours ended (7:00 PM). Stopping for today.")
                break
        
        cycle_count += 1
        print(f"\n{'='*80}")
        print(f"LEARNING CYCLE #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        try:
            # Step 1: Fetch latest race data
            print("\n📥 Fetching latest race data...")
            subprocess.run(['python', 'betfair_odds_fetcher.py'], timeout=300)
            
            # Step 1.5: Check data quality
            check_data_quality()
            
            # Step 2: Store ALL horses from ALL races for learning
            print("\n📊 Storing all horses for learning analysis...")
            stored = store_all_races_for_learning()
            
            # Step 3: Fetch results for completed races
            print("\n🏁 Fetching results...")
            fetch_latest_results()
            
            # Step 4: Analyze winners - learn WHY they won
            print("\n🧠 Analyzing winners and learning patterns...")
            learned = analyze_winners_and_learn()
            
            # Step 5: Auto-adjust scoring logic based on learnings
            print("\n⚙️ Auto-adjusting scoring weights...")
            adjusted = auto_adjust_logic()
            
            # Step 6: Log this cycle
            log_learning_cycle(cycle_count, 0, 0, adjusted)
            
            # Wait 30 minutes
            next_run = datetime.now() + timedelta(minutes=30)
            print(f"\n⏳ Learning cycle complete. Next run at {next_run.strftime('%H:%M:%S')}")
            print(f"   Sleeping for 30 minutes...")
            time.sleep(1800)
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Learning system stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Error in learning cycle: {str(e)}")
            import traceback
            traceback.print_exc()
            print("\n⏳ Waiting 5 minutes before retry...")
            time.sleep(300)
    
    print("\n" + "="*80)
    print("BACKGROUND LEARNING SYSTEM STOPPED")
    print(f"Total cycles completed: {cycle_count}")
    print("="*80)


if __name__ == "__main__":
    run_background_learning()
