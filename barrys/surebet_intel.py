"""
surebet_intel.py
Barry's Cheltenham 2026 - SureBet Scoring Engine Integration
=============================================================
Connects Barry's competition picks to the SureBet analysis engine:
  - Uses RACES_2026 from cheltenham_deep_analysis_2026.py (8 featured races)
  - Extends with EXTRA_RACES data for remaining 20 Cheltenham races
  - Applies score_horse_2026() — the proven SureBet grading model
  - Pulls 2 live entries already in SureBet DynamoDB as quality anchors
  - Generates picks per strategy:
      Surebet          → highest raw SureBet score (form-first)
      Douglas Stunners → prioritises Cheltenham festival winners/course specialists

Usage:
    python barrys/surebet_intel.py                   # show picks table
    python barrys/surebet_intel.py --save            # save to BarrysCompetition DynamoDB
    python barrys/surebet_intel.py --json            # JSON output
"""

import sys, os, json, argparse
from decimal import Decimal
from datetime import datetime

# ── path setup ─────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from cheltenham_deep_analysis_2026 import RACES_2026, score_horse_2026
from barrys.barrys_config import FESTIVAL_RACES, ENTRIES, FESTIVAL_DAYS

# ── Mapping: RACES_2026 race-name → FESTIVAL_RACES key ─────────────────────
RACES_2026_MAP = {
    "Supreme Novices Hurdle":      "day1_race1",
    "Arkle Challenge Trophy":      "day1_race2",
    "Champion Hurdle":             "day1_race4",
    "Close Brothers Mares Hurdle": "day1_race5",
    "Queen Mother Champion Chase": "day2_race4",
    "Stayers Hurdle":              "day3_race4",
    "Cheltenham Gold Cup":         "day4_race4",
    "Champion Bumper":             "day4_race6",
}

