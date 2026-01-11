#!/usr/bin/env python3
"""
Enrich greyhound snapshot with Racing Post form data.

Reads Betfair snapshot JSON, fetches form data for each dog,
and adds historical stats to the snapshot before AI analysis.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import time

# Import existing scrapers
try:
    from fetch_greyhound_stats import (
        fetch_racing_post_dog_form,
        calculate_dog_statistics
    )
except ImportError:
    print("ERROR: Cannot import fetch_greyhound_stats.py", file=sys.stderr)
    sys.exit(1)


def enrich_snapshot(snapshot_path: str, output_path: str, max_dogs: int = 50) -> bool:
    """
    Enrich greyhound snapshot with Racing Post form data.
    
    Args:
        snapshot_path: Path to Betfair snapshot JSON
        output_path: Path to save enriched JSON
        max_dogs: Maximum dogs to fetch form for (rate limiting)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load snapshot
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)
        
        if not snapshot or 'races' not in snapshot:
            print(f"ERROR: Invalid snapshot format in {snapshot_path}", file=sys.stderr)
            return False
        
        print(f"Loaded snapshot with {len(snapshot['races'])} races")
        
        enriched_count = 0
        total_dogs = 0
        
        # Process each race
        for race in snapshot['races']:
            if 'runners' not in race:
                continue
            
            track = race.get('venue', '') or race.get('track', '')
            
            # Process each runner
            for runner in race['runners']:
                total_dogs += 1
                
                if total_dogs > max_dogs:
                    print(f"Reached max_dogs limit ({max_dogs}), stopping enrichment")
                    break
                
                dog_name = runner.get('name', '').strip()
                if not dog_name:
                    continue
                
                # Skip if already enriched
                if 'form_data' in runner and runner['form_data']:
                    enriched_count += 1
                    continue
                
                print(f"  Fetching form for: {dog_name} @ {track}...")
                
                try:
                    # Fetch Racing Post form data
                    form_data = fetch_racing_post_dog_form(dog_name, track)
                    
                    if form_data and form_data.get('last_races'):
                        # Calculate statistics
                        stats = calculate_dog_statistics(form_data)
                        
                        # Add to runner
                        runner['form_data'] = {
                            'source': 'Racing Post',
                            'win_percentage': stats.get('win_percentage', 0),
                            'place_percentage': stats.get('place_percentage', 0),
                            'preferred_trap': stats.get('preferred_trap'),
                            'avg_time': stats.get('avg_time'),
                            'best_time': stats.get('best_time'),
                            'last_5_form': form_data.get('last_5_form', ''),
                            'races_analyzed': len(form_data.get('last_races', []))
                        }
                        
                        enriched_count += 1
                        print(f"    ✓ Win: {stats.get('win_percentage', 0):.1f}%, "
                              f"Place: {stats.get('place_percentage', 0):.1f}%, "
                              f"Pref Trap: {stats.get('preferred_trap', 'N/A')}")
                    else:
                        print(f"    ⚠ No form data found")
                        runner['form_data'] = None
                    
                    # Rate limit - be respectful to Racing Post
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"    ⚠ Error fetching form: {e}", file=sys.stderr)
                    runner['form_data'] = None
            
            if total_dogs > max_dogs:
                break
        
        # Save enriched snapshot
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2)
        
        print(f"\n✓ Enriched {enriched_count}/{total_dogs} dogs with form data")
        print(f"✓ Saved to: {output_path}")
        
        return True
        
    except FileNotFoundError:
        print(f"ERROR: Snapshot file not found: {snapshot_path}", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in snapshot: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: Enrichment failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Enrich greyhound snapshot with Racing Post form data"
    )
    parser.add_argument(
        '--snapshot',
        required=True,
        help="Path to Betfair snapshot JSON"
    )
    parser.add_argument(
        '--out',
        required=True,
        help="Path to save enriched snapshot"
    )
    parser.add_argument(
        '--max_dogs',
        type=int,
        default=50,
        help="Maximum dogs to enrich (default: 50)"
    )
    
    args = parser.parse_args()
    
    success = enrich_snapshot(
        snapshot_path=args.snapshot,
        output_path=args.out,
        max_dogs=args.max_dogs
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
