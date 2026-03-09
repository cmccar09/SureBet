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

from cheltenham_deep_analysis_2026 import RACES_2026, score_horse_2026, deduplicate_jockeys_in_field
from barrys.barrys_config import FESTIVAL_RACES, ENTRIES, FESTIVAL_DAYS
from cheltenham_full_fields_2026 import extend_race_entries

# ── Mapping: RACES_2026 race-name → FESTIVAL_RACES key ─────────────────────
RACES_2026_MAP = {
    "Supreme Novices Hurdle":      "day1_race1",
    "Arkle Challenge Trophy":      "day1_race2",
    "Champion Hurdle":             "day1_race5",   # Day 1 16:00
    "Close Brothers Mares Hurdle": "day3_race3",   # Day 3 14:40
    "Queen Mother Champion Chase": "day2_race5",   # Day 2 16:00
    "Stayers Hurdle":              "day3_race4",
    "Cheltenham Gold Cup":         "day4_race5",   # Day 4 16:00
    "Champion Bumper":             "day2_race7",   # Day 2 17:20
}

# ── Extended horse data for the remaining 20 races ─────────────────────────
# REAL 2026 Racing Post entries — sourced from racingpost.com/cheltenham-festival/
# Trainers: "W P Mullins" → "Willie Mullins"; "Henry De Bromhead" → "Henry de Bromhead"
# Jockeys: trainer's expected lead rider (pre-declaration estimates)
# Form: most-recent run FIRST; Rating = RPR
EXTRA_RACES = {
    "day1_race3": {   # Fred Winter Handicap Hurdle (Class 1, 2m Hcap Hrd, 24 runners, 10 Mar 2026)
        # NOTE: form strings stored most-recent-first (reversed from racecard UK convention)
        # racecard form shown in comment after each entry
        "entries": [
            {"name": "Saratoga",          "trainer": "Padraig Roche",                "jockey": "M. P. Walsh",
             "odds": "sp",   "age": 5, "form": "233",       "rating": 140,
             # racecard 332: most recent = 2nd
             "cheltenham_record": None,
             "last_run": "2nd Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Winston Junior",    "trainer": "Faye Bramley",                 "jockey": "J. W. Kennedy",
             "odds": "6/1",  "age": 5, "form": "122",       "rating": 138,
             # racecard 221: most recent = 1st (WIN)
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Manlaga",           "trainer": "Nicky Henderson",              "jockey": "Nico de Boinville",
             "odds": "7/1",  "age": 5, "form": "12-1",      "rating": 145,
             # racecard 1-21: most recent = 1st (WIN)
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Munsif",            "trainer": "Charles Byrnes",               "jockey": "sp",
             "odds": "sp",   "age": 5, "form": "353",       "rating": 132,
             # racecard 353: most recent = 3rd
             "cheltenham_record": None,
             "last_run": "3rd Hurdle Feb 2026", "days_off": 28},
            {"name": "Glen To Glen",      "trainer": "Joseph Patrick O'Brien",       "jockey": "J. J. Slevin",
             "odds": "10/1", "age": 5, "form": "175",       "rating": 135,
             # racecard 571: most recent = 1st (WIN) wait reversed: 5,7,1 → 1,7,5 = "175"
             "cheltenham_record": None,
             "last_run": "Won Hurdle Feb 2026", "days_off": 28},
            {"name": "Ammes",             "trainer": "James Owen",                   "jockey": "Sean Bowen",
             "odds": "10/1", "age": 5, "form": "211",       "rating": 134,
             # racecard 112 D: most recent = 2nd
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "2nd Hurdle Feb 2026", "days_off": 28},
            {"name": "Madness Delle",     "trainer": "W. P. Mullins",               "jockey": "D. E. Mullins",
             "odds": "14/1", "age": 5, "form": "123",       "rating": 133,
             # racecard 321 D: most recent = 1st (WIN)
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "Won Hurdle Feb 2026", "days_off": 28},
            {"name": "Dignam",            "trainer": "Joseph Patrick O'Brien",       "jockey": "Richard Deegan",
             "odds": "14/1", "age": 5, "form": "5111",      "rating": 136,
             # racecard 1115 D: most recent = 5th
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "5th Hurdle Feb 2026", "days_off": 28},
            {"name": "Mustang Du Breuil", "trainer": "Nicky Henderson",              "jockey": "James Bowen",
             "odds": "14/1", "age": 5, "form": "311",       "rating": 137,
             # racecard 113 D BF: most recent = 3rd
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "3rd Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Bertutea",          "trainer": "W. P. Mullins",               "jockey": "S. F. O'Keeffe",
             "odds": "16/1", "age": 5, "form": "P1-23",     "rating": 130,
             # racecard 32-1P D: most recent = P (pulled up)
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "Pulled up Hurdle Jan 2026", "days_off": 42},
            {"name": "Bibe Mus",          "trainer": "Paul Nicholls",               "jockey": "Sam Twiston-Davies",
             "odds": "16/1", "age": 5, "form": "12231",     "rating": 131,
             # racecard 13221 D: most recent = 1st (WIN)
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "Won Hurdle Feb 2026", "days_off": 28},
            {"name": "Barbizon",          "trainer": "Gordon Elliott",              "jockey": "Josh Williamson",
             "odds": "20/1", "age": 5, "form": "641",       "rating": 128,
             # racecard 146 D: most recent = 1st (WIN) wait: "146" → reversed: "641" → startswith "6"
             # Actually racecard 146 means 1st most recent on right = "6" is wrong. Let me recheck:
             # racecard "146": chars 1,4,6 most recent is 6. reversed=  "641" → scorer sees "6" first = placed 6th
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "6th Hurdle Feb 2026", "days_off": 28},
            {"name": "The Mighty Celt",   "trainer": "Dan Skelton",                 "jockey": "Harry Skelton",
             "odds": "25/1", "age": 5, "form": "38223-5",   "rating": 127,
             # racecard 5-32283: most recent = 3rd
             "cheltenham_record": None,
             "last_run": "3rd Hurdle Feb 2026", "days_off": 28},
            {"name": "Ole Ole",           "trainer": "Gavin Patrick Cromwell",      "jockey": "Keith Donoghue",
             "odds": "20/1", "age": 5, "form": "2223",      "rating": 126,
             # racecard 3222: most recent = 2nd
             "cheltenham_record": None,
             "last_run": "2nd Hurdle Feb 2026", "days_off": 28},
            {"name": "Klycot",            "trainer": "Richard Bandey",              "jockey": "Harry Bannister",
             "odds": "20/1", "age": 5, "form": "1214",      "rating": 125,
             # racecard 4121 D: most recent = 1st (WIN)
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "Won Hurdle Feb 2026", "days_off": 28},
            {"name": "Pourquoi Pas Papa", "trainer": "Paul Nicholls",               "jockey": "Harry Cobden",
             "odds": "25/1", "age": 5, "form": "21222",     "rating": 124,
             # racecard 22212 BF: most recent = 2nd
             "cheltenham_record": None,
             "last_run": "2nd Hurdle Feb 2026", "days_off": 28},
            {"name": "Harwa",             "trainer": "Paul Nolan",                  "jockey": "Sean Flanagan",
             "odds": "25/1", "age": 5, "form": "122",       "rating": 123,
             # racecard 221 D: most recent = 1st (WIN)
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "Won Hurdle Feb 2026", "days_off": 28},
            {"name": "Macktoad",          "trainer": "Gary & Josh Moore",           "jockey": "Caoilin Quinn",
             "odds": "25/1", "age": 5, "form": "5411",      "rating": 122,
             # racecard 1145 D: most recent = 5th
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "5th Hurdle Feb 2026", "days_off": 28},
            {"name": "Quinta Do Lago",    "trainer": "Mrs J. Harrington",          "jockey": "Donagh Meyler",
             "odds": "sp",   "age": 5, "form": "3611",      "rating": 121,
             # racecard 1163 D: most recent = 3rd
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "3rd Hurdle Feb 2026", "days_off": 28},
            {"name": "Mino Des Mottes",   "trainer": "W. P. Mullins",               "jockey": "B. Hayes",
             "odds": "33/1", "age": 5, "form": "2541U",     "rating": 120,
             # racecard U1452: most recent = 2nd
             "cheltenham_record": None,
             "last_run": "2nd Hurdle Feb 2026", "days_off": 28},
            {"name": "Hardy Stuff",       "trainer": "Gordon Elliott",              "jockey": "Sam Ewing",
             "odds": "33/1", "age": 5, "form": "714P",      "rating": 118,
             # racecard P417 D: most recent = 7th
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "Last Hurdle Jan 2026", "days_off": 42},
            {"name": "Paddockwood",       "trainer": "Ben Pauling",                 "jockey": "Ben Jones",
             "odds": "40/1", "age": 5, "form": "5141",      "rating": 117,
             # racecard 1415 D BF: most recent = 5th
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "5th Hurdle Jan 2026", "days_off": 42},
            {"name": "Lord",              "trainer": "Donald McCain",               "jockey": "sp",
             "odds": "sp",   "age": 5, "form": "216111",    "rating": 116,
             # racecard 111612 D BF: most recent = 2nd
             "cheltenham_record": "Cheltenham course runner",
             "last_run": "2nd Hurdle Feb 2026", "days_off": 28},
            {"name": "Bandjo",            "trainer": "Georgina Nicholls",           "jockey": "Finn Lambert",
             "odds": "sp",   "age": 5, "form": "6F2176",    "rating": 115,
             # racecard 6712F6: most recent = 6th
             "cheltenham_record": None,
             "last_run": "6th Hurdle Feb 2026", "days_off": 28},
        ]
    },
    "day1_race4": {   # Ultima Handicap Chase (3m1f Hcap Chs, Class 2, 22 runners, 10 Mar 2026 15:20)
        # Confirmed 22-runner field from Betfair 08 Mar 2026
        # VERDICT: Jagwar (Willie Mullins / Paul Townend) — Won 2024 NH Chase at Cheltenham
        "entries": [
            {"name": "Jagwar",           "trainer": "Willie Mullins",      "jockey": "Paul Townend",
             "odds": "6/1",  "age": 9,  "form": "121312",  "rating": 163,
             "cheltenham_record": "Won 2024 National Hunt Chase",
             "last_run": "3rd Ryanair Chase Feb 2026", "days_off": 28},
            {"name": "Iroko",            "trainer": "Paul Nicholls",       "jockey": "Harry Cobden",
             "odds": "8/1",  "age": 9,  "form": "213241",  "rating": 158,
             "cheltenham_record": None, "last_run": "Won Hcap Chase Jan 2026", "days_off": 42},
            {"name": "Handstands",       "trainer": "Dan Skelton",         "jockey": "Harry Skelton",
             "odds": "10/1", "age": 8,  "form": "312124",  "rating": 155,
             "cheltenham_record": None, "last_run": "4th Hcap Chase Feb 2026", "days_off": 28},
            {"name": "Myretown",         "trainer": "Gordon Elliott",      "jockey": "Jack Kennedy",
             "odds": "10/1", "age": 8,  "form": "231431",  "rating": 154,
             "cheltenham_record": None, "last_run": "Won Hcap Chase Feb 2026", "days_off": 28},
            {"name": "Quebecois",        "trainer": "Henry de Bromhead",   "jockey": "Rachael Blackmore",
             "odds": "12/1", "age": 9,  "form": "142312",  "rating": 153,
             "cheltenham_record": None, "last_run": "2nd Hcap Chase Feb 2026", "days_off": 21},
            {"name": "Johnnywho",        "trainer": "Paul Nolan",          "jockey": "Bryan Cooper",
             "odds": "12/1", "age": 9,  "form": "312143",  "rating": 152,
             "cheltenham_record": None, "last_run": "3rd Hcap Chase Jan 2026", "days_off": 42},
            {"name": "Hyland",           "trainer": "Nicky Henderson",     "jockey": "Nico de Boinville",
             "odds": "14/1", "age": 9,  "form": "124312",  "rating": 151,
             "cheltenham_record": None, "last_run": "2nd Hcap Chase Feb 2026", "days_off": 28},
            {"name": "Konfusion",        "trainer": "Willie Mullins",      "jockey": "Patrick Mullins",
             "odds": "14/1", "age": 8,  "form": "231412",  "rating": 150,
             "cheltenham_record": None, "last_run": "2nd Hcap Chase Jan 2026", "days_off": 49},
            {"name": "The Short Go",     "trainer": "Gordon Elliott",      "jockey": "J. W. Kennedy",
             "odds": "16/1", "age": 9,  "form": "413231",  "rating": 149,
             "cheltenham_record": None, "last_run": "Won Hcap Chase Feb 2026", "days_off": 21},
            {"name": "Knight Of Allen",  "trainer": "Gavin Cromwell",      "jockey": "Danny Mullins",
             "odds": "16/1", "age": 10, "form": "323142",  "rating": 148,
             "cheltenham_record": None, "last_run": "2nd Hcap Chase Jan 2026", "days_off": 42},
            {"name": "Blaze The Way",    "trainer": "Nicky Henderson",     "jockey": "Nico de Boinville",
             "odds": "20/1", "age": 8,  "form": "131424",  "rating": 147,
             "cheltenham_record": None, "last_run": "4th Hcap Chase Feb 2026", "days_off": 28},
            {"name": "Imperial Saint",   "trainer": "Emmet Mullins",       "jockey": "M. P. Walsh",
             "odds": "20/1", "age": 8,  "form": "142312",  "rating": 146,
             "cheltenham_record": None, "last_run": "2nd Hcap Chase Feb 2026", "days_off": 21},
            {"name": "Resplendent Grey", "trainer": "Tom Lacey",           "jockey": "Tom Cannon",
             "odds": "20/1", "age": 8,  "form": "231344",  "rating": 145,
             "cheltenham_record": None, "last_run": "4th Hcap Chase Jan 2026", "days_off": 42},
            {"name": "The Doyen Chief",  "trainer": "James Moffatt",       "jockey": "James Bowen",
             "odds": "25/1", "age": 10, "form": "324131",  "rating": 144,
             "cheltenham_record": None, "last_run": "Won Hcap Chase Feb 2026", "days_off": 28},
            {"name": "Leave of Absence", "trainer": "Gordon Elliott",      "jockey": "Jack Kennedy",
             "odds": "25/1", "age": 9,  "form": "412332",  "rating": 143,
             "cheltenham_record": None, "last_run": "2nd Hcap Chase Feb 2026", "days_off": 21},
            {"name": "Search For Glory", "trainer": "Henry de Bromhead",   "jockey": "Rachael Blackmore",
             "odds": "25/1", "age": 9,  "form": "341223",  "rating": 142,
             "cheltenham_record": None, "last_run": "3rd Hcap Chase Feb 2026", "days_off": 28},
            {"name": "Blow Your Wad",    "trainer": "Philip Hobbs",        "jockey": "Tom O'Brien",
             "odds": "33/1", "age": 10, "form": "234141",  "rating": 141,
             "cheltenham_record": None, "last_run": "Won Hcap Chase Jan 2026", "days_off": 49},
            {"name": "Margarets Legacy", "trainer": "Paul Nicholls",       "jockey": "Harry Cobden",
             "odds": "33/1", "age": 9,  "form": "142314",  "rating": 140,
             "cheltenham_record": None, "last_run": "4th Hcap Chase Feb 2026", "days_off": 28},
            {"name": "Patter Merchant",  "trainer": "Nicky Henderson",     "jockey": "Nico de Boinville",
             "odds": "40/1", "age": 8,  "form": "213243",  "rating": 139,
             "cheltenham_record": None, "last_run": "3rd Hcap Chase Feb 2026", "days_off": 35},
            {"name": "Eyed",             "trainer": "Jonjo O'Neill",       "jockey": "Aidan Coleman",
             "odds": "40/1", "age": 10, "form": "342152",  "rating": 138,
             "cheltenham_record": None, "last_run": "2nd Hcap Chase Jan 2026", "days_off": 49},
            {"name": "Filanderer",       "trainer": "Alan King",           "jockey": "Tom Cannon",
             "odds": "50/1", "age": 10, "form": "231435",  "rating": 137,
             "cheltenham_record": None, "last_run": "5th Hcap Chase Feb 2026", "days_off": 28},
            {"name": "Stolen Silver",    "trainer": "Venetia Williams",    "jockey": "Charlie Deutsch",
             "odds": "50/1", "age": 10, "form": "324241",  "rating": 136,
             "cheltenham_record": None, "last_run": "Won Hcap Chase Dec 2025", "days_off": 70},
        ]
    },
    "day1_race6": {   # Cheltenham Plate Chase (Class 1, 2m4f Hcap Chs, 23 runners, 10 Mar 2026)
        # NOTE: form strings stored most-recent-first (reversed from racecard UK convention)
        # VERDICT: Madara (Dan Skelton / Harry Skelton) — C=Cheltenham course winner, eye-catching 2nd Kempton
        "entries": [
            {"name": "McLaurey",           "trainer": "Emmet Mullins",           "jockey": "M. P. Walsh",
             "odds": "15/2", "age": 7, "form": "473401",  "rating": 155,
             # racecard 10-4374: most recent = 4th
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Madara",             "trainer": "Dan Skelton",             "jockey": "Harry Skelton",
             "odds": "9/2",  "age": 8, "form": "252489",  "rating": 158,
             # racecard 9/842-52 C (Cheltenham course winner): most recent = 2nd Kempton
             "cheltenham_record": "Won Cheltenham Plate Chase 2024",
             "last_run": "2nd Handicap Chase Kempton Feb 2026", "days_off": 35},
            {"name": "Will The Wise",      "trainer": "Gavin Cromwell",          "jockey": "Keith Donoghue",
             "odds": "7/1",  "age": 7, "form": "041225",  "rating": 153,
             # racecard 5-22140 BF: most recent = 0 (tailed off)
             "cheltenham_record": None,
             "last_run": "Last Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Downmexicoway",      "trainer": "Henry de Bromhead",       "jockey": "D. J. O'Keeffe",
             "odds": "9/1",  "age": 8, "form": "31210P",  "rating": 150,
             # racecard P01213: most recent = 3rd
             "cheltenham_record": None,
             "last_run": "3rd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Zurich",             "trainer": "Henry de Bromhead",       "jockey": "B. Hayes",
             "odds": "8/1",  "age": 9, "form": "311035",  "rating": 155,
             # racecard 530-113 CD: most recent = 3rd
             "cheltenham_record": "Won Cheltenham 2m4f Chase 2023",
             "last_run": "3rd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Down Memory Lane",   "trainer": "Gordon Elliott",          "jockey": "Jack Kennedy",
             "odds": "10/1", "age": 9, "form": "104231",  "rating": 155,
             # racecard 1324-01 D: most recent = 1 (WIN)
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Booster Bob",        "trainer": "Olly Murphy",             "jockey": "Sean Bowen",
             "odds": "10/1", "age": 7, "form": "511323",  "rating": 150,
             # racecard 3231-15 D: most recent = 5th
             "cheltenham_record": None,
             "last_run": "5th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Dee Capo",           "trainer": "Gordon Elliott",          "jockey": "Danny Gilligan",
             "odds": "10/1", "age": 8, "form": "4U1041",  "rating": 148,
             # racecard 140-1U4: most recent = 4th
             "cheltenham_record": None,
             "last_run": "4th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "No Questions Asked", "trainer": "Ben Pauling",             "jockey": "Ben Jones",
             "odds": "12/1", "age": 7, "form": "132101",  "rating": 148,
             # racecard 10-1231: most recent = 1 (WIN)
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "OMoore Park",        "trainer": "Willie Mullins",          "jockey": "S. F. O'Keeffe",
             "odds": "12/1", "age": 8, "form": "050202",  "rating": 148,
             # racecard 20-2050 D: most recent = 0 (last)
             "cheltenham_record": None,
             "last_run": "Last Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Peaky Boy",          "trainer": "Jonjo O'Neill",           "jockey": "Jonjo O'Neill Jr.",
             "odds": "16/1", "age": 8, "form": "F33111",  "rating": 148,
             # racecard 11/133-F CD: most recent = Fell; two wins in recent form
             "cheltenham_record": "Won Cheltenham 2m4f Chase 2023",
             "last_run": "Fell Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Guard Your Dreams",  "trainer": "Nigel Twiston-Davies",    "jockey": "Sam Twiston-Davies",
             "odds": "16/1", "age": 8, "form": "12F474",  "rating": 145,
             # racecard 474F-21 C+D: most recent = 1 (WIN)
             "cheltenham_record": "Won Cheltenham 2m4f Chase 2024",
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Midnight It Is",     "trainer": "Gavin Cromwell",          "jockey": "Sean Flanagan",
             "odds": "40/1", "age": 9, "form": "790383",  "rating": 142,
             # racecard 383-097: most recent = 7th
             "cheltenham_record": None,
             "last_run": "7th Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Jungle Boogie",      "trainer": "Venetia Williams",        "jockey": "Charlie Deutsch",
             "odds": "25/1", "age": 7, "form": "P7P161",  "rating": 140,
             # racecard 16/1P-7P D: most recent = P (pulled up)
             "cheltenham_record": None,
             "last_run": "P Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Jipcot",             "trainer": "Jonjo O'Neill",           "jockey": "Kielan Woods",
             "odds": "25/1", "age": 7, "form": "413P04",  "rating": 140,
             # racecard 40P-314 D+BF: most recent = 4th
             "cheltenham_record": None,
             "last_run": "4th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Theatre Native",     "trainer": "Henry de Bromhead",       "jockey": "M. P. O'Connor",
             "odds": "25/1", "age": 8, "form": "693012",  "rating": 142,
             # racecard 21-0396 CD: most recent = 6th
             "cheltenham_record": "Won Cheltenham 2m4f Chase 2022",
             "last_run": "6th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Riskintheground",    "trainer": "Dan Skelton",             "jockey": "Charlie Todd",
             "odds": "25/1", "age": 8, "form": "940691",  "rating": 140,
             # racecard 196049 CD: most recent = 9th
             "cheltenham_record": "Won Cheltenham 2m4f 2023",
             "last_run": "9th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Boombawn",           "trainer": "Dan Skelton",             "jockey": "Tristan Durrell",
             "odds": "33/1", "age": 7, "form": "083445",  "rating": 137,
             # racecard 5-44380 D: most recent = 0 (last)
             "cheltenham_record": None,
             "last_run": "Last Handicap Chase Feb 2026", "days_off": 42},
            {"name": "Grandeur Dame",      "trainer": "Alan King",               "jockey": "Tom Bellamy",
             "odds": "40/1", "age": 8, "form": "P30FP0",  "rating": 135,
             # racecard 0P-F03P: most recent = P (pulled up)
             "cheltenham_record": None,
             "last_run": "P Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Moon Dorange",       "trainer": "John McConnell",          "jockey": "Callum Pritchard",
             "odds": "40/1", "age": 7, "form": "076500",  "rating": 135,
             # racecard 005670 CD: most recent = 0 (last)
             "cheltenham_record": "Won Cheltenham 2m4f Chase 2024",
             "last_run": "Last Handicap Chase Jan 2026", "days_off": 56},
            {"name": "Western Zephyr",     "trainer": "Mickey Bowen",            "jockey": "Shane Fenelon",
             "odds": "40/1", "age": 7, "form": "2P0321",  "rating": 132,
             # racecard 1230P-2: most recent = 2nd
             "cheltenham_record": None,
             "last_run": "2nd Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Yes Indeed",         "trainer": "Martin Keighley",         "jockey": "Freddie Keighley",
             "odds": "50/1", "age": 8, "form": "43P11P",  "rating": 130,
             # racecard P11-P34: most recent = 4th
             "cheltenham_record": None,
             "last_run": "4th Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Embittered",         "trainer": "Syd Hosie",               "jockey": "Paddy Hanlon",
             "odds": "80/1", "age": 8, "form": "72P917",  "rating": 128,
             # racecard 719P27 D: most recent = 7th
             "cheltenham_record": None,
             "last_run": "7th Handicap Chase Jan 2026", "days_off": 42},
        ]
    },
    "day1_race7": {   # Challenge Cup Chase (3m6f Nov Hcap Chs, Class 2, 17 runners, 10 Mar 2026)
        # NOTE: form strings stored most-recent-first (reversed from racecard UK convention)
        # to match scorer's startswith() recency logic.
        "entries": [
            {"name": "Backmersackme",    "trainer": "Emmet Mullins",            "jockey": "Donagh Meyler",
             "odds": "7/2",  "age": 8, "form": "102876",  "rating": 152,
             # racecard "6-78201": most recent = 1(WIN), then 0, 2, 8, 7, 6
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Leopardstown Feb 2026", "days_off": 28},
            {"name": "Newton Tornado",   "trainer": "Rebecca Curtis",           "jockey": "Sean Flanagan",
             "odds": "9/2",  "age": 7, "form": "1P1F12",  "rating": 148,
             # racecard "21-F1P1": most recent = 1(WIN), then P, 1, F, 1, 2
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
            {"name": "Wade Out",         "trainer": "Olly Murphy",              "jockey": "Sean Bowen",
             "odds": "11/2", "age": 8, "form": "411616",  "rating": 145,
             # racecard "616-114": most recent = 4(4th), before = 1,1 (two wins)
             "cheltenham_record": "Cheltenham winner",
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "King Of Answers",  "trainer": "Lucinda Russell",          "jockey": "Derek Fox",
             "odds": "10/1", "age": 9, "form": "14152P",  "rating": 143,
             # racecard "P2-5141": most recent = 1(WIN)
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "One Big Bang",     "trainer": "James Owen",               "jockey": "Alex Chadwick",
             "odds": "10/1", "age": 8, "form": "312351",  "rating": 141,
             # racecard "15-3213": most recent = 3(3rd)
             "cheltenham_record": None,
             "last_run": "3rd Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Guard The Moon",   "trainer": "Nigel Twiston-Davies",     "jockey": "Sam Twiston-Davies",
             "odds": "10/1", "age": 8, "form": "1P1FP8",  "rating": 140,
             # racecard "8PF-1P1": most recent = 1(WIN), poor_form: 2 P's
             "cheltenham_record": None,
             "last_run": "Won Chase Jan 2026", "days_off": 42},
            {"name": "Iceberg Theory",   "trainer": "Paul Nolan",               "jockey": "C Stone-Walsh",
             "odds": "8/1",  "age": 7, "form": "112P63",  "rating": 147,
             # racecard "36P2-11": most recent = 1,1 (two consecutive wins)
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Cork Nov 2025", "days_off": 119},
            {"name": "Grand Geste",      "trainer": "Joel Parkinson",           "jockey": "Danny McMenamin",
             "odds": "12/1", "age": 9, "form": "1P122P",  "rating": 138,
             # racecard "P-221P1": most recent = 1(WIN), 2 P's penalty
             "cheltenham_record": None,
             "last_run": "Won Chase Feb 2026", "days_off": 28},
            {"name": "Walking On Air",   "trainer": "Faye Bramley",             "jockey": "Harry Cobden",
             "odds": "14/1", "age": 9, "form": "38P0F3",  "rating": 133,
             # racecard "3F0P-83": most recent = 3(3rd)
             "cheltenham_record": None,
             "last_run": "8th Chase Feb 2026", "days_off": 28},
            {"name": "Pic Roc",          "trainer": "Ben Pauling",              "jockey": "Ben Jones",
             "odds": "16/1", "age": 8, "form": "1951U6",  "rating": 135,
             # racecard "6-U1591": most recent = 1(WIN)
             "cheltenham_record": None,
             "last_run": "9th Chase Feb 2026", "days_off": 28},
            {"name": "Holloway Queen",   "trainer": "Nicky Henderson",          "jockey": "James Bowen",
             "odds": "16/1", "age": 8, "form": "14UPP4",  "rating": 136,
             # racecard "4P-PU41": most recent = 1(WIN), 2 P's penalty
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "First Confession", "trainer": "Joe Tizzard",              "jockey": "Brendan Powell",
             "odds": "20/1", "age": 8, "form": "1F533P",  "rating": 131,
             # racecard "P-335F1": most recent = 1(WIN), 1 P penalty
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Kurasso Blue",     "trainer": "Gordon Elliott",           "jockey": "J W Kennedy",
             "odds": "9/1",  "age": 6, "form": "212151",  "rating": 146,
             # racecard "151-212": most recent = 2(2nd), no consecutive wins from front
             "cheltenham_record": None,
             "last_run": "2nd Novice Chase Jan 2026", "days_off": 42},
            {"name": "Will Do",          "trainer": "Gordon Elliott",           "jockey": "Danny Gilligan",
             "odds": "25/1", "age": 7, "form": "P02070",  "rating": 128,
             # racecard "0-7020P": most recent = P(pulled up)
             "cheltenham_record": None,
             "last_run": "P Chase Jan 2026", "days_off": 42},
            {"name": "Union Station",    "trainer": "Gavin Cromwell",           "jockey": "Keith Donoghue",
             "odds": "25/1", "age": 8, "form": "U2P262",  "rating": 130,
             # racecard "26-2P2U": most recent = U(unseated)
             "cheltenham_record": None,
             "last_run": "Unseated Chase Jan 2026", "days_off": 42},
            {"name": "Silver Thorn",     "trainer": "Emma Lavelle",             "jockey": "Jonathan Burke",
             "odds": "25/1", "age": 8, "form": "4115P2",  "rating": 134,
             # racecard "2P-5114": most recent = 4(4th), two wins before
             "cheltenham_record": None,
             "last_run": "Won Chase Jan 2026", "days_off": 42},
            {"name": "Holokea",          "trainer": "Mickey Bowen",             "jockey": "Shane Fenelon",
             "odds": "33/1", "age": 8, "form": "922212",  "rating": 126,
             # racecard "212229": most recent = 9(9th)
             "cheltenham_record": None,
             "last_run": "9th Chase Feb 2026", "days_off": 28},
        ]
    },
    "day2_race1": {   # Turner's Novices' Hurdle  (Grade 1, 2m5f — 33 runners, Wed 11 Mar 13:20)
        # Full official racecard including horses previously misplaced in Supreme / Albert Bartlett
        "entries": [
            {"name": "Talk The Talk", "trainer": "Joseph Patrick O'Brien", "jockey": "J.J. Slevin",
             "odds": "6/1", "age": 5, "form": "1-F-1-1-2", "rating": 149,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "King Rasko Grey", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "8/1", "age": 5, "form": "1-1-3-1", "rating": 146,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Skylight Hustle", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "8/1", "age": 6, "form": "1-1-1-2-4", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "No Drama This End", "trainer": "Paul Nicholls", "jockey": "Harry Cobden",
             "odds": "10/1", "age": 6, "form": "1-1-1-9-1", "rating": 144,
             "cheltenham_record": "CD winner",
             "last_run": "Won Grade 1 Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "I'll Sort That", "trainer": "Declan Queally", "jockey": "TBD",
             "odds": "12/1", "age": 6, "form": "1-1-1-1-1-2", "rating": 142,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Ballyfad", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "12/1", "age": 5, "form": "2-1-1-1-1", "rating": 147,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Act Of Innocence", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "10/1", "age": 6, "form": "1-2-1-1-4", "rating": 138,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Koktail Brut", "trainer": "Gordon Elliott", "jockey": "Danny Gilligan",
             "odds": "20/1", "age": 5, "form": "4-7-1-1-5-3", "rating": 140,
             "cheltenham_record": None,
             "last_run": "4th Grade 1 Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Hurricane Pat", "trainer": "G L Moore", "jockey": "Caoilin Quinn",
             "odds": "20/1", "age": 6, "form": "2-1-1-1-3", "rating": 136,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Klimt Madrik", "trainer": "T Lawes", "jockey": "K Brogan",
             "odds": "20/1", "age": 6, "form": "2-2-1-4-4-3", "rating": 138,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Taurus Bay", "trainer": "Ben Pauling", "jockey": "Ben Jones",
             "odds": "25/1", "age": 6, "form": "2-1-1-1-1", "rating": 135,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Kripticjim", "trainer": "Joe Tizzard", "jockey": "Brendan Powell",
             "odds": "25/1", "age": 6, "form": "1-2-2", "rating": 135,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Bossman Jack", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "25/1", "age": 5, "form": "1-1-3-1", "rating": 134,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Riskaway", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "25/1", "age": 6, "form": "2-2-1-2-4-2", "rating": 134,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Road Exile", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "25/1", "age": 6, "form": "2-1-3-1", "rating": 134,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Came From Nowhere", "trainer": "Jeremy Scott", "jockey": "Lorcan Williams",
             "odds": "33/1", "age": 7, "form": "1-1-2-3", "rating": 132,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Fortune Timmy", "trainer": "Chris Gordon", "jockey": "Freddie Gordon",
             "odds": "33/1", "age": 7, "form": "3-1-3-1-2", "rating": 132,
             "cheltenham_record": None,
             "last_run": "3rd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Johnny's Jury", "trainer": "Jamie Snowden", "jockey": "TBD",
             "odds": "33/1", "age": 6, "form": "1-1-3", "rating": 129,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Shuttle Diplomacy", "trainer": "Thomas Cooper", "jockey": "TBD",
             "odds": "33/1", "age": 7, "form": "1-2-7-p-5-3", "rating": 133,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Soldier Reeves", "trainer": "Dan Skelton", "jockey": "Tristan Durrell",
             "odds": "33/1", "age": 6, "form": "3-2-1-3-2", "rating": 131,
             "cheltenham_record": None,
             "last_run": "3rd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Too Bossy For Us", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "33/1", "age": 5, "form": "1-0-3-0-2-5", "rating": 131,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Walks In June", "trainer": "Henry de Bromhead", "jockey": "Jack Kennedy",
             "odds": "33/1", "age": 6, "form": "1-1-6-1-5", "rating": 131,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Zeus Power", "trainer": "Joseph Patrick O'Brien", "jockey": "TBD",
             "odds": "33/1", "age": 5, "form": "1-1-2-3-2", "rating": 131,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Sober", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "33/1", "age": 6, "form": "1-1-1-1-5", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Leader D'Allier", "trainer": "Willie Mullins", "jockey": "Patrick Mullins",
             "odds": "33/1", "age": 5, "form": "1-2-1-6", "rating": 128,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Baron Noir", "trainer": "Alan King", "jockey": "Tom Bellamy",
             "odds": "33/1", "age": 6, "form": "1-1-2-1-3", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Jalon D'Oudairies", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "40/1", "age": 5, "form": "1-1-3", "rating": 126,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Laurets D'Estruval", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "40/1", "age": 5, "form": "1-2-2", "rating": 124,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Saint Baco", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "50/1", "age": 6, "form": "6-1-3-4", "rating": 120,
             "cheltenham_record": None,
             "last_run": "6th Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Sortudo", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "50/1", "age": 6, "form": "3-2-2-2-1", "rating": 122,
             "cheltenham_record": None,
             "last_run": "3rd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Doujadou", "trainer": "Rebecca Curtis", "jockey": "Sean Bowen",
             "odds": "50/1", "age": 7, "form": "2-1-c-p", "rating": 118,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Free Spirit", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "66/1", "age": 5, "form": "3-1-2", "rating": 115,
             "cheltenham_record": None,
             "last_run": "3rd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "It's Top", "trainer": "Oliver Signy", "jockey": "TBD",
             "odds": "100/1", "age": 7, "form": "1-2-7-7-1", "rating": 116,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day2_race2": {   # Brown Advisory Novices' Chase  (Grade 1, 3m1f — 18 runners, Wed 11 Mar 14:00)
        "entries": [
            {"name": "Kaid D'Authie", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "6/4", "age": 6, "form": "1-1-2-1-p-4", "rating": 158,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Romeo Coolio", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "7/2", "age": 7, "form": "1-1-1-1-2-3", "rating": 157,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Western Fold", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "5/1", "age": 7, "form": "2-3-1-1-1-1", "rating": 157,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Final Demand", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "8/1", "age": 7, "form": "3-1-1-1-3-1", "rating": 156,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Kitzbuhel", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "10/1", "age": 7, "form": "u-1-0-1-3-5", "rating": 153,
             "cheltenham_record": None,
             "last_run": "Unseated Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Thomas Mor", "trainer": "Philip Hobbs", "jockey": "TBD",
             "odds": "12/1", "age": 7, "form": "2-2-1-0-4-1", "rating": 147,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Wendigo", "trainer": "Jamie Snowden", "jockey": "Gavin Sheehan",
             "odds": "12/1", "age": 7, "form": "1-3-1-2-5-1", "rating": 147,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Feb 2026", "days_off": 28},
            {"name": "The Big Westerner", "trainer": "Henry de Bromhead", "jockey": "Jack Kennedy",
             "odds": "12/1", "age": 7, "form": "1-1-2-p-2-1", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Koktail Divin", "trainer": "Henry de Bromhead", "jockey": "Jack Kennedy",
             "odds": "14/1", "age": 8, "form": "1-1-2-2-4-1", "rating": 149,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Oscars Brother", "trainer": "Connor King", "jockey": "TBD",
             "odds": "14/1", "age": 7, "form": "1-1-1-2-2-f", "rating": 151,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Predators Gold", "trainer": "Willie Mullins", "jockey": "Patrick Mullins",
             "odds": "16/1", "age": 7, "form": "3-1-3-5-2", "rating": 146,
             "cheltenham_record": None,
             "last_run": "3rd Grade 2 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Salver", "trainer": "G L Moore", "jockey": "Caoilin Quinn",
             "odds": "16/1", "age": 6, "form": "1-1-3-2-3-1", "rating": 149,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
            {"name": "Gold Dancer", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "16/1", "age": 7, "form": "4-2-2-1-1-1", "rating": 148,
             "cheltenham_record": None,
             "last_run": "4th Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Argento Boy", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "20/1", "age": 6, "form": "1-1-f-5-7-0", "rating": 144,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Now Is The Hour", "trainer": "Gavin Cromwell", "jockey": "TBD",
             "odds": "20/1", "age": 8, "form": "1-4-8-3-1-f-p", "rating": 149,
             "cheltenham_record": "CD winner",
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
            {"name": "Ol Man Dingle", "trainer": "Eoin Griffin", "jockey": "TBD",
             "odds": "25/1", "age": 7, "form": "5-5-1-1-4", "rating": 143,
             "cheltenham_record": None,
             "last_run": "5th Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Rushmount", "trainer": "Jonathan Sweeney", "jockey": "TBD",
             "odds": "33/1", "age": 8, "form": "1-1-5-5-4-0", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
            {"name": "Joystick", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "33/1", "age": 7, "form": "1-6-4-7-p-2", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
        ]
    },
    "day2_race3": {   # BetMGM Cup Handicap Hurdle  (Grade 3, 2m5f — 60 runners, Wed 11 Mar 14:40)
        # Top runners by Official Rating from official racecard
        "entries": [
            {"name": "Ndaawi", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "10/1", "age": 6, "form": "3-3-6-4-1-2", "rating": 156,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Hurdle Feb 2026", "days_off": 28},
            {"name": "The Yellow Clay", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "10/1", "age": 7, "form": "3-5-2-f-2-1", "rating": 155,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Maxxum", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "12/1", "age": 8, "form": "3-3-3-4-1-p", "rating": 152,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Storm Heart", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "8/1", "age": 6, "form": "1-1-2-4-5", "rating": 151,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Lucky Place", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "12/1", "age": 7, "form": "3-2-3-4-7-1", "rating": 151,
             "cheltenham_record": "CD winner",
             "last_run": "3rd Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Jingko Blue", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "14/1", "age": 7, "form": "2-7-u-1-1", "rating": 144,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Iberico Lord", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "14/1", "age": 7, "form": "1-9-9-0-0-4", "rating": 144,
             "cheltenham_record": "CD winner",
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "I Started A Joke", "trainer": "C Byrnes", "jockey": "Danny Mullins",
             "odds": "16/1", "age": 7, "form": "2-1-4-3-4", "rating": 143,
             "cheltenham_record": None,
             "last_run": "4th Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Galileo Dame", "trainer": "Joseph O'Brien", "jockey": "J.J. Slevin",
             "odds": "16/1", "age": 6, "form": "1-0-2-0-0-0", "rating": 136,
             # note: 131+5 penalty = effective 136
             "cheltenham_record": None,
             "last_run": "Won Grade 3 Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Jump Allen", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "20/1", "age": 6, "form": "1-1-2-1-3-4", "rating": 133,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Kateira", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "20/1", "age": 7, "form": "1-2-3-4-1", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Won Hurdle Jan 2026", "days_off": 42},
            {"name": "Workahead", "trainer": "Henry de Bromhead", "jockey": "Jack Kennedy",
             "odds": "25/1", "age": 8, "form": "4-2-1-1-1", "rating": 140,
             "cheltenham_record": None,
             "last_run": "Won Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day2_race4": {   # Glenfarclas Cross Country Chase  (Grade 2, ~4m — 18 runners, Wed 11 Mar 15:20)
        "entries": [
            {"name": "Stumptown", "trainer": "Gavin Cromwell", "jockey": "Danny Mullins",
             "odds": "3/1", "age": 9, "form": "1-1-1-2-1", "rating": 162,
             "cheltenham_record": "Won 2025 Glenfarclas Cross Country Chase",
             "last_run": "Won Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Favori De Champdou", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "7/2", "age": 11, "form": "1-1-2-1-1-1", "rating": 157,
             "cheltenham_record": "Won 2024 Glenfarclas Cross Country Chase",
             "last_run": "Won Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Final Orders", "trainer": "Gavin Cromwell", "jockey": "TBD",
             "odds": "7/1", "age": 8, "form": "5-1-3-6-4-0", "rating": 147,
             "cheltenham_record": "CD winner",
             "last_run": "5th Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Vanillier", "trainer": "Gavin Cromwell", "jockey": "Brian Hayes",
             "odds": "7/1", "age": 10, "form": "1-1-1-2-3", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Cross Country Chase Feb 2026", "days_off": 28},
            {"name": "Conflated", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "10/1", "age": 11, "form": "3-2-4-4-5-3", "rating": 145,
             "cheltenham_record": None,
             "last_run": "3rd Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Pied Piper", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "10/1", "age": 8, "form": "f-9-2-6-5-3", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Fell Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Desertmore House", "trainer": "Martin Brassil", "jockey": "Keith Donoghue",
             "odds": "10/1", "age": 11, "form": "1-1-3-6-0-2", "rating": 140,
             "cheltenham_record": "Placed Cross Country 2024",
             "last_run": "Won Amateur Cross Country Feb 2026", "days_off": 28},
            {"name": "Chemical Energy", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "12/1", "age": 8, "form": "1-8-0-1-1-0-4", "rating": 141,
             "cheltenham_record": "CD winner",
             "last_run": "Won Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Anibale Fly", "trainer": "Tony Martin", "jockey": "Mark Walsh",
             "odds": "20/1", "age": 14, "form": "2-3-1-5-2", "rating": 142,
             "cheltenham_record": "Cross Country specialist",
             "last_run": "2nd Cross Country Jan 2026", "days_off": 42},
        ]
    },
    "day2_race6": {   # Grand Annual Handicap Chase  (Grade 3, 2m — 37 runners, Wed 11 Mar 16:40)
        "entries": [
            {"name": "Touch Me Not", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "6/1", "age": 8, "form": "2-2-3-4-4-5", "rating": 155,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Calico", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "7/1", "age": 8, "form": "4-1-1-2-3-4", "rating": 153,
             "cheltenham_record": None,
             "last_run": "4th Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Edwardstone", "trainer": "Alan King", "jockey": "TBD",
             "odds": "8/1", "age": 13, "form": "4-4-1-2-5-5", "rating": 151,
             "cheltenham_record": "Won 2022 Arkle Challenge Trophy; CD winner",
             "last_run": "4th Handicap Chase Jan 2026", "days_off": 42},
            {"name": "No Questions Asked", "trainer": "Ben Pauling", "jockey": "Ben Jones",
             "odds": "10/1", "age": 7, "form": "1-1-3-2-0-1", "rating": 149,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Rubaud", "trainer": "Paul Nicholls", "jockey": "TBD",
             "odds": "10/1", "age": 8, "form": "2-2-2-1-1-3", "rating": 148,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Be Aware", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "12/1", "age": 8, "form": "2-2-2-1-1-8", "rating": 147,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Inthepocket", "trainer": "Henry de Bromhead", "jockey": "Rachael Blackmore",
             "odds": "14/1", "age": 7, "form": "5-f-3-5", "rating": 146,
             "cheltenham_record": None,
             "last_run": "5th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Vanderpoel", "trainer": "Ben Pauling", "jockey": "TBD",
             "odds": "14/1", "age": 6, "form": "1-1-2-3-1-p", "rating": 141,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Jour D'Evasion", "trainer": "H D Daly", "jockey": "Sam Twiston-Davies",
             "odds": "16/1", "age": 8, "form": "1-1-1-5-1-4", "rating": 137,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Coeur De Lion", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "16/1", "age": 8, "form": "1-2-1-1-1", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Dancewiththedevil", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "16/1", "age": 7, "form": "2-1-1-2-1", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Waterbys Hurricane", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "20/1", "age": 8, "form": "1-2-3-3-1", "rating": 141,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Chase Feb 2026", "days_off": 28},
        ]
    },
    "day3_race1": {   # Ryanair Mares' Novices' Hurdle  (Grade 1, 2m1f, Day 3 13:20)
        "entries": [
            {"name": "Bambino Fever", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "4/5", "age": 5, "form": "1-1-1", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Oldschool Outlaw", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "4/1", "age": 6, "form": "2-1-1-11", "rating": 140,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Echoing Silence", "trainer": "Henry de Bromhead", "jockey": "Jack Kennedy",
             "odds": "10/1", "age": 5, "form": "1-2-1-21", "rating": 135,
             "cheltenham_record": None,
             "last_run": "2nd Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "La Conquiere", "trainer": "Jamie Snowden", "jockey": "Gavin Sheehan",
             "odds": "14/1", "age": 5, "form": "1-2-1-11", "rating": 133,
             "cheltenham_record": None,
             "last_run": "Won Mares Novice Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day2_race7": {   # Weatherbys Champion Bumper  (Grade 1, 2m1f — 32 runners, Wed 11 Mar 17:20)
        "entries": [
            {"name": "The Irish Avatar", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "5/1", "age": 5, "form": "2-1", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Won INH Flat Feb 2026", "days_off": 28},
            {"name": "Keep Him Company", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "5/1", "age": 6, "form": "1-1", "rating": 132,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Bumper Jan 2026", "days_off": 42},
            {"name": "Quiryn", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "7/1", "age": 4, "form": "1", "rating": 128,
             "cheltenham_record": None,
             "last_run": "Won INH Flat Feb 2026", "days_off": 28},
            {"name": "Broadway Ted", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "10/1", "age": 5, "form": "3-1", "rating": 125,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Bumper Jan 2026", "days_off": 42},
            {"name": "With Nolimit", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "12/1", "age": 5, "form": "1-4-1-2", "rating": 126,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Bumper Feb 2026", "days_off": 28},
            {"name": "Wilde's Legacy", "trainer": "Jamie Snowden", "jockey": "Gavin Sheehan",
             "odds": "14/1", "age": 5, "form": "1-1", "rating": 122,
             "cheltenham_record": None,
             "last_run": "Won Bumper Feb 2026", "days_off": 28},
            {"name": "Moonverrin", "trainer": "Martin Hassett", "jockey": "Mr F. Maguire",
             "odds": "16/1", "age": 5, "form": "2-1-1", "rating": 120,
             "cheltenham_record": None,
             "last_run": "Won Bumper Feb 2026", "days_off": 28},
            {"name": "Bass Hunter", "trainer": "Chris Gordon", "jockey": "Freddie Gordon",
             "odds": "16/1", "age": 5, "form": "1", "rating": 118,
             "cheltenham_record": "CD winner",
             "last_run": "Won Bumper Feb 2026", "days_off": 28},
            {"name": "No Walkover", "trainer": "David Pipe", "jockey": "Jack Tudor",
             "odds": "20/1", "age": 5, "form": "2-1-1-8", "rating": 116,
             "cheltenham_record": "CD winner",
             "last_run": "8th Grade 1 Bumper Jan 2026", "days_off": 42},
            {"name": "Charismatic Kid", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "20/1", "age": 5, "form": "2-1", "rating": 115,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Bumper Jan 2026", "days_off": 42},
            {"name": "Love Sign d'Aunou", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "25/1", "age": 5, "form": "1", "rating": 112,
             "cheltenham_record": None,
             "last_run": "Won Bumper Jan 2026", "days_off": 42},
        ]
    },
    "day3_race2": {   # Jack Richards Novices' Chase  (Grade 1, 2m4f, Day 3 14:00)
        "entries": [
            {"name": "Koktail Divin", "trainer": "Henry de Bromhead", "jockey": "Jack Kennedy",
             "odds": "9/2", "age": 7, "form": "1-1-1-21", "rating": 162,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Regent's Stroll", "trainer": "Paul Nicholls", "jockey": "Harry Cobden",
             "odds": "6/1", "age": 6, "form": "1-1-1-11", "rating": 157,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Meetmebythesea", "trainer": "Ben Pauling", "jockey": "Jonjo O'Neill Jr",
             "odds": "6/1", "age": 8, "form": "1-2-1-11", "rating": 156,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Slade Steel", "trainer": "Henry de Bromhead", "jockey": "Jack Kennedy",
             "odds": "9/1", "age": 7, "form": "3-1-1-31", "rating": 151,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Grey Dawning", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "10/1", "age": 9, "form": "3-1-2-P1", "rating": 155,
             "cheltenham_record": "3rd 2025 Gold Cup",
             "last_run": "Won Grade 2 Chase Feb 2026", "days_off": 28},
        ]
    },
    "day3_race6": {   # Pertemps Handicap Hurdle  (Grade 3, 3m, Day 3 16:40)
        "entries": [
            {"name": "Supremely West", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "9/2", "age": 8, "form": "1-2-1-11", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Pertemps Qualifier Feb 2026", "days_off": 28},
            {"name": "C'Est Different", "trainer": "Sam Thomas", "jockey": "Tom O'Brien",
             "odds": "10/1", "age": 9, "form": "2-1-2-11", "rating": 147,
             "cheltenham_record": None,
             "last_run": "Won Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Electric Mason", "trainer": "Chris Gordon", "jockey": "Tom Cannon",
             "odds": "12/1", "age": 8, "form": "1-3-2-11", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Ace Of Spades", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "12/1", "age": 7, "form": "1-2-3-31", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Pertemps Qualifier Feb 2026", "days_off": 28},
            {"name": "Minella Emperor", "trainer": "Emmet Mullins", "jockey": "Rob James",
             "odds": "12/1", "age": 7, "form": "2-1-2-11", "rating": 146,
             "cheltenham_record": None,
             "last_run": "Won Pertemps Qual Jan 2026", "days_off": 42},
            # Shantreusse removed — NOT in Betfair ANTEPOST 2026-03-06 (not entered)
        ]
    },
    "day3_race5": {   # Ryanair Chase  (Grade 1, 2m5f, Day 3 16:00)
        # NB: Jonbon/Heart Wood/Gaelic Warrior/Banbridge moved to Gold Cup field
        # Panic Attack, Protektorat, Jagwar, Energumene etc added via
        # cheltenham_full_fields_2026.ADDITIONAL_RUNNERS["day3_race5"]
        "entries": [
            {"name": "Fact To File", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "4/5", "age": 8, "form": "1-1-1-11", "rating": 179,
             "cheltenham_record": "Won 2024 Ryanair Chase; Won 2025 Ryanair Chase",
             "last_run": "Won Grade 1 Ryanair Chase Trial 2m5f Jan 2026", "days_off": 42,
             "ground_pref": "soft", "dist_class_form": "Won Grade 1 Ryanair Chase 2m5f Cheltenham ×2"},
        ]
    },
    "day1_race6_plate": {   # Cheltenham Plate Chase  (Day 1 16:40) — field data archive
        "entries": [
            {"name": "Madara", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "4/1", "age": 8, "form": "1-2-1-11", "rating": 156,
             "cheltenham_record": None,
             "last_run": "Won Grade 3 Handicap Chase Feb 2026", "days_off": 28},
            {"name": "McLaurey", "trainer": "Emmet Mullins", "jockey": "Rob James",
             "odds": "4/1", "age": 9, "form": "2-1-3-11", "rating": 153,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Will The Wise", "trainer": "Gavin Cromwell", "jockey": "Danny Mullins",
             "odds": "12/1", "age": 8, "form": "1-3-2-11", "rating": 150,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Down Memory Lane", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "14/1", "age": 9, "form": "2-1-1-43", "rating": 148,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Chase Feb 2026", "days_off": 28},
            # Grange Walk removed — not entered for Cheltenham (Betfair ANTEPOST: absent)
        ]
    },
    "day3_race7": {   # Kim Muir Handicap Chase  (Grade 3, 3m2f, amateur riders, Day 3 17:20)
        "entries": [
            {"name": "Weveallbeencaught", "trainer": "Gordon Elliott", "jockey": "Derek O'Connor (am)",
             "odds": "8/1", "age": 9, "form": "1-2-1-11", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Campers Rock", "trainer": "Gavin Cromwell", "jockey": "Derek O'Connor (am)",
             "odds": "10/1", "age": 8, "form": "2-1-1-21", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Brave Kingdom", "trainer": "Nicky Henderson", "jockey": "Harry Bannister (am)",
             "odds": "10/1", "age": 8, "form": "1-2-3-11", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Hunters Chase Feb 2026", "days_off": 28},
            {"name": "Rivella Reina", "trainer": "Willie Mullins", "jockey": "Patrick Mullins (am)",
             "odds": "12/1", "age": 7, "form": "1-1-2-31", "rating": 141,
             "cheltenham_record": None,
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
        ]
    },
    "day4_race1": {   # JCB Triumph Hurdle  (Grade 1, 2m1f, 4yo juveniles)
        "entries": [
            {"name": "Proactif", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "7/2", "age": 4, "form": "1-1", "rating": 139,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Selma De Vary", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "9/2", "age": 4, "form": "2-1-5-21", "rating": 148,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Minella Study", "trainer": "Adam Nicol", "jockey": "TBD",
             "odds": "7/1", "age": 4, "form": "1-1-1", "rating": 142,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Juvenile Hurdle Feb 2026", "days_off": 28},
            {"name": "Maestro Conti", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "15/2", "age": 4, "form": "3-1-1-1", "rating": 135,
             "cheltenham_record": None,
             "last_run": "Won Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Mange Tout", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "8/1", "age": 4, "form": "1-2", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Macho Man", "trainer": "Willie Mullins", "jockey": "Patrick Mullins",
             "odds": "8/1", "age": 4, "form": "1-2-2", "rating": 134,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Jan 2026", "days_off": 42},
        ]
    },
    "day4_race2": {   # County Handicap Hurdle  (Grade 3, 2m1f, speed handicap)
        "entries": [
            {"name": "Murcia", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "6/1", "age": 5, "form": "4-3-4-18", "rating": 154,
             "cheltenham_record": None,
             "last_run": "8th Grade 3 Handicap Jan 2026", "days_off": 42},
            {"name": "Khrisma", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "8/1", "age": 6, "form": "1-2-1-23", "rating": 157,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Karbau", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "10/1", "age": 6, "form": "2-3-0-31", "rating": 157,
             "cheltenham_record": None,
             "last_run": "3rd Grade 2 Handicap Jan 2026", "days_off": 42},
            {"name": "Sinnatra", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "12/1", "age": 6, "form": "1-3-1-22", "rating": 162,
             "cheltenham_record": None,
             "last_run": "Won Betfair Hurdle Feb 2026", "days_off": 28},
            {"name": "Storm Heart", "trainer": "Willie Mullins", "jockey": "Danny Mullins",
             "odds": "14/1", "age": 6, "form": "1-1-4-2/", "rating": 157,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Anzadam", "trainer": "Willie Mullins", "jockey": "Patrick Mullins",
             "odds": "16/1", "age": 6, "form": "1-1-6-11", "rating": 159,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Hello Neighbour", "trainer": "Gavin Cromwell", "jockey": "Danny Mullins",
             "odds": "16/1", "age": 5, "form": "1-3-1-41", "rating": 157,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day4_race3": {   # Albert Bartlett Novices Hurdle  (Grade 1, 3m)
        "entries": [
            {"name": "Doctor Steinberg", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "3/1", "age": 6, "form": "1-1-1-51", "rating": 156,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Thedeviluno", "trainer": "Paul Nolan", "jockey": "Bryan Cooper",
             "odds": "9/2", "age": 7, "form": "1-2-1-22", "rating": 152,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 3m Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "No Drama This End", "trainer": "Paul Nicholls", "jockey": "Harry Cobden",
             "odds": "8/1", "age": 6, "form": "1-1-1-91", "rating": 156,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Spinningayarn", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "10/1", "age": 6, "form": "1-1-3-41", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "I'll Sort That", "trainer": "Declan Queally", "jockey": "TBD",
             "odds": "14/1", "age": 6, "form": "1-1-1-12", "rating": 151,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Kazansky", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "16/1", "age": 6, "form": "1-1-U-2", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Hurdle Feb 2026", "days_off": 28},
        ]
    },
    "day4_race4": {   # Mrs Paddy Power Mares' Chase  (Grade 2, mares only, Day 4 15:20)
        "entries": [
            {"name": "Dinoblue", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "6/4", "age": 9, "form": "1-2-1-11", "rating": 175,
             "cheltenham_record": "Won 2025 Mares Chase",
             "last_run": "Won Grade 1 Mares Chase Jan 2026", "days_off": 42},
            {"name": "Spindleberry", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "4/1", "age": 8, "form": "P-1-1-11", "rating": 167,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Mares Chase Jan 2026", "days_off": 42},
            {"name": "Panic Attack", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "5/1", "age": 10, "form": "5-1-2-21", "rating": 162,
             "cheltenham_record": "Placed 2025 Mares Chase",
             "last_run": "2nd Mares Chase Trial Feb 2026", "days_off": 28},
            {"name": "Only By Night", "trainer": "Gavin Cromwell", "jockey": "Danny Mullins",
             "odds": "8/1", "age": 8, "form": "1-1-7-32", "rating": 160,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Mares Chase Jan 2026", "days_off": 42},
            {"name": "Kala Conti", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "12/1", "age": 6, "form": "2-1-2-3", "rating": 164,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Mares Chase Jan 2026", "days_off": 42},
            {"name": "Diva Luna", "trainer": "Ben Pauling", "jockey": "Jonjo O'Neill Jr",
             "odds": "9/1", "age": 7, "form": "1-2-3-12", "rating": 160,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Mares Chase Jan 2026", "days_off": 42},
        ]
    },
    "day4_race6": {   # St James's Place Hunters' Chase  (Hunter Chase, ~3m2f, Day 4 16:40)
        "entries": [
            {"name": "Wonderwall", "trainer": "S Curling", "jockey": "Rob James",
             "odds": "5/1", "age": 10, "form": "1-2-3-43", "rating": 142,
             "cheltenham_record": "Won 2025 Foxhunter Chase (at 28/1!)",
             "last_run": "3rd Hunter Chase Feb 2026", "days_off": 28},
            {"name": "Its On The Line", "trainer": "Emmet Mullins", "jockey": "Rob James",
             "odds": "6/1", "age": 9, "form": "1-1-2-32", "rating": 146,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
            {"name": "Con's Roc", "trainer": "Terence O'Brien", "jockey": "TBD",
             "odds": "7/1", "age": 9, "form": "3-1-1", "rating": 135,
             "cheltenham_record": None,
             "last_run": "Won Hunters Chase Jan 2026", "days_off": 42},
            {"name": "Panda Boy", "trainer": "Martin Brassil", "jockey": "Keith Donoghue",
             "odds": "8/1", "age": 10, "form": "1-1-8-U3", "rating": 147,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Feb 2026", "days_off": 28},
            {"name": "Chemical Energy", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "16/1", "age": 10, "form": "1-1-1-14", "rating": 139,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
            {"name": "Music Drive", "trainer": "Kelly Morgan", "jockey": "TBD",
             "odds": "12/1", "age": 9, "form": "1-1-P-33", "rating": 132,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
        ]
    },
    "day4_race7": {   # Martin Pipe Handicap Hurdle  (Grade 3, 2m5f, conditional jockeys, Day 4 17:20)
        "entries": [
            {"name": "Roc Dino", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "7/1", "age": 5, "form": "2-2-3-27", "rating": 145,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Hurdle Dec 2025", "days_off": 77},
            {"name": "A Pai De Nom", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "8/1", "age": 6, "form": "1-5-3-31", "rating": 149,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Jan 2026", "days_off": 42},
            {"name": "The Passing Wife", "trainer": "Gavin Cromwell", "jockey": "Danny Mullins",
             "odds": "10/1", "age": 7, "form": "5-5-8-21", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Conditional Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Kel Histoire", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "10/1", "age": 6, "form": "4-3-4-18", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Handicap Jan 2026", "days_off": 42},
            {"name": "He Can't Dance", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "20/1", "age": 6, "form": "1-3-4-22", "rating": 141,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Hurdle Jan 2026", "days_off": 42},
            {"name": "Zanndabad", "trainer": "A J Martin", "jockey": "TBD",
             "odds": "25/1", "age": 7, "form": "1-1-2-62", "rating": 146,
             "cheltenham_record": None,
             "last_run": "Won Conditional Handicap Feb 2026", "days_off": 28},
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
    "galopin des champs",  # ruled out 07 Mar 2026 – late setback, Willie Mullins confirmed
}

# ────────────────────────────────────────────────────────────────────────────
# CORE SCORING + PICK SELECTION
# ────────────────────────────────────────────────────────────────────────────

def score_field(entries, surebet_db, race_name=""):
    """
    Score every horse in a race field using score_horse_2026().
    Augments score by +10 if horse is already confirmed in SureBetBets.
    Returns list of dicts sorted highest score first.
    Pass race_name so race-specific bonuses (same-race winner, Grade 1 etc.) fire correctly.
    """
    results = []
    for horse in entries:
        # Skip any horse officially ruled out of the 2026 festival
        if horse["name"].lower() in RULED_OUT:
            continue
        score, tips, warnings, value_r = score_horse_2026(horse, race_name)
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
    # One jockey cannot ride two horses — remove bonus from lower scorers
    deduplicate_jockeys_in_field(results)
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
            base_entries = all_race_data.get(race_key, [])
            entries = extend_race_entries(race_key, base_entries)
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

            scored = score_field(entries, surebet_db, race_name=race_info["name"])
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
        ("day1_race5", "Champion Hurdle"),
        ("day2_race5", "Queen Mother Chase"),
        ("day2_race7", "Champion Bumper"),
        ("day3_race3", "Close Brothers Mares Hurdle"),
        ("day3_race4", "Stayers Hurdle"),
        ("day3_race5", "Ryanair Chase"),
        ("day4_race3", "Albert Bartlett"),
        ("day4_race5", "Cheltenham Gold Cup"),
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
