"""
LEARNING ANALYSIS: Musselburgh 13:55 - Koukeo Loss
Comparing our selection vs actual winner to identify the mistake
"""

import json

print("\n" + "="*80)
print("❌ LOSS ANALYSIS: Musselburgh 13:55")
print("="*80)

# Data from the saved analysis
koukeo = {
    "selected": True,
    "runner_name": "Koukeo",
    "odds": 2.2,
    "value_score": 7,
    "edge_percentage": 14.4,
    "true_probability": 0.52,
    "form_score": 9,
    "last_3_runs": "1-1-8",
    "class_advantage": True,
    "course_wins": 1,
    "advantage_score": 8,
    "value_reasoning": "Recent form shows two consecutive wins, indicating strong current form.",
    "form_reasoning": "Two consecutive wins, showing hot form.",
    "class_reasoning": "In-form with recent wins, likely well-handicapped."
}

pure_carbon = {
    "selected": False,
    "winner": True,
    "runner_name": "Pure Carbon",
    "odds": 3.25,
    "value_score": 9,
    "edge_percentage": 23.5,
    "true_probability": 0.38,
    "form_score": 8,
    "last_3_runs": "U-2-1",
    "class_advantage": False,
    "course_wins": 0,
    "advantage_score": 6,
    "value_reasoning": "Recent win and place, showing good form at attractive odds.",
    "form_reasoning": "Recent win and place, progressive improvement.",
    "class_reasoning": "Improving form but untested at this course."
}

print("\n📊 COMPARISON:")
print("-" * 80)

print(f"\n{'Metric':<25} {'Koukeo (OUR PICK)':<25} {'Pure Carbon (WINNER)':<25}")
print("-" * 80)

comparisons = [
    ("Odds", f"{koukeo['odds']}", f"{pure_carbon['odds']}"),
    ("Value Score", f"{koukeo['value_score']}/10", f"⭐ {pure_carbon['value_score']}/10 (BETTER)"),
    ("Edge %", f"{koukeo['edge_percentage']}%", f"⭐ {pure_carbon['edge_percentage']}% (BETTER)"),
    ("True Probability", f"{koukeo['true_probability']:.2f}", f"{pure_carbon['true_probability']:.2f}"),
    ("Form Score", f"⭐ {koukeo['form_score']}/10", f"{pure_carbon['form_score']}/10"),
    ("Last 3 Runs", f"⭐ {koukeo['last_3_runs']}", f"{pure_carbon['last_3_runs']}"),
    ("Class Advantage", f"⭐ Yes", "No"),
    ("Course Wins", f"⭐ {koukeo['course_wins']}", f"{pure_carbon['course_wins']}"),
    ("Advantage Score", f"⭐ {koukeo['advantage_score']}/10", f"{pure_carbon['advantage_score']}/10"),
]

for metric, ours, winner in comparisons:
    print(f"{metric:<25} {ours:<25} {winner:<25}")

print("\n" + "="*80)
print("🔍 MISTAKE ANALYSIS")
print("="*80)

print("""
WHY WE PICKED KOUKEO (❌ Lost):
  1. ✓ Hot form: Two consecutive wins (1-1-8)
  2. ✓ Course winner: 1 previous win at Musselburgh
  3. ✓ Class advantage marked as TRUE
  4. ✓ Highest form score (9/10)
  5. ⚠️ BUT: Lower value score (7 vs 9)
  6. ⚠️ BUT: Lower edge percentage (14.4% vs 23.5%)
  7. ⚠️ BUT: Shorter odds (2.2 vs 3.25) = lower potential return

WHY WE REJECTED PURE CARBON (✅ Won):
  1. ❌ No course wins at Musselburgh
  2. ❌ Marked as "untested at this course"
  3. ❌ No class advantage
  4. ❌ Slightly lower form score (8 vs 9)
  5. ✓ BUT: HIGHEST value score (9/10)
  6. ✓ BUT: HIGHEST edge percentage (23.5%)
  7. ✓ BUT: Better odds (3.25) with strong form (U-2-1)

""")

