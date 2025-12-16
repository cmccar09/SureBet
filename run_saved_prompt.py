#!/usr/bin/env python3
"""
run_saved_prompt.py - Integrates prompt.txt logic with Betfair market data
Sends prompt + race data to LLM, parses selections back to CSV format
"""

import os
import sys
import argparse
import glob
import json
import csv
import io
from pathlib import Path
from datetime import datetime, timezone

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

REQUIRED_COLUMNS = [
    "runner_name", "selection_id", "market_id", "market_name", "venue", 
    "start_time_dublin", "p_win", "p_place", "ew_places", "ew_fraction", 
    "tags", "why_now"
]

def load_prompt_text(prompt_path: str = "./prompt.txt") -> str:
    """Load the betting prompt from file"""
    if not os.path.exists(prompt_path):
        print(f"ERROR: Prompt file not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def discover_latest_snapshot() -> str | None:
    """Find the most recent snapshot file"""
    patterns = [
        "./snapshots/run_*_once.csv",
        "./snapshots/*.csv",
        "./*snapshot*.csv",
        "./response*.json"  # fallback to JSON responses
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    return None

def load_market_data(snapshot_path: str) -> pd.DataFrame:
    """Load market data from CSV or JSON"""
    if not HAS_PANDAS:
        print("ERROR: pandas not installed. Run: pip install pandas", file=sys.stderr)
        sys.exit(1)
    
    ext = os.path.splitext(snapshot_path)[1].lower()
    
    if ext == '.json':
        # Handle JSON format (from betfair responses)
        with open(snapshot_path, 'r') as f:
            data = json.load(f)
        
        # Extract races array from response
        races = []
        if isinstance(data, list):
            races = data
        elif isinstance(data, dict):
            # Try different keys
            races = data.get('races', data.get('result', data.get('markets', data.get('data', []))))
        
        if not races:
            print(f"WARNING: No races found in JSON. Keys: {data.keys() if isinstance(data, dict) else 'list'}")
            return pd.DataFrame()
        
        # Flatten to DataFrame
        rows = []
        for race in races:
            if not isinstance(race, dict):
                continue
            market_id = race.get('market_id', race.get('marketId', 'UNKNOWN'))
            market_name = race.get('market_name', race.get('marketName', ''))
            venue = race.get('venue', race.get('course', race.get('event', {}).get('venue', '')))
            start_time = race.get('start_time', race.get('marketStartTime', ''))
            
            runners = race.get('runners', [])
            for runner in runners:
                rows.append({
                    'market_id': market_id,
                    'market_name': market_name,
                    'venue': venue,
                    'start_time_dublin': start_time,
                    'runner_name': runner.get('name', runner.get('runnerName', '')),
                    'selection_id': runner.get('selectionId', ''),
                    'best_back': runner.get('ex', {}).get('availableToBack', [{}])[0].get('price', ''),
                    'best_lay': runner.get('ex', {}).get('availableToLay', [{}])[0].get('price', ''),
                })
        df = pd.DataFrame(rows)
    else:
        # CSV format
        df = pd.read_csv(snapshot_path)
    
    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def format_race_data_for_llm(race_df: pd.DataFrame, meta: dict) -> str:
    """Format a single race's data for the LLM prompt"""
    race_info = f"""
Race: {meta.get('market_name', 'Unknown')}
Venue: {meta.get('venue', 'Unknown')}
Start Time: {meta.get('start_time', 'Unknown')}
Market ID: {meta.get('market_id', 'Unknown')}

Runners:
"""
    
    # Build runner table
    for idx, row in race_df.iterrows():
        runner_name = row.get('runner_name', 'Unknown')
        selection_id = row.get('selection_id', '')
        best_back = row.get('best_back', row.get('price', row.get('decimal_odds', '')))
        best_lay = row.get('best_lay', '')
        
        race_info += f"- {runner_name} (ID: {selection_id}), Back: {best_back}"
        if best_lay:
            race_info += f", Lay: {best_lay}"
        race_info += "\n"
    
    return race_info

def call_llm_for_race(prompt_text: str, race_data: str, provider: str = "auto") -> str:
    """Call LLM with prompt + race data, return response"""
    
    full_prompt = f"""{prompt_text}

===== RACE DATA =====
{race_data}

===== INSTRUCTIONS =====
Analyze this race using the prompt logic above. Return ONLY the selections in CSV format with these exact columns:
runner_name,selection_id,market_id,market_name,venue,start_time_dublin,p_win,p_place,ew_places,ew_fraction,tags,why_now

If no selections meet the thresholds, return just the header row.
"""
    
    # Determine provider
    if provider == "auto":
        if HAS_BOTO3:  # Prefer AWS Bedrock (no API key needed)
            provider = "bedrock"
        elif HAS_ANTHROPIC and os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif HAS_OPENAI and os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        else:
            print("ERROR: No API access found. Configure AWS credentials or set ANTHROPIC_API_KEY/OPENAI_API_KEY", file=sys.stderr)
            sys.exit(1)
    
    try:
        if provider == "bedrock":
            bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": full_prompt}]
            })
            
            response = bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        
        elif provider == "anthropic":
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": full_prompt}]
            )
            return response.content[0].text
        
        elif provider == "openai":
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        
    except Exception as e:
        print(f"ERROR calling {provider} API: {e}", file=sys.stderr)
        return ""

