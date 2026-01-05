#!/usr/bin/env python3
"""
fetch_race_results.py - Fetch actual race results from Betfair to evaluate predictions

Note: For settled/historical markets, Betfair requires markets to be queried while they're still
available. For truly historical data, you need the Historical Data API (subscription required).
This script will attempt to fetch recent settled markets, but may not work for races >24hrs old.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
import pandas as pd

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

def load_betfair_creds():
    """Load Betfair credentials"""
    creds_path = "./betfair-creds.json"
    if not os.path.exists(creds_path):
        print(f"ERROR: {creds_path} not found", file=sys.stderr)
        sys.exit(1)
    
    with open(creds_path, 'r') as f:
        return json.load(f)

def get_market_results(market_ids: list[str], session_token: str, app_key: str) -> dict:
    """Fetch settled market results from Betfair"""
    
    # Use listMarketBook with betSettled status for historical results
    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/"
    
    headers = {
        "X-Application": app_key,
        "X-Authentication": session_token,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    results = []
    
    # Process markets in batches of 10 (API limit)
    for i in range(0, len(market_ids), 10):
        batch = market_ids[i:i+10]
        
        payload = {
            "marketIds": batch,
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS", "EX_TRADED"]
            },
            "orderProjection": "ALL",
            "matchProjection": "ROLLED_UP_BY_PRICE"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            batch_results = response.json()
            results.extend(batch_results if isinstance(batch_results, list) else [])
            print(f"  Fetched {len(batch)} markets (batch {i//10 + 1})")
        except Exception as e:
            print(f"  WARNING: Failed to fetch batch {i//10 + 1}: {e}", file=sys.stderr)
            continue
    
    return results

def parse_settled_markets(market_data: list) -> list[dict]:
    """Parse settled market data to extract winners"""
    results = []
    
    for market in market_data:
        market_id = market.get("marketId")
        status = market.get("status")
        
        # Markets can be CLOSED, SUSPENDED, or SETTLED
        if status not in ["CLOSED", "SETTLED"]:
            print(f"  Market {market_id}: status={status} (not settled yet)")
            continue
        
        runners = market.get("runners", [])
        for runner in runners:
            selection_id = runner.get("selectionId")
            runner_status = runner.get("status", "")
            
            results.append({
                "market_id": market_id,
                "selection_id": str(selection_id),
                "status": runner_status,  # WINNER, LOSER, PLACED, REMOVED
                "is_winner": runner_status == "WINNER",
                "is_placed": runner_status in ["WINNER", "PLACED"],
                "last_price_traded": runner.get("lastPriceTraded", 0.0)
            })
    
    print(f"  Parsed {len(results)} runner results from {len(market_data)} markets")
    return results

def fetch_results_for_date(date_str: str, session_token: str, app_key: str) -> pd.DataFrame:
    """Fetch all race results for a given date"""
    
    # First, get list of settled markets for that date
    # Note: This requires knowing the market IDs from your selections
    # In practice, you'd load from your selections CSV
    
    print(f"Fetching results for {date_str}...")
    print("NOTE: Requires market IDs from selections file")
    
    return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser(description="Fetch race results from Betfair")
    parser.add_argument("--date", type=str, default="", help="Date to fetch (YYYY-MM-DD, default: yesterday)")
    parser.add_argument("--selections", type=str, default="", help="Path to selections CSV with market_ids")
    parser.add_argument("--out", type=str, default="./results.json", help="Output JSON path")
    
    args = parser.parse_args()
    
    # Determine date
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = (datetime.now() - timedelta(days=1)).date()
    
    print(f"Fetching results for: {target_date}")
    
    # Load credentials
    creds = load_betfair_creds()
    session_token = creds.get("session_token", "")
    app_key = creds.get("app_key", "")
    
    if not session_token or not app_key:
        print("ERROR: Missing session_token or app_key in betfair-creds.json", file=sys.stderr)
        sys.exit(1)
    
    # Load selections to get market IDs
    if not args.selections:
        print("ERROR: --selections path required to get market IDs", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(args.selections):
        print(f"ERROR: Selections file not found: {args.selections}", file=sys.stderr)
        sys.exit(1)
    
    selections_df = pd.read_csv(args.selections)
    market_ids = selections_df["market_id"].astype(str).unique().tolist()
    
    print(f"Found {len(market_ids)} unique markets to check")
    
    # Calculate hours since race date
    hours_old = (datetime.now().date() - target_date).days * 24
    if hours_old > 48:
        print(f"\n⚠️  WARNING: Races are {hours_old/24:.1f} days old", file=sys.stderr)
        print("  Betfair free API typically only retains settled markets for 24-48 hours", file=sys.stderr)
        print("  Historical data requires Betfair Historical Data subscription", file=sys.stderr)
        print("  Attempting to fetch anyway...\n", file=sys.stderr)
    
    # Fetch results
    market_data = get_market_results(market_ids, session_token, app_key)
    
    if not market_data:
        print("\n❌ No market data returned - markets may be too old or API error", file=sys.stderr)
        print("  Creating empty results file to prevent re-attempts", file=sys.stderr)
        results = []
    else:
        results = parse_settled_markets(market_data)
    
    # Save results
    with open(args.out, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✓ Saved {len(results)} results to: {args.out}")

if __name__ == "__main__":
    main()
