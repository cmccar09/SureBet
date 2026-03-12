"""
auto_refresh_betfair.py
-----------------------
Automated 30-minute refresh: pull live Betfair odds → re-score → save to DynamoDB → deploy Lambda.
Run by Windows Task Scheduler every 30 mins during Festival days (07:00–19:00 UTC).

Usage:
    python auto_refresh_betfair.py [--force]   # --force skips time-window check
"""
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR   = Path(__file__).parent
PYTHON     = str(BASE_DIR / ".venv" / "Scripts" / "python.exe")
POWERSHELL = "powershell.exe"
LOG_FILE   = BASE_DIR / "auto_refresh.log"

# Only run between 07:00 and 19:00 UTC on Festival days
FESTIVAL_DAYS  = {"2026-03-10", "2026-03-11", "2026-03-12", "2026-03-13"}
START_HOUR_UTC = 7
END_HOUR_UTC   = 19

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def within_window():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    if today not in FESTIVAL_DAYS:
        return False
    return START_HOUR_UTC <= now.hour < END_HOUR_UTC

def run_py(script, label):
    result = subprocess.run(
        [PYTHON, str(BASE_DIR / script)],
        capture_output=True, text=True, cwd=str(BASE_DIR), timeout=120
    )
    if result.returncode != 0:
        log(f"ERROR [{label}]:\n{result.stderr[-600:]}")
        return False
    # Scan output for NR warnings
    for line in result.stdout.splitlines():
        if any(kw in line for kw in ["NR", "CHANGED", "non-runner", "ERROR", "WARNING"]):
            log(f"  >> {line.strip()}")
    log(f"OK: {label}")
    return True

def run_ps(script, label):
    result = subprocess.run(
        [POWERSHELL, "-NonInteractive", "-File", str(BASE_DIR / script)],
        capture_output=True, text=True, cwd=str(BASE_DIR), timeout=120
    )
    if result.returncode != 0:
        log(f"ERROR [{label}]:\n{result.stderr[-400:]}")
        return False
    if "DEPLOYMENT COMPLETE" in result.stdout or "COMPLETE" in result.stdout:
        log(f"OK: {label} — deployed successfully")
    else:
        log(f"OK: {label}")
    return True

def main():
    force = "--force" in sys.argv
    log("=" * 60)
    log(f"auto_refresh_betfair.py starting (force={force})")

    if not force and not within_window():
        log("Outside refresh window — exiting")
        return

    # Step 1: Fetch fresh Betfair odds + NR detection
    log("Step 1: Fetching live Betfair race cards...")
    ok = run_py("fetch_cheltenham_racecards.py", "fetch_cheltenham_racecards")
    if not ok:
        log("WARNING: Betfair fetch failed — continuing with cached prices")

    # Step 2: Re-score and save picks to DynamoDB
    log("Step 2: Re-scoring and saving picks...")
    if not run_py("save_cheltenham_picks.py", "save_cheltenham_picks"):
        log("ERROR: save_cheltenham_picks failed — aborting deploy")
        return

    # Step 3: Deploy Lambda
    log("Step 3: Deploying Lambda...")
    run_ps("deploy_cheltenham_save_lambda.ps1", "deploy_cheltenham_save_lambda")

    log("Refresh complete")
    log("=" * 60)

if __name__ == "__main__":
    main()