def parse_csv_response(response_text: str) -> list[dict]:
    """Parse LLM CSV response into structured data"""
    # Remove markdown code fences if present
    text = response_text.strip()
    if text.startswith("```"):
        lines = [ln for ln in text.split("\n") if not ln.strip().startswith("```")]
        text = "\n".join(lines)
    
    # Find header row
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    header_idx = -1
    for i, line in enumerate(lines):
        if "runner_name" in line.lower() and "p_win" in line.lower():
            header_idx = i
            break
    
    if header_idx == -1:
        return []
    
    # Parse CSV
    csv_text = "\n".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(csv_text))
    
    rows = []
    for row in reader:
        # Clean and validate
        cleaned = {}
        for col in REQUIRED_COLUMNS:
            # Try exact match first, then case-insensitive
            val = row.get(col)
            if val is None:
                for k in row.keys():
                    if k.lower() == col.lower():
                        val = row[k]
                        break
            cleaned[col] = (val or "").strip()
        
        # Only include if has runner_name and p_win
        if cleaned.get("runner_name") and cleaned.get("p_win"):
            rows.append(cleaned)
    
    return rows

def process_all_races(snapshot_path: str, prompt_text: str, provider: str, max_races: int = None) -> list[dict]:
    """Process all races from snapshot file"""
    print(f"Loading market data from: {snapshot_path}")
    df = load_market_data(snapshot_path)
    
    if df.empty:
        print("WARNING: No market data found")
        return []
    
    # Group by market
    if 'market_id' not in df.columns:
        df['market_id'] = 'RACE_1'
    
    races = {}
    for market_id, group in df.groupby('market_id'):
        races[market_id] = group.copy()
    
    print(f"Found {len(races)} races")
    
    if max_races:
        races = dict(list(races.items())[:max_races])
        print(f"Processing first {len(races)} races (max_races={max_races})")
    
    all_selections = []
    
    for idx, (market_id, race_df) in enumerate(races.items(), 1):
        # Extract metadata
        meta = {
            'market_id': str(market_id),
            'market_name': race_df.iloc[0].get('market_name', f'Race {idx}') if not race_df.empty else f'Race {idx}',
            'venue': race_df.iloc[0].get('venue', 'Unknown') if not race_df.empty else 'Unknown',
            'start_time': race_df.iloc[0].get('start_time_dublin', race_df.iloc[0].get('market_start_time', '')) if not race_df.empty else '',
        }
        
        print(f"\n[{idx}/{len(races)}] Processing: {meta['venue']} - {meta['market_name']}")
        
        race_data = format_race_data_for_llm(race_df, meta)
        
        # Call LLM
        print(f"  Calling {provider} API...")
        response = call_llm_for_race(prompt_text, race_data, provider)
        
        if not response:
            print("  WARNING: Empty response from LLM")
            continue
        
        # Parse response
        selections = parse_csv_response(response)
        
        if selections:
            print(f"  ✓ Found {len(selections)} selection(s)")
            all_selections.extend(selections)
        else:
            print("  No selections met thresholds")
    
    return all_selections

def save_selections_csv(selections: list[dict], output_path: str):
    """Save selections to CSV file"""
    if not selections:
        print(f"No selections to save. Creating empty file: {output_path}")
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
        return
    
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(selections)
    
    print(f"\n✓ Saved {len(selections)} selection(s) to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Run betting prompt with live market data")
    parser.add_argument("--prompt", type=str, default="./prompt.txt", help="Path to prompt file")
    parser.add_argument("--snapshot", type=str, default="", help="Path to snapshot CSV/JSON (auto-discover if empty)")
    parser.add_argument("--out", type=str, default="./my_probs.csv", help="Output CSV path")
    parser.add_argument("--provider", type=str, default="auto", choices=["auto", "openai", "anthropic"], help="LLM provider")
    parser.add_argument("--max_races", type=int, default=None, help="Limit number of races to process")
    parser.add_argument("--scope", type=str, default="today", help="Time scope (legacy compat)")
    
    args = parser.parse_args()
    
    # Load prompt
    prompt_text = load_prompt_text(args.prompt)
    print(f"Loaded prompt from: {args.prompt} ({len(prompt_text)} chars)")
    
    # Find snapshot
    snapshot_path = args.snapshot
    if not snapshot_path:
        snapshot_path = discover_latest_snapshot()
        if not snapshot_path:
            print("ERROR: No snapshot file found. Run betfair snapshot script first.", file=sys.stderr)
            sys.exit(1)
    
    if not os.path.exists(snapshot_path):
        print(f"ERROR: Snapshot file not found: {snapshot_path}", file=sys.stderr)
        sys.exit(1)
    
    # Process races
    selections = process_all_races(snapshot_path, prompt_text, args.provider, args.max_races)
    
    # Save output
    save_selections_csv(selections, args.out)
    
    if selections:
        print(f"\n{'='*60}")
        print(f"SUMMARY: {len(selections)} selections generated")
        print(f"Output: {args.out}")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print("No Bets – ROI threshold not met")
        print(f"{'='*60}")

if __name__ == "__main__":
    main()
