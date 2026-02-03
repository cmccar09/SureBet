# Weather-Based Going Integration

## Overview
Weather-based going inference is now locked into the value betting workflow. The system automatically fetches 3-day rainfall history for each racecourse and adjusts scoring based on predicted ground conditions.

## How It Works

### 1. Rainfall Data Collection
- **API**: Open-Meteo Archive API (free, no key required)
- **Location**: `weather_going_inference.py`
- **Frequency**: Once per scoring run (cached for all tracks)
- **Time Window**: Last 3 days of rainfall history

### 2. Going Inference Logic

| Rainfall (3 days) | Going Condition | Score Adjustment |
|-------------------|-----------------|------------------|
| 20mm+             | Heavy           | -10              |
| 10-20mm           | Soft            | -5               |
| 5-10mm            | Good to Soft    | -2               |
| 2-5mm             | Good            | +5               |
| 0-2mm             | Good to Firm    | +10              |

**All-Weather Tracks**: No adjustment (±0) regardless of rainfall

### 3. Track Locations
Pre-configured GPS coordinates for:
- Carlisle (54.8951, -2.9382)
- Taunton (51.0151, -3.1034)
- Fairyhouse (53.5060, -6.4240)
- Wolverhampton (52.5901, -2.1284)
- Kempton (51.4186, -0.3730)
- Punchestown (53.2060, -6.7460)

### 4. Integration Points

**generate_ui_picks.py**:
```python
# Fetch going data once
going_data = check_all_tracks_going()

# Apply to each horse at that track
track_going = going_data.get(venue, {})
going_adjustment = track_going.get('adjustment', 0)
score, reasons = score_horse(runner, race, going_adjustment)
```

**value_betting_workflow.py**:
- Calls `generate_ui_picks.py` every 30 minutes
- Weather data refreshed each cycle
- Going adjustments applied to all picks

## Example Output

```
Checking weather and ground conditions...

Checking Carlisle (turf)...
  ☁️ Rainfall: 3.6mm → Going: Good (Score: +5)

Checking Taunton (turf)...
  🌧️ Rainfall: 16.6mm → Going: Soft (Score: -5)

✓ HIGH CONFIDENCE PICK
  Carlisle - 14:00:00 | Going: Good
  Thank You Maam @ 6.8
  Score: 50/100 (adjustment: +5)
```

## Why This Matters

### Ground Conditions Are Critical
- **Soft Ground** (-5 to -10): Favors stamina horses, slower times, tougher for speed horses
- **Good Ground** (+5): Optimal conditions, favors most horses
- **Good to Firm** (+10): Fast times, favors speed horses

### Real-World Impact
- Taunton (16.6mm rain): Soft going → -5 adjustment
- Fairyhouse (15.0mm rain): Soft going → -5 adjustment  
- Carlisle (3.6mm rain): Good going → +5 adjustment
- Wolverhampton (all-weather): No adjustment (consistent surface)

### Example Adjustments
**Before Weather Integration**:
- Courageous Strike @ Taunton: 50 points

**After Weather Integration** (16.6mm rain = soft):
- Courageous Strike @ Taunton: 45 points (-5)
- Still meets 45+ threshold but now accounts for ground

**Before Weather Integration**:
- Haarar @ Carlisle: 50 points

**After Weather Integration** (3.6mm rain = good):
- Haarar @ Carlisle: 55 points (+5)
- Higher confidence in good conditions

## Configuration Locked

This weather integration is now **locked** into the workflows:
- ✅ Automatic rainfall fetching every 30 minutes
- ✅ Going inference based on 3-day history
- ✅ Adjustments applied to all turf track picks
- ✅ All-weather tracks excluded (no adjustment needed)
- ✅ Results displayed in UI pick summaries

## Future Enhancements (NOT LOCKED)
- Add more UK/Ireland tracks as needed
- Fine-tune adjustment values based on results
- Consider temperature and wind factors
- Add manual override for official going reports

## NO ACTION REQUIRED
This system runs automatically with every workflow cycle. Weather data is fetched, going conditions inferred, and adjustments applied without manual intervention.
