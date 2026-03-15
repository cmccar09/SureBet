"""
auto_refresh_betfair.py
-----------------------
Regular daily refresh (post-Cheltenham): runs 3x per day at 12:00, 14:00, 16:00 local time.

Pipeline:
  1. betfair_odds_fetcher.py   → fetches next 3 days of races → response_horses.json
  2. complete_daily_analysis.py → scores all horses, picks top 5 for UI, saves to DynamoDB

Usage:
    python auto_refresh_betfair.py           # normal run (always executes)
    python auto_refresh_betfair.py --dry-run  # print steps only, no execution
"""
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
PYTHON   = str(BASE_DIR / ".venv" / "Scripts" / "python.exe")
LOG_FILE = BASE_DIR / "auto_refresh.log"

# ── Pipeline steps ────────────────────────────────────────────────────────────
# Each tuple: (script_filename, short_label, abort_on_failure)
PIPELINE = [
    ("betfair_odds_fetcher.py",   "Fetch Betfair odds (next 3 days)", True),
    ("complete_daily_analysis.py", "Score all horses + build top-5 UI picks", False),
]


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def run_py(script: str, label: str, dry_run: bool = False) -> bool:
    """Run a Python script from BASE_DIR. Returns True on success."""
    path = BASE_DIR / script
    if not path.exists():
        log(f"SKIP (not found): {script}")
        return True  # non-fatal — don't abort pipeline

    if dry_run:
        log(f"DRY-RUN: would run {script}")
        return True

    log(f"Running: {label} ...")
    result = subprocess.run(
        [PYTHON, str(path)],
        capture_output=True, text=True,
        cwd=str(BASE_DIR), timeout=180
    )

    # Surface notable output lines
    for line in result.stdout.splitlines():
        if any(kw in line for kw in ["ERROR", "WARNING", "PICK", "✅", "❌", "top", "saved", "Total"]):
            log(f"  >> {line.strip()}")

    if result.returncode != 0:
        log(f"ERROR [{label}]:\n{result.stderr[-800:]}")
        return False

    log(f"OK: {label}")
    return True


def main():
    dry_run = "--dry-run" in sys.argv
    log("=" * 60)
    log(f"auto_refresh_betfair.py  {'(DRY-RUN) ' if dry_run else ''}starting")
    log(f"Time: {datetime.now().strftime('%A %d %b %Y %H:%M')}")

    for script, label, abort_on_fail in PIPELINE:
        ok = run_py(script, label, dry_run=dry_run)
        if not ok and abort_on_fail:
            log(f"Aborting pipeline after failure in: {label}")
            break

    log("Refresh cycle complete")
    log("=" * 60)


if __name__ == "__main__":
    main()

