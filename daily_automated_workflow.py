"""
Daily Automated Learning - Complete Workflow
Runs automatically every day to:
1. Fetch yesterday's results
2. Analyze performance
3. Auto-adjust weights
4. Generate today's picks
"""

import subprocess
import sys
from datetime import datetime, timedelta

def run_step(description, command):
    """Run a workflow step with logging"""
    print(f"\n{'='*80}")
    print(f"STEP: {description}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"\n⚠️ WARNING: {description} returned code {result.returncode}")
            print(result.stderr)
            return False
        
        print(f"\n✓ {description} completed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"\n❌ ERROR: {description} timed out")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {description} failed: {str(e)}")
        return False


def main():
    """Run complete daily workflow"""
    
    print(f"""
{'='*80}
DAILY AUTOMATED LEARNING WORKFLOW
{'='*80}
Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}
""")
    
    # STEP 1: Fetch results for yesterday's picks
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    run_step(
        "Fetch yesterday's race results",
        f"python betfair_results_fetcher_v2.py --date {yesterday}"
    )
    
    # STEP 2: Auto-adjust weights based on results
    success = run_step(
        "Auto-adjust scoring weights based on performance",
        "python auto_adjust_weights.py"
    )
    
    if success:
        print("\n🎯 Weights have been automatically optimized based on yesterday's results")
    
    # STEP 3: Fetch today's races
    run_step(
        "Fetch today's race data",
        "python betfair_odds_fetcher.py"
    )
    
    # STEP 4: Analyze races with NEW weights
    run_step(
        "Analyze races using updated weights",
        "python comprehensive_workflow.py"
    )
    
    # Summary
    print(f"""
{'='*80}
WORKFLOW COMPLETE
{'='*80}
Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

WHAT HAPPENED:
1. ✓ Fetched yesterday's results
2. ✓ Analyzed performance patterns
3. ✓ Automatically adjusted scoring weights
4. ✓ Fetched today's races
5. ✓ Generated picks using optimized weights

NEXT STEPS:
- Picks are now in DynamoDB with updated confidence scores
- Lambda/API will show only HIGH confidence picks (score >= 75)
- System will repeat tomorrow with further optimized weights

CONTINUOUS IMPROVEMENT:
The system learns from every day's results and automatically
adjusts its scoring algorithm to improve future predictions.
{'='*80}
""")


if __name__ == "__main__":
    main()
