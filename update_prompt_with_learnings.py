"""
Update prompt.txt with today's learnings
Add going-specific strategies and trainer multipliers
"""

new_learnings = """

============================================================
CRITICAL LEARNINGS - GOING-SPECIFIC STRATEGIES (2026-02-02)
============================================================

**FORM PARSING BUG FIX (IMPLEMENTED):**
- Form strings like "231-426" and "132-111" were incorrectly parsed
- Now strips all non-digits before counting wins
- Directly validated: Jacob's Ladder winner @ 2/1 (form "1P-2312" = 2 wins)
- Fact To File winner @ 9/2 (form "231-426" = 1 win)

**GOING CONDITION IS PRIMARY STRATEGIC FACTOR:**

1. **HEAVY GOING STRATEGY:**
   - Odds Range: Extend to 3.0-25.0 (was 3.0-15.0)
   - Pattern: Longshots win, favorites flop, form less reliable
   - Winners today: Saint Le Fort @ 10/1, Broadway Ted @ 18/1
   - Optimal odds: 10.0-20.0 = +30 confidence points
   - Minimum score threshold: 35 points (reduced from 40)
   - Why: Market struggles to price heavy going correctly
   - Going ability > Recent form in extreme conditions

2. **SOFT GOING STRATEGY:**
   - Odds Range: 3.0-15.0 (standard sweet spot applies)
   - Pattern: Sweet spot 3.0-9.0 performs well, form matters
   - Winners today: Romeo Coolio @ 4/9, Fact To File @ 9/2, Jacob's Ladder @ 2/1
   - Optimal odds: 3.0-9.0 = +30 confidence points
   - Minimum score threshold: 40 points (standard)
   - Why: Form book reliable but trainer power significant

3. **GOOD TO SOFT (NORMAL) STRATEGY:**
   - Odds Range: 3.0-15.0 (favor favorites)
   - Pattern: Favorites deliver, form highly reliable
   - Winners today: Aviation @ 5/1, Lover Desbois @ 11/4
   - Optimal odds: 2.5-6.0 = +35 confidence points (favor favorites)
   - Minimum score threshold: 40 points (standard)
   - Why: Normal conditions = trust form book and market

**TRAINER-SPECIFIC MULTIPLIERS:**

1. **GORDON ELLIOTT AT LEOPARDSTOWN (SOFT/HEAVY):**
   - Evidence: 16:05 race = 1st + 2nd, 16:40 race = 1st + 2nd + 3rd + 6th
   - Pattern: 7 of top 11 finishers across 2 races in soft/heavy going
   - Multiplier: +50% to total score (0.5x boost)
   - Applies to: ALL Elliott runners at Leopardstown in soft/heavy going
   - Why: Extreme home-course advantage in testing conditions

2. **W.P. MULLINS IN GRADE 1 CHASES:**
   - Evidence: Trained 6 of top 8 in Irish Gold Cup
   - Pattern: Stable power in top-tier races
   - Action: Consider multiple Mullins runners in Grade 1

**SCORE-BASED INSIGHTS:**

1. **SCORE 65+ = HIGH QUALITY:**
   - Jacob's Ladder @ 2/1 scored 65, won easily
   - Pattern: 60-70 score range = premium picks
   - Action: Prioritize horses scoring 60+

2. **SCORE 40-45 CAN WIN IN SPECIAL CONDITIONS:**
   - Broadway Ted @ 18/1 scored 40, won in heavy going
   - Fact To File @ 9/2 scored 45, won in Grade 1
   - Pattern: Lower scores viable with going/trainer edge
   - Action: Don't reject score 40+ if Elliott/Leopardstown/heavy

**CLASS-SPECIFIC PATTERNS:**

1. **CLASS 5 RACES = FORM MORE RELIABLE:**
   - Lover Desbois @ 11/4 won Class 5 in normal going
   - Pattern: Lower class races more predictable
   - Action: Increase form weight for Class 4-5 races

2. **GRADE 1-2 RACES = FORM LESS PREDICTIVE:**
   - Fact To File @ 9/2 won despite limited form
   - Pattern: Higher class = more variance
   - Action: Reduce form requirements for Grade 1-2 if other factors strong

**AMATEUR RACE DYNAMICS:**

1. **AMATEUR + HEAVY GOING = CHAOS:**
   - Broadway Ted @ 18/1 won, favorites 7/4, 11/4, 5/2 all flopped
   - Pattern: Amateur races in heavy going = unpredictable
   - Action: Expect longshots, reduce favorite confidence

2. **AMATEUR + NORMAL GOING = FORM WORKS:**
   - Lover Desbois @ 11/4 won in Good to Soft
   - Pattern: Amateur races predictable in normal conditions
   - Action: Trust form in Good/Good to Soft amateur races

**VALUE DISCIPLINE VALIDATED:**
- Romeo Coolio @ 4/9 won but correctly avoided (no value)
- Pattern: Winning ≠ value betting
- Action: Maintain discipline on odds <2.0 even if likely winner

**GOING-SPECIFIC ODDS SCORING (NOW IMPLEMENTED):**

Heavy Going:
  - 10.0-20.0 odds = +30 points
  - 5.0-10.0 odds = +25 points
  - 3.0-5.0 odds = +15 points

Soft Going:
  - 3.0-9.0 odds = +30 points
  - 2.5-3.0 or 9.0-12.0 = +15 points

Normal Going (Good/Good to Soft):
  - 2.5-6.0 odds = +35 points (favor favorites)
  - 6.0-9.0 odds = +25 points
  - 9.0-12.0 odds = +10 points

============================================================
END OF 2026-02-02 LEARNINGS
============================================================

"""

print("="*80)
print("UPDATING PROMPT.TXT WITH TODAY'S LEARNINGS")
print("="*80)

with open('prompt.txt', 'r', encoding='utf-8') as f:
    current_content = f.read()

# Append new learnings at the end
updated_content = current_content + new_learnings

with open('prompt.txt', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print("\n✓ Added going-specific strategies to prompt.txt")
print("✓ Added trainer multipliers (Elliott @ Leopardstown)")
print("✓ Added score-based insights (65+ = premium, 40+ viable)")
print("✓ Added class-specific patterns")
print("✓ Added amateur race dynamics")
print("✓ Added going-specific odds scoring")

print("\n" + "="*80)
print("PROMPT.TXT UPDATED SUCCESSFULLY")
print("="*80)
print("\nNew content added:")
print("  - Form parsing bug fix documentation")
print("  - Heavy/Soft/Normal going strategies")
print("  - Elliott Leopardstown multiplier (+50%)")
print("  - Mullins Grade 1 insights")
print("  - Score thresholds by going type")
print("  - Amateur race dynamics")
print("  - Value discipline validation")
print("\nAll learnings from 6 races analyzed today now in prompt.txt")
print("="*80 + "\n")