print("="*80)
print("💡 KEY LEARNING INSIGHTS")
print("="*80)

insights = [
    {
        "mistake": "OVER-WEIGHTED Course Experience",
        "evidence": "Pure Carbon won despite 0 course wins vs Koukeo's 1 win",
        "lesson": "Course wins are helpful but NOT essential. Good horses adapt to new courses."
    },
    {
        "mistake": "UNDER-WEIGHTED Value Score",
        "evidence": "Pure Carbon had value score 9 vs 7, edge 23.5% vs 14.4%",
        "lesson": "VALUE SCORE should be PRIMARY factor. A 9/10 value horse beats a 7/10 value horse."
    },
    {
        "mistake": "OVER-WEIGHTED Recent Form Perfection",
        "evidence": "Koukeo's 1-1 wins looked better than Pure Carbon's U-2-1, but U-2-1 shows improvement",
        "lesson": "Progressive improvement (U-2-1) can be STRONGER than plateau (1-1-X after 8th)"
    },
    {
        "mistake": "FAVORED Lower Odds",
        "evidence": "Chose 2.2 favorite over 3.25 value pick in 5-runner race",
        "lesson": "In small fields (≤5), the favorite can be over-bet. Look for value at 3-4 odds."
    }
]

for i, insight in enumerate(insights, 1):
    print(f"\n{i}. {insight['mistake']}")
    print(f"   Evidence: {insight['evidence']}")
    print(f"   Lesson:   {insight['lesson']}")

print("\n" + "="*80)
print("📝 RECOMMENDED PROMPT UPDATES")
print("="*80)

recommendations = """
ADD TO SELECTION CRITERIA:

1. VALUE SCORE PRIORITY:
   "When comparing two horses with similar form (8-9/10), ALWAYS prefer 
    the one with higher value score and edge percentage. A 23% edge beats 
    a 14% edge even with slightly worse form."

2. PROGRESSIVE FORM > PLATEAU:
   "A horse showing improvement (e.g., U-2-1 trending up) can be STRONGER 
    than a horse with recent wins but prior poor form (1-1-8). Look at the 
    TRAJECTORY, not just recent wins."

3. SMALL FIELD DYNAMICS:
   "In 5-runner races, the favorite is often over-bet. Give extra weight to 
    value picks at 3-5 odds with strong value scores (8+) even without course 
    experience."

4. COURSE WINS - HELPFUL NOT ESSENTIAL:
   "Course wins are a positive indicator but should NOT override:
    - Superior value score (9 vs 7)
    - Superior edge percentage (>15% difference)
    - Progressive recent form"

WEIGHT ADJUSTMENTS:
  - Value Score: Increase from 30% → 40% of decision
  - Form Score: Keep at 30%
  - Class/Course: Reduce from 40% → 30% of decision
"""

print(recommendations)

print("\n" + "="*80)
print("✅ ACTION ITEMS FOR LEARNING SYSTEM")
print("="*80)

actions = """
Tonight at 10pm, daily_learning_cycle.py should:

1. Load this exact comparison from all_horses_analyzed
2. Identify the pattern: "Chose lower-value favorite over higher-value improver"
3. Update prompt.txt with new weighting rules
4. Add to learnings_history.json:
   {
     "date": "2026-02-01",
     "race": "Musselburgh 13:55",
     "mistake_type": "value_underweight",
     "pattern": "Favored course experience over superior value metrics",
     "correction": "Increase value_score weight to 40%, reduce class weight to 30%"
   }

Result: Tomorrow's picks will prioritize VALUE over course experience!
"""

print(actions)

print("\n" + "="*80)
print("🎯 SUMMARY")
print("="*80)
print("""
The mistake was clear: We had ALL the data showing Pure Carbon was the better bet,
but our weighting system favored Koukeo's course experience and perfect recent form
over Pure Carbon's SUPERIOR value metrics (9 vs 7 score, 23.5% vs 14.4% edge).

The learning system will extract this tonight and adjust the weights accordingly.
This is EXACTLY how the continuous learning improves the AI! 🚀
""")