# ── Extended horse data for the remaining 20 races ─────────────────────────
# Format matches RACES_2026 entries: name, trainer, jockey, odds, age, form,
# rating, cheltenham_record, last_run, days_off
EXTRA_RACES = {
    "day1_race3": {   # Ultima Handicap Chase  (Grade 3, 3m1f)
        "entries": [
            {"name": "Gaillard Du Mesnil", "trainer": "Willie Mullins", "jockey": "Jack Kennedy",
             "odds": "6/1", "age": 9, "form": "1-2-1", "rating": 162,
             "cheltenham_record": "Won 2024 Ultima Handicap Chase",
             "last_run": "Won Grade 3 Handicap Chase Jan 2026", "days_off": 45},
            {"name": "Cloudy Glen", "trainer": "Venetia Williams", "jockey": "Tom Cannon",
             "odds": "8/1", "age": 11, "form": "2-1-2", "rating": 155,
             "cheltenham_record": "Placed National Hunt Chase",
             "last_run": "2nd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Porticello", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "10/1", "age": 8, "form": "1-1-2", "rating": 152,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Monkfish", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "7/1", "age": 10, "form": "1-2-1", "rating": 158,
             "cheltenham_record": "Won 2021 Brown Advisory Chase",
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
        ]
    },
    "day1_race6": {   # National Hunt Chase  (Grade 2, 4m, amateur)
        "entries": [
            {"name": "Crosshill", "trainer": "Willie Mullins", "jockey": "Patrick Mullins",
             "odds": "7/2", "age": 7, "form": "1-1-1", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Chase Jan 2026", "days_off": 45},
            {"name": "Minella Drama", "trainer": "Willie Mullins", "jockey": "Danny Mullins",
             "odds": "4/1", "age": 7, "form": "1-2-1", "rating": 146,
             "cheltenham_record": None,
             "last_run": "Won Amateur Chase Feb 2026", "days_off": 28},
            {"name": "Delta Work", "trainer": "Gordon Elliott", "jockey": "Davy Russell",
             "odds": "5/1", "age": 11, "form": "3-1-2", "rating": 152,
             "cheltenham_record": "Won 2019 RSA Chase",
             "last_run": "3rd Grade 1 Dec 2025", "days_off": 90},
            {"name": "Commander Of Fleet", "trainer": "Gordon Elliott", "jockey": "Mark Walsh",
             "odds": "6/1", "age": 9, "form": "1-1-2", "rating": 149,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
        ]
    },
    "day1_race7": {   # Turners Handicap Hurdle / Conditional Jockeys
        "entries": [
            {"name": "Blazing Khal", "trainer": "Willie Mullins", "jockey": "Danny Mullins",
             "odds": "5/1", "age": 6, "form": "1-1-1", "rating": 140,
             "cheltenham_record": None,
             "last_run": "Won Conditional Hurdle Jan 2026", "days_off": 42},
            {"name": "Golden Ace", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "8/1", "age": 6, "form": "1-2-1", "rating": 138,
             "cheltenham_record": None,
             "last_run": "Won Conditional Hurdle Feb 2026", "days_off": 28},
            {"name": "Run For Oscar", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "10/1", "age": 5, "form": "1-1-2", "rating": 134,
             "cheltenham_record": None,
             "last_run": "2nd Conditional Hurdle Feb 2026", "days_off": 28},
        ]
    },
    "day2_race1": {   # Ballymore Novices Hurdle  (Grade 1, 2m5f)
        "entries": [
            {"name": "Ballyburn", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "6/4", "age": 6, "form": "1-1-1", "rating": 155,
             "cheltenham_record": "Won 2024 Ballymore Novices Hurdle",
             "last_run": "Won Grade 2 Jan 2026", "days_off": 50},
            {"name": "American Mike", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "4/1", "age": 6, "form": "1-1-1", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Majborough", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "6/1", "age": 5, "form": "1-1", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Champion INH Flat Jan 2026", "days_off": 42},
            {"name": "Fact To File", "trainer": "Willie Mullins", "jockey": "Patrick Mullins",
             "odds": "8/1", "age": 6, "form": "1-1-2", "rating": 147,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Novice Jan 2026", "days_off": 42},
        ]
    },
    "day2_race2": {   # Brown Advisory Novices Chase  (Grade 1, 3m)
        "entries": [
            {"name": "James Du Berlais", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "5/2", "age": 7, "form": "1-1-1", "rating": 157,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Dance With Debon", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "7/2", "age": 7, "form": "1-1-1", "rating": 153,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Dannyday", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "5/1", "age": 7, "form": "1-2-1", "rating": 150,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Novice Chase Jan 2026", "days_off": 42},
        ]
    },
    "day2_race3": {   # Coral Cup Handicap Hurdle  (Grade 3, 2m5f)
        "entries": [
            {"name": "Sharp Secret", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "8/1", "age": 6, "form": "1-1-2", "rating": 145,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Handicap Jan 2026", "days_off": 42},
            {"name": "Happy Landing", "trainer": "Gavin Cromwell", "jockey": "Danny Mullins",
             "odds": "10/1", "age": 7, "form": "1-2-1", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Stumptown", "trainer": "Gordon Elliott", "jockey": "Davy Russell",
             "odds": "12/1", "age": 7, "form": "2-1-1", "rating": 141,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day2_race5": {   # Glenfarclas Cross Country Chase  (Grade 2, ~4m)
        "entries": [
            {"name": "Billaway", "trainer": "Willie Mullins", "jockey": "Patrick Mullins",
             "odds": "5/2", "age": 11, "form": "1-1-2", "rating": 148,
             "cheltenham_record": "Won 2022 2023 Cross Country Chase",
             "last_run": "Won Cross Country Chase Jan 2026", "days_off": 45},
            {"name": "Shalmaneser", "trainer": "Gordon Elliott", "jockey": "Davy Russell",
             "odds": "7/2", "age": 10, "form": "1-3-1", "rating": 144,
             "cheltenham_record": "Placed Cross Country 2024",
             "last_run": "Won Cross Country Jan 2026", "days_off": 45},
            {"name": "Good Time Jonny", "trainer": "Martin Brassil", "jockey": "Keith Donoghue",
             "odds": "5/1", "age": 11, "form": "2-1-1", "rating": 141,
             "cheltenham_record": "Won 2021 Cross Country; Placed 2023",
             "last_run": "Won Amateur Cross Country Feb 2026", "days_off": 28},
        ]
    },
    "day2_race6": {   # Dawn Run Mares Novices Hurdle  (Grade 2, 2m1f)
        "entries": [
            {"name": "Sainte Sangria", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "9/4", "age": 5, "form": "1-1-1", "rating": 142,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Mares Novice Dec 2025", "days_off": 72},
            {"name": "Miracle Lily", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "7/2", "age": 6, "form": "1-1-1", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Mares Novice Jan 2026", "days_off": 42},
            {"name": "In A Tangle", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "5/1", "age": 6, "form": "1-2-1", "rating": 140,
             "cheltenham_record": None,
             "last_run": "Won Mares Novice Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day2_race7": {   # FBD Hotels NH Flat Race  (Maiden Bumper, 2m1f)
        "entries": [
            {"name": "Lagos All Day", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "4/1", "age": 4, "form": "1-1", "rating": 125,
             "cheltenham_record": None,
             "last_run": "Won NH Flat Race Jan 2026", "days_off": 45},
            {"name": "Power Of Pause", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "5/1", "age": 4, "form": "1-2-1", "rating": 123,
             "cheltenham_record": None,
             "last_run": "Won Maiden Bumper Feb 2026", "days_off": 28},
            {"name": "Realt Mor", "trainer": "Henry de Bromhead", "jockey": "Rachael Blackmore",
             "odds": "6/1", "age": 4, "form": "1-1", "rating": 120,
             "cheltenham_record": None,
             "last_run": "Won Maiden Bumper Jan 2026", "days_off": 42},
        ]
    },
    "day3_race1": {   # Turners Novices Chase  (Grade 1, 2m4f)
        "entries": [
            {"name": "Jungle Boogie", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "9/4", "age": 7, "form": "1-1-1", "rating": 158,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Lecky Watson", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "7/2", "age": 8, "form": "1-1-2", "rating": 155,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Gaelic Warrior", "trainer": "Willie Mullins", "jockey": "Danny Mullins",
             "odds": "5/1", "age": 7, "form": "2-1-1", "rating": 161,
             "cheltenham_record": "Won 2024 Arkle Challenge Trophy",
             "last_run": "Won Grade 1 Chase Jan 2026", "days_off": 42},
        ]
    },
    "day3_race2": {   # Pertemps Final Handicap Hurdle  (Grade 3, 3m)
        "entries": [
            {"name": "Crambo", "trainer": "Emma Lavelle", "jockey": "Aidan Coleman",
             "odds": "8/1", "age": 10, "form": "1-1-2", "rating": 147,
             "cheltenham_record": "Won 2024 Pertemps Final",
             "last_run": "Won Pertemps Qualifier Feb 2026", "days_off": 28},
            {"name": "Jungle Jack", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "10/1", "age": 9, "form": "1-2-1", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Buzz", "trainer": "Nicky Henderson", "jockey": "Mark Walsh",
             "odds": "12/1", "age": 11, "form": "2-1-3", "rating": 144,
             "cheltenham_record": "Placed 2022 Pertemps Final",
             "last_run": "2nd Qualifier Dec 2025", "days_off": 75},
            {"name": "Gaillard Du Mesnil", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "7/1", "age": 9, "form": "2-1-1", "rating": 148,
             "cheltenham_record": "Won 2024 Ultima Handicap Chase",
             "last_run": "Won Pertemps Qualifier Jan 2026", "days_off": 42},
        ]
    },
    "day3_race3": {   # Ryanair Chase  (Grade 1, 2m5f)
        "entries": [
            {"name": "Banbridge", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "5/2", "age": 8, "form": "1-1-1", "rating": 169,
             "cheltenham_record": "Won 2025 Ryanair Chase",
             "last_run": "Won Grade 1 Ryanair Prep Jan 2026", "days_off": 42},
            {"name": "Mister Coffey", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "4/1", "age": 8, "form": "1-2-1", "rating": 165,
             "cheltenham_record": "Won 2024 Arkle; Festival placed",
             "last_run": "Won Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Conflated", "trainer": "Gordon Elliott", "jockey": "Davy Russell",
             "odds": "7/1", "age": 11, "form": "2-1-3", "rating": 161,
             "cheltenham_record": "Won 2022 Gold Cup",
             "last_run": "Won Grade 3 Chase Jan 2026", "days_off": 45},
            {"name": "Energumene", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "6/1", "age": 11, "form": "1-1-1", "rating": 172,
             "cheltenham_record": "Won 2022 2023 2025 Queen Mother Champion Chase",
             "last_run": "Won Grade 1 Tied Cottage Chase Jan 2026", "days_off": 42},
        ]
    },
    "day3_race5": {   # Plate Handicap Chase  (Grade 3, 2m5f)
        "entries": [
            {"name": "Run To Freedom", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "6/1", "age": 9, "form": "1-2-1", "rating": 155,
             "cheltenham_record": None,
             "last_run": "Won Grade 3 Chase Jan 2026", "days_off": 42},
            {"name": "History Of Fashion", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "7/1", "age": 8, "form": "1-1-2", "rating": 153,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Joyeux Machin", "trainer": "Alan King", "jockey": "Tom Cannon",
             "odds": "10/1", "age": 9, "form": "1-2-1", "rating": 150,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
        ]
    },
    "day3_race6": {   # Boodles Juvenile Handicap Hurdle  (Grade 3, 2m1f)
        "entries": [
            {"name": "Il Etait Temps", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "5/2", "age": 4, "form": "1-1-1", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Dynasty Lady", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "4/1", "age": 4, "form": "1-1-1", "rating": 140,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Blue Arrow", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "6/1", "age": 4, "form": "1-2-1", "rating": 138,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Juvenile Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day3_race7": {   # Martin Pipe Conditional Jockeys Handicap Hurdle  (2m5f)
        "entries": [
            {"name": "Kargese", "trainer": "Willie Mullins", "jockey": "Danny Mullins",
             "odds": "7/2", "age": 6, "form": "1-1-1", "rating": 141,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Hurdle Jan 2026", "days_off": 42},
            {"name": "Western Frontier", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "6/1", "age": 6, "form": "1-2-1", "rating": 138,
             "cheltenham_record": None,
             "last_run": "Won Conditional Hurdle Feb 2026", "days_off": 28},
            {"name": "Romeo Coolio", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "8/1", "age": 6, "form": "2-1-2", "rating": 137,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Hurdle Feb 2026", "days_off": 28},
        ]
    },
    "day4_race1": {   # JCB Triumph Hurdle  (Grade 1, 2m1f, juveniles)
        "entries": [
            {"name": "Il Etait Temps", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "9/4", "age": 4, "form": "1-1-1", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Dynasty Lady", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "3/1", "age": 4, "form": "1-1-1", "rating": 141,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Jan 2026", "days_off": 42},
            {"name": "Blue Arrow", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "5/1", "age": 4, "form": "1-2-1", "rating": 139,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Jan 2026", "days_off": 42},
            {"name": "Brightondaleight", "trainer": "Henry de Bromhead", "jockey": "Rachael Blackmore",
             "odds": "8/1", "age": 4, "form": "1-1-2", "rating": 136,
             "cheltenham_record": None,
             "last_run": "Won Juvenile Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day4_race2": {   # County Handicap Hurdle  (Grade 3, 2m1f, fast handicap)
        "entries": [
            {"name": "Kopek Des Bordes", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "6/1", "age": 5, "form": "1-1-1", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Fil Dor", "trainer": "Gavin Cromwell", "jockey": "Danny Mullins",
             "odds": "10/1", "age": 6, "form": "2-1-2", "rating": 144,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Impaire Et Passe", "trainer": "Oliver McKiernan", "jockey": "Mark Walsh",
             "odds": "12/1", "age": 7, "form": "1-1-2", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day4_race3": {   # Albert Bartlett Novices Hurdle  (Grade 1, 3m)
        "entries": [
            {"name": "Onemorefortheroad", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "5/2", "age": 6, "form": "1-1-1", "rating": 152,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Perceval Legallois", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "3/1", "age": 6, "form": "1-1-1", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Selected", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "5/1", "age": 7, "form": "1-1-2", "rating": 145,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Feb 2026", "days_off": 28},
        ]
    },
    "day4_race5": {   # Grand Annual Handicap Chase  (Grade 3, 2m)
        "entries": [
            {"name": "Haut En Couleurs", "trainer": "Henry de Bromhead", "jockey": "Rachael Blackmore",
             "odds": "6/1", "age": 8, "form": "1-2-1", "rating": 150,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Vauban", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "5/1", "age": 8, "form": "1-1-2", "rating": 152,
             "cheltenham_record": "3rd 2024 Champion Hurdle; Festival exp",
             "last_run": "Won International Hurdle Dec 2025", "days_off": 75},
            {"name": "Gallyhill", "trainer": "Gordon Elliott", "jockey": "Davy Russell",
             "odds": "8/1", "age": 8, "form": "2-1-2", "rating": 147,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Chase Feb 2026", "days_off": 28},
        ]
    },
    "day4_race7": {   # St James's Place Foxhunter Chase  (Hunter Chase, ~3m2f)
        "entries": [
            {"name": "Readin Tommy Wrong", "trainer": "Gordon Elliott", "jockey": "Davy Russell",
             "odds": "3/1", "age": 8, "form": "1-1-1", "rating": 152,
             "cheltenham_record": "Won 2025 Foxhunter Chase",
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 45},
            {"name": "Il Est Francais", "trainer": "Willie Mullins", "jockey": "Patrick Mullins",
             "odds": "4/1", "age": 9, "form": "1-1-1", "rating": 149,
             "cheltenham_record": "Won 2024 Foxhunter Chase",
             "last_run": "Won Hunter Chase Feb 2026", "days_off": 28},
            {"name": "Commander Of Fleet", "trainer": "Gordon Elliott", "jockey": "Mark Walsh",
             "odds": "6/1", "age": 9, "form": "2-1-1", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
        ]
    },
}


# ────────────────────────────────────────────────────────────────────────────
# SUREBET DYNAMODB — live entries already in SureBetBets
# (Salvator Mundi + Teahupoo — added 28 Feb 2026)
# ────────────────────────────────────────────────────────────────────────────

def get_surebet_db_entries():
    """Fetch Cheltenham picks already logged in SureBetBets DynamoDB."""
    try:
        import boto3
        from boto3.dynamodb.conditions import Attr
        db    = boto3.resource("dynamodb", region_name="eu-west-1")
        table = db.Table("SureBetBets")
        resp  = table.scan(
            FilterExpression=Attr("festival").contains("Cheltenham") |
                             Attr("course").contains("Cheltenham")
        )
        entries = {}
        for item in resp.get("Items", []):
            horse = item.get("horse", "").lower()
            entries[horse] = {
                "surebet_score":  float(item.get("comprehensive_score", 0) or 0),
                "confidence":     item.get("confidence", ""),
                "selection_reasons": item.get("selection_reasons", []),
                "race_name":      item.get("race_name", ""),
                "trainer":        item.get("trainer", ""),
                "jockey":         item.get("jockey", ""),
            }
        return entries
    except Exception as e:
        print(f"  [WARN] Could not read SureBetBets: {e}")
        return {}


# ────────────────────────────────────────────────────────────────────────────
# ── Horses ruled out / unavailable for 2026 festival ─────────────────────────
# Constitution Hill: officially ruled out by Nicky Henderson (25 Feb 2026)
RULED_OUT = {
    "constitution hill",   # ruled out 25 Feb 2026 – Nicky Henderson moving to flat
}

# ────────────────────────────────────────────────────────────────────────────
# CORE SCORING + PICK SELECTION
# ────────────────────────────────────────────────────────────────────────────

def score_field(entries, surebet_db):
    """
    Score every horse in a race field using score_horse_2026().
    Augments score by +10 if horse is already confirmed in SureBetBets.
    Returns list of dicts sorted highest score first.
    """
    results = []
    for horse in entries:
        # Skip any horse officially ruled out of the 2026 festival
        if horse["name"].lower() in RULED_OUT:
            continue
        score, tips, warnings, value_r = score_horse_2026(horse, "")
        name_lower = horse["name"].lower()
        db_bonus   = 0
        db_note    = None
        if name_lower in surebet_db:
            db_bonus = 10
            db_note  = f"SureBet DB confirmed (score {surebet_db[name_lower]['surebet_score']:.0f}): +{db_bonus}pts"
            tips     = tips + [db_note]
            score   += db_bonus
        has_festival_win = (
            horse.get("cheltenham_record", "") and
            "won" in (horse.get("cheltenham_record", "") or "").lower()
        )
        results.append({
            "name":             horse["name"],
            "trainer":          horse.get("trainer", "?"),
            "jockey":           horse.get("jockey", "?"),
            "score":            score,
            "tips":             tips,
            "warnings":         warnings[:2],
            "value_r":          value_r,
            "cheltenham_record": horse.get("cheltenham_record") or "First time",
            "has_festival_win": has_festival_win,
            "in_surebet_db":    name_lower in surebet_db,
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def pick_for_entry(scored, strategy):
    """
    Select the competition pick for a given entry strategy.

    Surebet (form):
        → Simply return the highest-scoring horse (best overall form).

    Douglas Stunners (festival_specialist):
        → Prefer horses with a confirmed Cheltenham festival win,
          provided they score within 15 points of the top scorer.
          Falls back to top scorer if no festival winner qualifies.
    """
    if not scored:
        return {"name": "TBC (declarations pending)", "score": 0, "trainer": "", "jockey": "", "reason": "No runners"}

    top = scored[0]

    if strategy == "form":
        return {**top, "reason": "Highest SureBet score (form-first)"}

    # festival_specialist: look for a Cheltenham winner close to the top
    threshold = top["score"] - 15
    festival_candidates = [h for h in scored if h["has_festival_win"] and h["score"] >= threshold]
    if festival_candidates:
        pick = festival_candidates[0]
        return {**pick, "reason": f"Festival specialist — previous Cheltenham winner (score gap {top['score']-pick['score']:.0f})"}
    # fallback
    return {**top, "reason": "Highest SureBet score (no festival winner in field)"}


# ────────────────────────────────────────────────────────────────────────────
# BUILD ALL 28 RACE PICKS
# ────────────────────────────────────────────────────────────────────────────

def build_all_picks(verbose=False):
    surebet_db = get_surebet_db_entries()
    if surebet_db:
        print(f"  [INFO] {len(surebet_db)} horse(s) found in SureBet DynamoDB: {', '.join(surebet_db.keys()).title()}")

    # Merge RACES_2026 (via mapping) into a flat race → entries dict
    all_race_data = {}
    for r2026_name, entries_data in RACES_2026.items():
        fkey = RACES_2026_MAP.get(r2026_name)
        if fkey:
            all_race_data[fkey] = entries_data["entries"]

    # Add the extra 20 races
    for fkey, data in EXTRA_RACES.items():
        all_race_data[fkey] = data["entries"]

    picks = {}
    for day_num in [1, 2, 3, 4]:
        for race_key, race_info in sorted(FESTIVAL_RACES.items(), key=lambda x: (x[1]["day"], x[1]["time"])):
            if race_info["day"] != day_num:
                continue
            entries = all_race_data.get(race_key, [])
            if not entries:
                picks[race_key] = {
                    "race_key":   race_key,
                    "race_name":  race_info["name"],
                    "day":        day_num,
                    "time":       race_info["time"],
                    "grade":      race_info["grade"],
                    "surebet":    {"name": "TBC", "score": 0, "trainer": "", "jockey": "", "reason": "No runners loaded yet"},
                    "douglas":    {"name": "TBC", "score": 0, "trainer": "", "jockey": "", "reason": "No runners loaded yet"},
                    "scored":     [],
                }
                continue

            scored = score_field(entries, surebet_db)
            sb_pick = pick_for_entry(scored, "form")
            ds_pick = pick_for_entry(scored, "festival_specialist")

            picks[race_key] = {
                "race_key":  race_key,
                "race_name": race_info["name"],
                "day":       day_num,
                "time":      race_info["time"],
                "grade":     race_info["grade"],
                "surebet":   sb_pick,
                "douglas":   ds_pick,
                "scored":    scored if verbose else scored[:3],
            }

    return picks


# ────────────────────────────────────────────────────────────────────────────
# DISPLAY
# ────────────────────────────────────────────────────────────────────────────

DAY_NAMES = {1: "Champion Day", 2: "Ladies Day", 3: "St Patrick's Thursday", 4: "Gold Cup Day"}
DAY_DATES = {1: "2026-03-10", 2: "2026-03-11", 3: "2026-03-12", 4: "2026-03-13"}


def print_picks_table(picks):
    print(f"\n{'='*100}")
    print(f"  BARRY'S CHELTENHAM 2026 — SUREBET-POWERED PICKS")
    print(f"  Source: cheltenham_deep_analysis_2026.py × SureBetBets DynamoDB")
    print(f"  Generated: {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'='*100}")
    print(f"  POINTS: 1st=10  2nd=5  3rd=3  |  Odds are IRRELEVANT — best horse wins")
    print(f"{'='*100}")

    total_diff = 0
    for day_num in [1, 2, 3, 4]:
        day_picks = {k: v for k, v in picks.items() if v["day"] == day_num}
        print(f"\n  DAY {day_num} — {DAY_NAMES[day_num].upper()}  ({DAY_DATES[day_num]})")
        print(f"  {'-'*96}")
        print(f"  {'TIME':<6} {'RACE':<38} {'GRADE':<12} {'SUREBET (FORM)':<25} {'DOUGLAS STUNNERS':<25} {'SAME?'}")
        print(f"  {'-'*96}")
        for race_key in sorted(day_picks, key=lambda x: day_picks[x]["time"]):
            r     = day_picks[race_key]
            sb    = r["surebet"]["name"][:23]
            ds    = r["douglas"]["name"][:23]
            same  = " <<BANKER" if r["surebet"]["name"] == r["douglas"]["name"] and r["surebet"]["name"] not in ("TBC", "") else ""
            sb_sc = r["surebet"].get("score", 0)
            ds_sc = r["douglas"].get("score", 0)
            total_diff += abs(sb_sc - ds_sc)
            print(f"  {r['time']:<6} {r['race_name'][:37]:<38} {r['grade'][:11]:<12} {sb:<25} {ds:<25}{same}")
        print()

    # Summary section
    print(f"\n  {'='*96}")
    print(f"  HEADLINE PICKS — CHAMPIONSHIP RACES")
    print(f"  {'='*96}")
    key_races = [
        ("day1_race1", "Supreme Novices Hurdle"),
        ("day1_race2", "Arkle Challenge Trophy"),
        ("day1_race4", "Champion Hurdle"),
        ("day1_race5", "Mares Hurdle"),
        ("day2_race4", "Queen Mother Chase"),
        ("day3_race3", "Ryanair Chase"),
        ("day3_race4", "Stayers Hurdle"),
        ("day4_race3", "Albert Bartlett"),
        ("day4_race4", "Cheltenham Gold Cup"),
        ("day4_race6", "Champion Bumper"),
    ]
    print(f"\n  {'RACE':<32} {'SUREBET PICK':<26} {'SCORE':<8} {'DOUGLAS STUNNERS PICK':<26} {'SCORE':<8} {'RATIONALE'}")
    print(f"  {'-'*115}")
    bankers = []
    for race_key, label in key_races:
        if race_key not in picks:
            continue
        r  = picks[race_key]
        sb = r["surebet"]
        ds = r["douglas"]
        if sb["name"] == ds["name"] and sb["name"] not in ("TBC", ""):
            bankers.append((label, sb["name"], sb.get("score", 0)))
        print(f"  {label:<32} {sb['name'][:24]:<26} {sb.get('score',0):<8.0f} {ds['name'][:24]:<26} {ds.get('score',0):<8.0f} {ds.get('reason','')[:30]}")

    if bankers:
        print(f"\n  BANKERS (both entries agree):")
        for label, horse, score in bankers:
            print(f"    **  {horse} in the {label}  (SureBet score: {score:.0f})")

    print(f"\n  [DATA] SureBet scoring engine: trainer/jockey/combo/form/rating/freshness/festival-record")
    print(f"  [DATA] Picks UPDATE pending once Betfair markets open ~4 Mar 2026")
    print()


def _score_tier(score):
    """Return a grade label for a raw SureBet score."""
    if score >= 155: return "A+  ELITE"
    if score >= 140: return "A   ELITE"
    if score >= 120: return "B   EXCELLENT"
    if score >= 100: return "C   STRONG"
    if score >= 80:  return "D   FAIR"
    return               "E   WEAK"


def print_scores_detail(picks):
    """Full per-horse scoring breakdown per race."""
    WIDTH = 104
    for day_num in [1, 2, 3, 4]:
        day_picks = {k: v for k, v in picks.items() if v["day"] == day_num}
        print(f"\n{'='*WIDTH}")
        print(f"  DAY {day_num} - {DAY_NAMES[day_num].upper()}  ({DAY_DATES[day_num]})")
        print(f"{'='*WIDTH}")

        for race_key in sorted(day_picks, key=lambda x: day_picks[x]["time"]):
            r = day_picks[race_key]
            sb_name = r["surebet"]["name"]
            ds_name = r["douglas"]["name"]
            print(f"\n  +{'-'*(WIDTH-3)}+")
            print(f"  |  {r['time']}  {r['race_name']}  [{r['grade']}]")
            print(f"  +{'-'*(WIDTH-3)}+")

            if not r["scored"]:
                print(f"  (no runners loaded)")
                continue

            for rank, h in enumerate(r["scored"], 1):
                is_sb = h["name"] == sb_name
                is_ds = h["name"] == ds_name
                badges = ("  [SUREBET PICK]" if is_sb else "") + (" [DOUGLAS PICK]" if is_ds else "")
                tier   = _score_tier(h["score"])
                vr     = h.get("value_r", 0)
                print()
                print(f"  #{rank}  {h['name']}  --  Score: {h['score']:.0f}  |  Tier: {tier}  |  Value Rating: {vr:.1f}{badges}")
                print(f"       Trainer: {h['trainer']}  |  Jockey: {h['jockey']}")
                print(f"       Festival Record : {h['cheltenham_record'][:60]}")
                for tip in h.get("tips", []):
                    print(f"       + {tip}")
                for warn in h.get("warnings", []):
                    print(f"       ! {warn}")

            print()
            print(f"  Surebet pick   -> {sb_name}  {r['surebet'].get('reason','')}")
            print(f"  Douglas pick   -> {ds_name}  {r['douglas'].get('reason','')}")
            print(f"  {'-'*(WIDTH-3)}")


# ────────────────────────────────────────────────────────────────────────────
# DYNAMODB SAVE
# ────────────────────────────────────────────────────────────────────────────

def save_picks_to_dynamodb(picks):
    """Save generated picks to BarrysCompetition DynamoDB table."""
    import boto3
    db    = boto3.resource("dynamodb", region_name="eu-west-1")
    table = db.Table("BarrysCompetition")
    saved = 0
    for race_key, r in picks.items():
        for entry_name, strategy, pick in [
            ("Surebet",         "form",               r["surebet"]),
            ("Douglas Stunners","festival_specialist", r["douglas"]),
        ]:
            if pick["name"] in ("TBC", ""):
                continue
            item = {
                "entry":         entry_name,
                "race_id":       race_key,
                "race_name":     r["race_name"],
                "day":           r["day"],
                "race_time":     r["time"],
                "grade":         r["grade"],
                "pick":          pick["name"],
                "trainer":       pick.get("trainer", ""),
                "jockey":        pick.get("jockey", ""),
                "surebet_score": Decimal(str(round(pick.get("score", 0), 1))),
                "pick_reason":   pick.get("reason", "")[:200],
                "strategy":      strategy,
                "source":        "surebet_deep_analysis",
                "generated_at":  datetime.now().isoformat(),
                "outcome":       "pending",
                "points":        Decimal("0"),
            }
            table.put_item(Item=item)
            saved += 1
    print(f"  [DB] Saved {saved} picks to BarrysCompetition DynamoDB")
    return saved


# ────────────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Barry's Cheltenham 2026 — SureBet-powered picks")
    parser.add_argument("--save",    action="store_true", help="Save picks to BarrysCompetition DynamoDB")
    parser.add_argument("--detail",  action="store_true", help="Show detailed horse scores per race")
    parser.add_argument("--json",    action="store_true", help="Output JSON only")
    args = parser.parse_args()

    picks = build_all_picks(verbose=args.detail)

    if args.json:
        def dec_serial(o):
            if isinstance(o, Decimal): return float(o)
            raise TypeError
        safe = {k: {k2: v2 for k2, v2 in v.items() if k2 != "scored"} for k, v in picks.items()}
        print(json.dumps(safe, indent=2, default=dec_serial))
    else:
        print_picks_table(picks)
        if args.detail:
            print_scores_detail(picks)
        if args.save:
            save_picks_to_dynamodb(picks)
