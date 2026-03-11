"""Audit race runner counts in source data."""
from cheltenham_deep_analysis_2026 import RACES_2026
from cheltenham_full_fields_2026 import RACE_FULL_FIELDS as FULL_FIELDS
from barrys.surebet_intel import ADDITIONAL_RUNNERS

print("=== RACES_2026 Day 2 runner counts ===")
for rid, r in RACES_2026.items():
    if r.get('day') == 2:
        runners = r.get('runners', [])
        print(f"  [{rid}]  {r.get('name',''):<45}  runners={len(runners)}")

print()
print("=== FULL_FIELDS Day 2 runner counts ===")
for rid, runners in FULL_FIELDS.items():
    # try to match day
    d = RACES_2026.get(rid, {})
    if d.get('day') == 2:
        print(f"  [{rid}]  {d.get('name',''):<45}  full_field={len(runners)}")

print()
print("=== ADDITIONAL_RUNNERS Day 2 ===")
for rid, runners in ADDITIONAL_RUNNERS.items():
    d = RACES_2026.get(rid, {})
    if d.get('day') == 2:
        print(f"  [{rid}]  {d.get('name',''):<45}  additional={len(runners)}")
        for h in runners:
            print(f"    - {h.get('name','')}")
