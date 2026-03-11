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

import sys, os, json, argparse, re
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
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28,
             "improving": True},
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
             "last_run": "2nd Handicap Chase Kempton Feb 2026", "days_off": 35,
             "finishes_strongly": True},
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
             "odds": "5/1",  "age": 6, "form": "212151",  "rating": 146,  # updated from 9/1 — now Betfair FAV 4/1
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
    "day2_race1": {   # Baring Bingham Hurdle (Turner's) — 22 declared runners, Wed 11 Mar 13:20
        # Non-runners removed: Talk The Talk, Koktail Brut, Road Exile, Kripticjim,
        # Johnny's Jury, Too Bossy For Us, Leader D'Allier, Baron Noir, Jalon D'Oudairies,
        # Doujadou, It's Top
        "entries": [
            {"name": "No Drama This End", "trainer": "Paul Nicholls", "jockey": "Harry Cobden",
             "odds": "11/4", "age": 6, "form": "1-1-1-9-1", "rating": 144,
             "cheltenham_record": "CD winner",
             "last_run": "Won Grade 1 Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Bossman Jack", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "15/2", "age": 5, "form": "1-1-3-1", "rating": 134,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Sober", "trainer": "Willie Mullins", "jockey": "Mr P. W. Mullins",
             "odds": "8/1", "age": 6, "form": "1-1-1-1-5", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Act Of Innocence", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "7/1", "age": 6, "form": "3-4-1-1-2-1", "rating": 138,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "King Rasko Grey", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "7/1", "age": 5, "form": "4-2-1-3", "rating": 146,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Sortudo", "trainer": "Willie Mullins", "jockey": "D. E. Mullins",
             "odds": "12/1", "age": 6, "form": "2-2-7-1-1-2", "rating": 122,
             "cheltenham_record": None,
             "last_run": "3rd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Ballyfad", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "10/1", "age": 5, "form": "1-1-1-2", "rating": 147,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Skylight Hustle", "trainer": "Gordon Elliott", "jockey": "Danny Gilligan",
             "odds": "12/1", "age": 6, "form": "4-2-1-1", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "I'll Sort That", "trainer": "Declan Queally", "jockey": "Mr D. L. Queally",
             "odds": "25/1", "age": 6, "form": "1-2-1-1-1-1", "rating": 142,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Shuttle Diplomacy", "trainer": "Thomas Cooper", "jockey": "D. King",
             "odds": "14/1", "age": 7, "form": "3-5-P-7-2-1", "rating": 133,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Taurus Bay", "trainer": "Ben Pauling", "jockey": "Ben Jones",
             "odds": "25/1", "age": 6, "form": "1-1-2", "rating": 135,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Hurricane Pat", "trainer": "Gary & Josh Moore", "jockey": "Caoilin Quinn",
             "odds": "22/1", "age": 6, "form": "1-3-1-1-2", "rating": 136,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Zeus Power", "trainer": "Joseph Patrick O'Brien", "jockey": "J. J. Slevin",
             "odds": "40/1", "age": 5, "form": "2-3-2-1-1", "rating": 131,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Klimt Madrik", "trainer": "Toby Lawes", "jockey": "K. Brogan",
             "odds": "50/1", "age": 6, "form": "4-1-2", "rating": 138,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Saint Baco", "trainer": "Willie Mullins", "jockey": "S. F. O'Keeffe",
             "odds": "40/1", "age": 6, "form": "3-1-6-4", "rating": 120,
             "cheltenham_record": None,
             "last_run": "6th Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Laurets D'Estruval", "trainer": "Willie Mullins", "jockey": "B. Hayes",
             "odds": "33/1", "age": 5, "form": "2-2-1", "rating": 124,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Soldier Reeves", "trainer": "Dan Skelton", "jockey": "Tristan Durrell",
             "odds": "33/1", "age": 6, "form": "3-1-2-3-2", "rating": 131,
             "cheltenham_record": None,
             "last_run": "3rd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Came From Nowhere", "trainer": "Jeremy Scott", "jockey": "Lorcan Williams",
             "odds": "50/1", "age": 7, "form": "3-3-3-2-1-1", "rating": 132,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Walks In June", "trainer": "Henry de Bromhead", "jockey": "D. J. O'Keeffe",
             "odds": "40/1", "age": 6, "form": "3-5-1-6-1", "rating": 131,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Free Spirit", "trainer": "Willie Mullins", "jockey": "M. P. Walsh",
             "odds": "66/1", "age": 5, "form": "2-1-3", "rating": 115,
             "cheltenham_record": None,
             "last_run": "3rd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Fortune Timmy", "trainer": "Chris Gordon", "jockey": "Freddie Gordon",
             "odds": "66/1", "age": 7, "form": "3-1-3-1-2", "rating": 132,
             "cheltenham_record": None,
             "last_run": "3rd Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Riskaway", "trainer": "Gordon Elliott", "jockey": "Sam Ewing",
             "odds": "66/1", "age": 6, "form": "2-2-1-2-4-2", "rating": 134,
             "cheltenham_record": None,
             "last_run": "2nd Novice Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day2_race2": {   # Broadway Chase (Brown Advisory Novices') — 16 declared runners, Wed 11 Mar 14:00
        # Non-runners: Gold Dancer, Ol Man Dingle
        # Romeo Coolio REINSTATED — confirmed in Brown Advisory per official racecard (not Ryanair)
        "entries": [
            {"name": "Romeo Coolio", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "9/4", "age": 7, "form": "3-2-1-1-1-1", "rating": 157,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Final Demand", "trainer": "Willie Mullins", "jockey": "P. Townend",
             "odds": "5/1", "age": 7, "form": "3-1-1-1-3-1", "rating": 156,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Kaid D'Authie", "trainer": "Willie Mullins", "jockey": "M. P. Walsh",
             "odds": "6/1", "age": 6, "form": "1-1-2-1-p-4", "rating": 158,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Koktail Divin", "trainer": "Henry de Bromhead", "jockey": "D. J. O'Keeffe",
             "odds": "15/2", "age": 8, "form": "1-1-2-2-4-1", "rating": 149,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Wendigo", "trainer": "Jamie Snowden", "jockey": "Gavin Sheehan",
             "odds": "15/2", "age": 7, "form": "1-3-1-2-5-1", "rating": 147,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Feb 2026", "days_off": 28},
            {"name": "Oscars Brother", "trainer": "Connor King", "jockey": "D. King",
             "odds": "10/1", "age": 7, "form": "1-1-1-2-2-f", "rating": 151,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Western Fold", "trainer": "Gordon Elliott", "jockey": "Danny Gilligan",
             "odds": "12/1", "age": 7, "form": "2-3-1-1-1-1", "rating": 157,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "The Big Westerner", "trainer": "Henry de Bromhead", "jockey": "M. P. O'Connor",
             "odds": "12/1", "age": 7, "form": "1-1-2-p-2-1", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Kitzbuhel", "trainer": "Willie Mullins", "jockey": "Harry Cobden",
             "odds": "20/1", "age": 7, "form": "u-1-0-1-3-5", "rating": 153,
             "cheltenham_record": None,
             "last_run": "Unseated Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Argento Boy", "trainer": "Willie Mullins", "jockey": "D. E. Mullins",
             "odds": "33/1", "age": 6, "form": "1-1-f-5-7-0", "rating": 144,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Predators Gold", "trainer": "Willie Mullins", "jockey": "Mr P. W. Mullins",
             "odds": "33/1", "age": 7, "form": "3-1-3-5-2", "rating": 146,
             "cheltenham_record": None,
             "last_run": "3rd Grade 2 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Salver", "trainer": "Gary & Josh Moore", "jockey": "Caoilin Quinn",
             "odds": "30/1", "age": 6, "form": "1-1-3-2-3-1", "rating": 149,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
            {"name": "Now Is The Hour", "trainer": "Gavin Patrick Cromwell", "jockey": "Keith Donoghue",
             "odds": "50/1", "age": 8, "form": "1-4-8-3-1-f-p", "rating": 149,
             "cheltenham_record": "CD winner",
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
            {"name": "Joystick", "trainer": "Willie Mullins", "jockey": "B. Hayes",
             "odds": "150/1", "age": 7, "form": "1-6-4-7-p-2", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
            {"name": "Thomas Mor", "trainer": "Philip Hobbs & Johnson White", "jockey": "Ben Jones",
             "odds": "40/1", "age": 7, "form": "2-2-1-0-4-1", "rating": 147,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Novice Chase Jan 2026", "days_off": 42},
            {"name": "Rushmount", "trainer": "Jonathan Sweeney", "jockey": "S. F. O'Keeffe",
             "odds": "100/1", "age": 8, "form": "1-1-5-5-4-0", "rating": 143,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
        ]
    },
    "day2_race3": {   # Cup Handicap Hurdle  (Grade 3, 2m5f — 26 declared runners, Wed 11 Mar 14:40)
        "entries": [
            {"name": "Kopeck De Mee", "trainer": "Willie Mullins", "jockey": "M. P. Walsh",
             "odds": "8/1", "age": 7, "form": "11/102-F", "rating": 141,
             "cheltenham_record": "2nd Martin Pipe 2024",
             "last_run": "Fell Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Storm Heart", "trainer": "Willie Mullins", "jockey": "D. E. Mullins",
             "odds": "8/1", "age": 6, "form": "25/42-11", "rating": 151,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "The Yellow Clay", "trainer": "Gordon Elliott", "jockey": "M. J. Kenneally",
             "odds": "15/2", "age": 7, "form": "112-F25", "rating": 155,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Kateira", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "6/1", "age": 7, "form": "2-14389", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Won Hurdle Jan 2026", "days_off": 42},
            {"name": "Iberico Lord", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "9/1", "age": 7, "form": "40-0991", "rating": 144,
             "cheltenham_record": "CD winner",
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Puturhandstogether", "trainer": "Joseph Patrick O'Brien", "jockey": "J. J. Slevin",
             "odds": "10/1", "age": 9, "form": "13-6026", "rating": 142,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Dec 2025", "days_off": 56},
            {"name": "Forty Coats", "trainer": "Henry de Bromhead", "jockey": "D. J. O'Keeffe",
             "odds": "25/1", "age": 5, "form": "2224-73", "rating": 141,
             "cheltenham_record": None,
             "last_run": "8th Hurdle Feb 2026", "days_off": 28},
            {"name": "Jingko Blue", "trainer": "Nicky Henderson", "jockey": "James Bowen",
             "odds": "9/2", "age": 7, "form": "11U-72", "rating": 144,  # SP 9/2 (was 9/1 morning); stripped old P (4+ runs ago)
             "cheltenham_record": "WON BetMGM Cup Hurdle 2026",  # WON today 11 Mar 2026 at 9/2 SP
             "last_run": "WON BetMGM Cup Handicap Hurdle Mar 2026", "days_off": 28},
            {"name": "Bunting", "trainer": "Willie Mullins", "jockey": "Harry Cobden",
             "odds": "11/1", "age": 9, "form": "2P60-49", "rating": 149,
             "cheltenham_record": None,
             "last_run": "7th Hurdle Feb 2026", "days_off": 28},
            {"name": "Farren Glory", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "25/1", "age": 9, "form": "1233-33", "rating": 148,
             "cheltenham_record": None,
             "last_run": "3rd Hurdle Dec 2025", "days_off": 84},
            {"name": "Guard Duty", "trainer": "Emma Lavelle", "jockey": "Ben Jones",
             "odds": "14/1", "age": 9, "form": "119-231", "rating": 148,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Hurdle Jan 2026", "days_off": 56},
            {"name": "Lucky Place", "trainer": "Nicky Henderson", "jockey": "Brian Hughes",
             "odds": "16/1", "age": 7, "form": "174-323", "rating": 151,
             "cheltenham_record": "CD winner",
             "last_run": "3rd Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Ballyadam", "trainer": "Henry de Bromhead", "jockey": "Patrick Michael O'Brien",
             "odds": "16/1", "age": 11, "form": "327/13-6", "rating": 152,
             "cheltenham_record": "Won Champion Novices' Hurdle 2021",
             "last_run": "6th Hurdle Nov 2025", "days_off": 112},
            {"name": "Beckett Rock", "trainer": "Henry de Bromhead", "jockey": "M. P. O'Connor",
             "odds": "25/1", "age": 9, "form": "6-00542", "rating": 140,
             "cheltenham_record": None,
             "last_run": "3rd Hurdle Jan 2026", "days_off": 56},
            {"name": "Buddy One", "trainer": "Paul John Gilligan", "jockey": "Jack Gilligan",
             "odds": "25/1", "age": 6, "form": "57-66P4", "rating": 136,
             "cheltenham_record": None,
             "last_run": "5th Hurdle Feb 2026", "days_off": 28},
            {"name": "Colonel Mustard", "trainer": "Mrs Lorna Fowler", "jockey": "J. P. Shinnick",
             "odds": "TBD", "age": 6, "form": "4-51184", "rating": 136,
             "cheltenham_record": None,
             "last_run": "6th Hurdle Feb 2026", "days_off": 28},
            {"name": "Chart Topper", "trainer": "Willie Mullins", "jockey": "B. Hayes",
             "odds": "20/1", "age": 7, "form": "22-63PF", "rating": 139,
             "cheltenham_record": None,
             "last_run": "5th Hurdle Jan 2026", "days_off": 56},
            {"name": "Sony Bill", "trainer": "Willie Mullins", "jockey": "S. F. O'Keeffe",
             "odds": "50/1", "age": 8, "form": "2350-F8", "rating": 140,
             "cheltenham_record": None,
             "last_run": "Win Hurdle Dec 2025", "days_off": 84},
            {"name": "Give It To Me Oj", "trainer": "Gary & Josh Moore", "jockey": "Caoilin Quinn",
             "odds": "33/1", "age": 5, "form": "411-156", "rating": 140,
             "cheltenham_record": None,
             "last_run": "6th Hurdle Feb 2026", "days_off": 28},
            {"name": "Franciscan Rock", "trainer": "M. F. Morris", "jockey": "J. H. Williamson",
             "odds": "TBD", "age": 11, "form": "833495", "rating": 148,
             "cheltenham_record": None,
             "last_run": "4th Hurdle Dec 2025", "days_off": 84},
            {"name": "Rambo T", "trainer": "Olly Murphy", "jockey": "Sean Bowen",
             "odds": "66/1", "age": 8, "form": "1-31980", "rating": 139,
             "cheltenham_record": None,
             "last_run": "4th Hurdle Dec 2025", "days_off": 84},
            {"name": "Hms Seahorse", "trainer": "Paul Nolan", "jockey": "E. Staples",
             "odds": "33/1", "age": 11, "form": "00-12FU", "rating": 140,
             "cheltenham_record": None,
             "last_run": "Won Hurdle Dec 2025", "days_off": 84},
            {"name": "Dargiannini", "trainer": "Harry Derham", "jockey": "Paul O'Brien",
             "odds": "66/1", "age": 5, "form": "5425-1P", "rating": 135,
             "cheltenham_record": None,
             "last_run": "9th Hurdle Feb 2026", "days_off": 28},
            {"name": "Minella Rescue", "trainer": "Gary Hanmer", "jockey": "Gavin Sheehan",
             "odds": "66/1", "age": 9, "form": "20-1284", "rating": 139,
             "cheltenham_record": None,
             "last_run": "5th Hurdle Jan 2026", "days_off": 56},
            {"name": "I Started A Joke", "trainer": "TBD", "jockey": "TBD",
             "odds": "TBD", "age": 6, "form": "TBD", "rating": 130,
             "cheltenham_record": None,
             "last_run": "TBD", "days_off": 42},
            {"name": "Intense Approach", "trainer": "TBD", "jockey": "TBD",
             "odds": "TBD", "age": 6, "form": "TBD", "rating": 128,
             "cheltenham_record": None,
             "last_run": "TBD", "days_off": 42},
        ]
    },
    "day2_race4": {   # Glenfarclas Chase (XC) — 14 declared runners, Wed 11 Mar 15:20
        # Non-runners: Chemical Energy, Anibale Fly
        # New: The Goffer, Fakir D'Oudairies, Latenightpass, Famous Bridge, Horantzau Dairy, Velvet Elvis, Minella Crooner
        "entries": [
            {"name": "Favori De Champdou", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "5/2", "age": 11, "form": "0-05F11", "rating": 157,
             "cheltenham_record": "Won 2024 Glenfarclas Cross Country Chase",
             "last_run": "Won Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Stumptown", "trainer": "Gavin Patrick Cromwell", "jockey": "Keith Donoghue",
             "odds": "3/1", "age": 9, "form": "1111P-1", "rating": 162,
             "cheltenham_record": "Won 2025 Glenfarclas Cross Country Chase",
             "last_run": "Won Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Desertmore House", "trainer": "Martin Brassil", "jockey": "R. A. Doyle",
             "odds": "7/2", "age": 11, "form": "00P-21P", "rating": 140,
             "cheltenham_record": "Placed Cross Country 2024",
             "last_run": "Won Amateur Cross Country Feb 2026", "days_off": 28},
            {"name": "Final Orders", "trainer": "Gavin Patrick Cromwell", "jockey": "C. Stone-Walsh(3)",
             "odds": "7/1", "age": 8, "form": "3P6315", "rating": 147,
             "cheltenham_record": "CD winner",
             "last_run": "5th Cross Country Chase Jan 2026", "days_off": 42},  # WON at 7/1 SP (3lb claimer booked)
            {"name": "Vanillier", "trainer": "Gavin Patrick Cromwell", "jockey": "Sean Flanagan",
             "odds": "8/1", "age": 10, "form": "30-U631", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Won Cross Country Chase Feb 2026", "days_off": 28},
            {"name": "The Goffer", "trainer": "Gordon Elliott", "jockey": "J. H. Williamson",
             "odds": "14/1", "age": 8, "form": "3-50272", "rating": 138,
             "cheltenham_record": None,
             "last_run": "3rd Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Pied Piper", "trainer": "Gordon Elliott", "jockey": "Sam Ewing",
             "odds": "30/1", "age": 8, "form": "32569F", "rating": 145,
             "cheltenham_record": None,
             "last_run": "Fell Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Fakir D'Oudairies", "trainer": "Enda Bolger", "jockey": "D. J. O'Keeffe",
             "odds": "16/1", "age": 11, "form": "50/740-4", "rating": 143,
             "cheltenham_record": None,
             "last_run": "4th Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Conflated", "trainer": "Gordon Elliott", "jockey": "Danny Gilligan",
             "odds": "20/1", "age": 11, "form": "708P-43", "rating": 145,
             "cheltenham_record": None,
             "last_run": "3rd Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Latenightpass", "trainer": "Tom Ellis", "jockey": "Miss Gina Andrews",
             "odds": "50/1", "age": 9, "form": "U20-779", "rating": 130,
             "cheltenham_record": None,
             "last_run": "7th Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Famous Bridge", "trainer": "Nicky Richards", "jockey": "Sean Quinlan",
             "odds": "50/1", "age": 10, "form": "D6P-770", "rating": 132,
             "cheltenham_record": None,
             "last_run": "7th Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Horantzau Dairy", "trainer": "Stuart Edmunds", "jockey": "Charlie Hammond",
             "odds": "80/1", "age": 9, "form": "990-28P", "rating": 128,
             "cheltenham_record": None,
             "last_run": "9th Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Velvet Elvis", "trainer": "John McConnell", "jockey": "Gavin Sheehan",
             "odds": "66/1", "age": 10, "form": "028-P7P", "rating": 130,
             "cheltenham_record": None,
             "last_run": "7th Cross Country Chase Jan 2026", "days_off": 42},
            {"name": "Minella Crooner", "trainer": "Sarah Humphrey", "jockey": "James Best",
             "odds": "100/1", "age": 11, "form": "P65P-8P", "rating": 125,
             "cheltenham_record": None,
             "last_run": "8th Cross Country Chase Jan 2026", "days_off": 42},
        ]
    },
    "day2_race5": {   # Queen Mother Champion Chase (Grade 1, 2m — 10 declared runners, Wed 11 Mar 16:00)
        # Non-runners: Jonbon, Solness, Only By Night
        "entries": [
            {"name": "Majborough", "trainer": "Willie Mullins", "jockey": "M. P. Walsh",
             "odds": "10/11", "age": 9, "form": "13-1231", "rating": 168,  # updated 10/11 -> 6/4 -> 10/11 live
             "cheltenham_record": "C D",
             "last_run": "Won Dublin Chase Grade 1 Feb 2026", "days_off": 35},
            {"name": "Il Etait Temps", "trainer": "Willie Mullins", "jockey": "P. Townend",
             "odds": "5/2", "age": 8, "form": "1/11-11F", "rating": 170,  # updated 9/2 -> 7/1 -> 5/2 live (big market move)
             "cheltenham_record": "D, BF",
             "last_run": "Won Grade 1 2m Chase Jan 2026", "days_off": 42},
            {"name": "L'Eau du Sud", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "13/2", "age": 7, "form": "1143-13", "rating": 163,  # updated 4/1 -> 6/1 -> 13/2 live
             "cheltenham_record": "C D",
             "last_run": "Won Shloer Chase Cheltenham Nov 2025", "days_off": 100},
            {"name": "Irish Panther", "trainer": "Eddie & Patrick Harty", "jockey": "Kieren Buckley",
             "odds": "14/1", "age": 7, "form": "30-3112", "rating": 155,
             "cheltenham_record": "D",
             "last_run": "Won Grade 1 Novice Chase Feb 2026", "days_off": 28},
            {"name": "Quilixios", "trainer": "Henry de Bromhead", "jockey": "D. J. O'Keeffe",
             "odds": "14/1", "age": 9, "form": "85/124F-", "rating": 155,
             "cheltenham_record": "C D",
             "last_run": "Fell Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Found A Fifty", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "28/1", "age": 8, "form": "411434", "rating": 145,
             "cheltenham_record": "D, BF",
             "last_run": "4th Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Saint Segal", "trainer": "Mrs Jane Williams", "jockey": "Ciaran Gethings",
             "odds": "50/1", "age": 9, "form": "1-12122", "rating": 142,
             "cheltenham_record": "D",
             "last_run": "2nd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Captain Guinness", "trainer": "Henry de Bromhead", "jockey": "Jordan Colin Gainford",
             "odds": "40/1", "age": 11, "form": "63-2P63", "rating": 161,
             "cheltenham_record": "C D",
             "last_run": "3rd Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Libberty Hunter", "trainer": "Mrs C. Williams", "jockey": "Sean Bowen",
             "odds": "80/1", "age": 9, "form": "12F-U43", "rating": 148,
             "cheltenham_record": "C D",
             "last_run": "3rd Chase Jan 2026", "days_off": 42},
            {"name": "Brookie", "trainer": "Anthony Honeyball", "jockey": "Sam Twiston-Davies",
             "odds": "100/1", "age": 8, "form": "312-43P", "rating": 140,
             "cheltenham_record": "D",
             "last_run": "Pulled up Chase Dec 2025", "days_off": 77},
        ]
    },
    "day2_race6": {   # Grand Annual Handicap Chase (Grade 3, 2m — 22 declared runners, Wed 11 Mar 16:40)
        # Fully updated declared field with corrected jockeys/trainers
        "entries": [
            {"name": "Be Aware", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "9/2", "age": 8, "form": "88-1222", "rating": 147,
             "cheltenham_record": "D, BF",
             "last_run": "2nd Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Jazzy Matty", "trainer": "Cian Michael Collins", "jockey": "Danny Gilligan",
             "odds": "6/1", "age": 9, "form": "16-P056", "rating": 143,
             "cheltenham_record": "Won 2025 Grand Annual Chase (CD)",
             "last_run": "Won Grand Annual Chase Mar 2025", "days_off": 364},
            {"name": "Vanderpoel", "trainer": "Ben Pauling", "jockey": "Ben Jones",
             "odds": "15/2", "age": 7, "form": "1P-3211", "rating": 141,
             "cheltenham_record": "D",
             "last_run": "Won Handicap Chase Dec 2025", "days_off": 84},
            {"name": "Release The Beast", "trainer": "Paul Nolan", "jockey": "Sean Flanagan",
             "odds": "10/1", "age": 11, "form": "3166-22", "rating": 145,
             "cheltenham_record": "BF",
             "last_run": "2nd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Inthepocket", "trainer": "Henry de Bromhead", "jockey": "M. P. Walsh",
             "odds": "17/2", "age": 7, "form": "13-F555", "rating": 146,
             "cheltenham_record": "D",
             "last_run": "5th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Relieved Of Duties", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "14/1", "age": 10, "form": "F51254", "rating": 136,
             "cheltenham_record": "D",
             "last_run": "4th Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Jour D'Evasion", "trainer": "Henry Daly", "jockey": "Sam Twiston-Davies",
             "odds": "11/1", "age": 9, "form": "15-5111", "rating": 137,
             "cheltenham_record": "D",
             "last_run": "Won Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Break My Soul", "trainer": "Ian Patrick Donoghue", "jockey": "Sam Ewing",
             "odds": "12/1", "age": 7, "form": "4-41472", "rating": 136,
             "cheltenham_record": "D",
             "last_run": "4th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Addragoole", "trainer": "Gavin Patrick Cromwell", "jockey": "Keith Donoghue",
             "odds": "18/1", "age": 8, "form": "321413", "rating": 138,
             "cheltenham_record": "D",
             "last_run": "Won Handicap Chase Dec 2025", "days_off": 84},
            {"name": "Ballysax Hank", "trainer": "Gavin Patrick Cromwell", "jockey": "James Bowen",
             "odds": "10/1", "age": 8, "form": "231286", "rating": 145,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Jasko Des Dames", "trainer": "Henry de Bromhead", "jockey": "D. J. O'Keeffe",
             "odds": "16/1", "age": 8, "form": "55-0220", "rating": 132,
             "cheltenham_record": None,
             "last_run": "0th Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Rubaud", "trainer": "Paul Nicholls", "jockey": "Harry Cobden",
             "odds": "18/1", "age": 9, "form": "5-51132", "rating": 148,
             "cheltenham_record": "D",
             "last_run": "2nd Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Western Diego", "trainer": "W. P. Mullins", "jockey": "B. Hayes",
             "odds": "20/1", "age": 8, "form": "25-8314", "rating": 141,
             "cheltenham_record": "D",
             "last_run": "4th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Personal Ambition", "trainer": "Ben Pauling", "jockey": "Kielan Woods",
             "odds": "16/1", "age": 8, "form": "3P-4P51", "rating": 139,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Jan 2026", "days_off": 56},
            {"name": "Touch Me Not", "trainer": "Gordon Elliott", "jockey": "James Smith(5)",
             "odds": "25/1", "age": 9, "form": "54-4232", "rating": 155,
             "cheltenham_record": "D",
             "last_run": "2nd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Special Cadeau", "trainer": "Henry de Bromhead", "jockey": "M. P. O'Connor",
             "odds": "20/1", "age": 10, "form": "5-25236", "rating": 141,
             "cheltenham_record": "D",
             "last_run": "6th Handicap Chase Jan 2026", "days_off": 42},
            {"name": "Calico", "trainer": "Dan Skelton", "jockey": "Tristan Durrell",
             "odds": "20/1", "age": 9, "form": "432-114", "rating": 153,
             "cheltenham_record": "CD",
             "last_run": "4th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Boothill", "trainer": "Harry Fry", "jockey": "Bryan Carver",
             "odds": "33/1", "age": 10, "form": "2F4-P53", "rating": 139,
             "cheltenham_record": "D",
             "last_run": "3rd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Martator", "trainer": "Venetia Williams", "jockey": "Charlie Deutsch",
             "odds": "33/1", "age": 9, "form": "08-529U", "rating": 133,
             "cheltenham_record": None,
             "last_run": "Unseated Rider Chase Jan 2026", "days_off": 42},
            {"name": "The Other Mozzie", "trainer": "L J Morgan", "jockey": "Brian Hughes",
             "odds": "33/1", "age": 8, "form": "71-0770", "rating": 136,
             "cheltenham_record": "D",
             "last_run": "0th Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Golden Joy", "trainer": "TBD", "jockey": "TBD",
             "odds": "TBD", "age": None, "form": "", "rating": 130,
             "cheltenham_record": None,
             "last_run": "TBD", "days_off": 42},
            {"name": "Ryans Rocket", "trainer": "TBD", "jockey": "TBD",
             "odds": "TBD", "age": None, "form": "", "rating": 130,
             "cheltenham_record": None,
             "last_run": "TBD", "days_off": 42},
        ]
    },
    "day3_race1": {   # Dawn Run Mares' Novices' Hurdle  (Grade 2, 2m1f — 22 runners, Thu 12 Mar 13:20)
        # UPDATED 11/03/2026 from live racecard. E/W: 1/5 odds, 4 places.
        # KEY MOVE: Oldschool Outlaw 12/1 -> 7/2 with M. P. Walsh (Elliott's #1 jockey, huge stable confidence)
        # Selma De Vary: non-runner (not on racecard)
        "entries": [
            {"name": "Bambino Fever", "trainer": "Willie Mullins", "jockey": "P. Townend",
             "odds": "1/1", "age": 5, "form": "111-121", "rating": 148,
             "cheltenham_record": "C D",
             "last_run": "2nd Grade 1 Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Oldschool Outlaw", "trainer": "Gordon Elliott", "jockey": "M. P. Walsh",
             "odds": "7/2", "age": 6, "form": "27-111", "rating": 138,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Carrigmoornaspruce", "trainer": "Declan Queally", "jockey": "James Bowen",
             "odds": "10/1", "age": 5, "form": "32-1122", "rating": 132,
             "cheltenham_record": "D",
             "last_run": "2nd Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Echoing Silence", "trainer": "Henry de Bromhead", "jockey": "D. J. O'Keeffe",
             "odds": "12/1", "age": 6, "form": "51-11", "rating": 130,
             "cheltenham_record": "D",
             "last_run": "Won Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Kingston Queen", "trainer": "David Pipe", "jockey": "Jack Tudor",
             "odds": "25/1", "age": 6, "form": "113-131", "rating": 129,
             "cheltenham_record": "D",
             "last_run": "Won Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "La Conquiere", "trainer": "Jamie Snowden", "jockey": "Gavin Sheehan",
             "odds": "20/1", "age": 7, "form": "22-112", "rating": 133,
             "cheltenham_record": "D, BF",
             "last_run": "2nd Grade 1 Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Charme De Faust", "trainer": "Willie Mullins", "jockey": "D. E. Mullins",
             "odds": "33/1", "age": 4, "form": "21", "rating": 115,
             "cheltenham_record": None,
             "last_run": "Won INH Flat Feb 2026", "days_off": 28},
            {"name": "Future Prospect", "trainer": "Willie Mullins", "jockey": "Harry Cobden",
             "odds": "20/1", "age": 6, "form": "153-61", "rating": 118,
             "cheltenham_record": "D",
             "last_run": "Won Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Place De La Nation", "trainer": "Willie Mullins", "jockey": "Danny Gilligan",
             "odds": "20/1", "age": 5, "form": "325-112", "rating": 135,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Mille Et Une Vies", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "20/1", "age": 4, "form": "32-2", "rating": 135,
             "cheltenham_record": None,
             "last_run": "2nd Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Full Of Life", "trainer": "Henry de Bromhead", "jockey": "M. P. O'Connor",
             "odds": "33/1", "age": 7, "form": "3P-1421", "rating": 130,
             "cheltenham_record": "D",
             "last_run": "3rd Grade 2 Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Amen Kate", "trainer": "Thomas Cooper", "jockey": "J. W. Kennedy",
             "odds": "33/1", "age": 8, "form": "4-431U1", "rating": 125,
             "cheltenham_record": None,
             "last_run": "Won Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Blue Velvet", "trainer": "Willie Mullins", "jockey": "S. F. O'Keeffe",
             "odds": "50/1", "age": 6, "form": "173-21", "rating": 118,
             "cheltenham_record": None,
             "last_run": "Won Mares Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "White Noise", "trainer": "Kim Bailey & Mat Nicholls", "jockey": "Tom Bellamy",
             "odds": "33/1", "age": 6, "form": "3-1112", "rating": 128,
             "cheltenham_record": "D",
             "last_run": "Won Mares Novice Hurdle Nov 2025", "days_off": 56},
            {"name": "Manganese", "trainer": "Max Comley", "jockey": "David Bass",
             "odds": "28/1", "age": 4, "form": "1111", "rating": 125,
             "cheltenham_record": "D",
             "last_run": "Won Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Diamond Du Berlais", "trainer": "Willie Mullins", "jockey": "Mr P. W. Mullins",
             "odds": "40/1", "age": 5, "form": "54-0381", "rating": 120,
             "cheltenham_record": None,
             "last_run": "Won Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Jackie Hobbs", "trainer": "Harry Derham", "jockey": "Paul O'Brien",
             "odds": "33/1", "age": 6, "form": "119-141", "rating": 125,
             "cheltenham_record": "D",
             "last_run": "Won Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "St Irene", "trainer": "Nick Scholfield", "jockey": "Jack Quinlan",
             "odds": "40/1", "age": 6, "form": "630-211", "rating": 123,
             "cheltenham_record": "D",
             "last_run": "Won Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Chosen Comrade", "trainer": "Peter Fahey", "jockey": "Sam Ewing",
             "odds": "66/1", "age": 5, "form": "114", "rating": 115,
             "cheltenham_record": "D",
             "last_run": "Won Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Louve Dirlande", "trainer": "Paul Nolan", "jockey": "C. Stone-Walsh(3)",
             "odds": "66/1", "age": 5, "form": "101", "rating": 112,
             "cheltenham_record": "D",
             "last_run": "Won Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Al Fonce", "trainer": "N. George & A. Zetterholm", "jockey": "Jordan Colin Gainford",
             "odds": "66/1", "age": 7, "form": "2113", "rating": 120,
             "cheltenham_record": "D",
             "last_run": "2nd Mares Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Scavengers Reign", "trainer": "James Owen", "jockey": "Sam Twiston-Davies",
             "odds": "66/1", "age": 6, "form": "3-2U313", "rating": 110,
             "cheltenham_record": "BF",
             "last_run": "3rd Mares Novice Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day2_race7": {   # Weatherbys Champion Bumper (Grade 1, 2m1f — 22 declared runners, Wed 11 Mar 17:20)
        "entries": [
            {"name": "Love Sign d'Aunou", "trainer": "W. P. Mullins", "jockey": "Mr P. W. Mullins",
             "odds": "9/2", "age": 5, "form": "1", "rating": 135,
             "cheltenham_record": None,
             "last_run": "Won Bumper Jan 2026", "days_off": 42},
            {"name": "Keep Him Company", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "9/1", "age": 6, "form": "11", "rating": 132,  # updated 7/1 -> 9/1 live
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Bumper Jan 2026", "days_off": 42},
            {"name": "Quiryn", "trainer": "W. P. Mullins", "jockey": "P. Townend",
             "odds": "8/1", "age": 4, "form": "1", "rating": 128,  # updated 7/1 -> 8/1 live
             "cheltenham_record": None,
             "last_run": "Won INH Flat Feb 2026", "days_off": 28},
            {"name": "The Mourne Rambler", "trainer": "Noel Meade", "jockey": "C. T. Keane",
             "odds": "8/1", "age": 5, "form": "1", "rating": 128,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Bumper Leopardstown Feb 2026", "days_off": 28},
            {"name": "Bass Hunter", "trainer": "Chris Gordon", "jockey": "Freddie Gordon",
             "odds": "11/1", "age": 5, "form": "11", "rating": 125,
             "cheltenham_record": None,
             "last_run": "Won Listed Bumper Ascot Jan 2026", "days_off": 42},
            {"name": "The Irish Avatar", "trainer": "W. P. Mullins", "jockey": "Harry Cobden",
             "odds": "13/2", "age": 5, "form": "1", "rating": 130,  # odds confirmed 13/2
             "cheltenham_record": None,
             "last_run": "Won INH Flat Feb 2026", "days_off": 28},
            {"name": "Its Only A Game", "trainer": "Martin Brassil", "jockey": "Mr J. L. Gleeson",
             "odds": "16/1", "age": 5, "form": "214", "rating": 120,
             "cheltenham_record": None,
             "last_run": "4th INH Flat Feb 2026", "days_off": 28},
            {"name": "Our Trigger", "trainer": "W. P. Mullins", "jockey": "D. E. Mullins",
             "odds": "11/1", "age": 5, "form": "1", "rating": 122,
             "cheltenham_record": None,
             "last_run": "Won INH Flat Feb 2026", "days_off": 28},
            {"name": "Mets Ta Ceinture", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "14/1", "age": 5, "form": "121", "rating": 122,
             "cheltenham_record": None,
             "last_run": "Won Bumper Feb 2026", "days_off": 28},
            {"name": "Broadway Ted", "trainer": "Gordon Elliott", "jockey": "Sean Bowen",
             "odds": "16/1", "age": 5, "form": "11", "rating": 125,  # updated 14/1 -> 16/1 live
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Bumper Jan 2026", "days_off": 42},
            {"name": "Charismatic Kid", "trainer": "Gordon Elliott", "jockey": "Sam Ewing",
             "odds": "20/1", "age": 5, "form": "13", "rating": 115,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Bumper Jan 2026", "days_off": 42},
            {"name": "Moonverrin", "trainer": "Martin Hassett", "jockey": "Mr Finian Maguire",
             "odds": "25/1", "age": 5, "form": "211", "rating": 120,
             "cheltenham_record": None,
             "last_run": "Won Bumper Feb 2026", "days_off": 28},
            {"name": "The Wager", "trainer": "W. P. Mullins", "jockey": "Miss J. Townend",
             "odds": "20/1", "age": 5, "form": "2-1", "rating": 118,
             "cheltenham_record": None,
             "last_run": "Won Bumper Jan 2026", "days_off": 42},
            {"name": "Boycetown", "trainer": "Gavin Patrick Cromwell", "jockey": "Keith Donoghue",
             "odds": "25/1", "age": 5, "form": "21", "rating": 116,
             "cheltenham_record": None,
             "last_run": "Won INH Flat Feb 2026", "days_off": 28},
            {"name": "With Nolimit", "trainer": "Gordon Elliott", "jockey": "Mr H. C. Swan",
             "odds": "25/1", "age": 5, "form": "412", "rating": 126,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Bumper Feb 2026", "days_off": 28},
            {"name": "Diamant Dore", "trainer": "Adrian Keatley", "jockey": "Brian Hughes",
             "odds": "30/1", "age": 5, "form": "1", "rating": 114,
             "cheltenham_record": None,
             "last_run": "Won INH Flat Feb 2026", "days_off": 28},
            {"name": "Wildes Legacy", "trainer": "Jamie Snowden", "jockey": "Gavin Sheehan",
             "odds": "TBD", "age": 5, "form": "11", "rating": 122,
             "cheltenham_record": None,
             "last_run": "Won Bumper Feb 2026", "days_off": 28},
            {"name": "Of Land And Sea", "trainer": "Paul Hennessy", "jockey": "Richard Condon",
             "odds": "25/1", "age": 5, "form": "451", "rating": 112,
             "cheltenham_record": None,
             "last_run": "Won Bumper Feb 2026", "days_off": 28},
            {"name": "The Skecher", "trainer": "Dan Skelton", "jockey": "Tristan Durrell",
             "odds": "33/1", "age": 5, "form": "1", "rating": 110,
             "cheltenham_record": None,
             "last_run": "Won Bumper Feb 2026", "days_off": 28},
            {"name": "Chicker", "trainer": "Fergal O'Brien", "jockey": "Jonathan Burke",
             "odds": "50/1", "age": 5, "form": "116", "rating": 110,
             "cheltenham_record": None,
             "last_run": "6th Bumper Feb 2026", "days_off": 28},
            {"name": "Tally Ho Back", "trainer": "Nigel Twiston-Davies", "jockey": "Sam Twiston-Davies",
             "odds": "50/1", "age": 5, "form": "426", "rating": 108,
             "cheltenham_record": None,
             "last_run": "6th Bumper Feb 2026", "days_off": 28},
            {"name": "Vango Can Go", "trainer": "Dan Skelton", "jockey": "Charlie Todd",
             "odds": "66/1", "age": 5, "form": "13", "rating": 106,
             "cheltenham_record": None,
             "last_run": "3rd Bumper Feb 2026", "days_off": 28},
        ]
    },
    "day3_race2": {   # Golden Miller Novices' Limited Handicap Chase  (Grade 2, 2m4f — 19 runners, Thu 12 Mar 14:00)
        # UPDATED 11/03/2026 from live racecard. E/W: 1/5 odds, 5 PLACES (paying 5 not 4).
        # NR: Old Cowboy (Gary & Josh Moore)
        # KEY MOVES: Meetmebythesea 14/1->5/1 (Ben Jones, stable confidence), Regents Stroll 8/1->5/1 (Cobden conf)
        #            Jordans Cross 14/1->13/2 (STD confirmed), Gold Dancer 6/4->25/1 (huge drift, 7lb claimer booked)
        # HANDICAP — claimer bonuses DO NOT fire
        "entries": [
            {"name": "Regents Stroll", "trainer": "Paul Nicholls", "jockey": "Harry Cobden",
             "odds": "5/1", "age": 6, "form": "212-312", "rating": 145,
             "cheltenham_record": None,
             "last_run": "2nd Novice Chase Feb 2026", "days_off": 28},
            {"name": "Sixmilebridge", "trainer": "Fergal O'Brien", "jockey": "Kielan Woods",
             "odds": "6/1", "age": 9, "form": "179-111", "rating": 150,
             "cheltenham_record": "CD winner",
             "last_run": "Won Novice Chase Feb 2026", "days_off": 28},
            {"name": "Jordans Cross", "trainer": "Anthony Honeyball", "jockey": "Sam Twiston-Davies",
             "odds": "13/2", "age": 8, "form": "12-1F11", "rating": 140,
             "cheltenham_record": "CD winner",
             "last_run": "Won Novice Chase Feb 2026 (CD)", "days_off": 28},
            {"name": "Meetmebythesea", "trainer": "Ben Pauling", "jockey": "Ben Jones",
             "odds": "5/1", "age": 8, "form": "113-116", "rating": 139,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Jan 2026", "days_off": 42},
            {"name": "Stencil", "trainer": "N. George & A. Zetterholm", "jockey": "Jonathan Burke",
             "odds": "13/2", "age": 8, "form": "620-521", "rating": 139,
             "cheltenham_record": None,
             "last_run": "Won Novice Chase Feb 2026", "days_off": 28},
            {"name": "Slade Steel", "trainer": "Henry de Bromhead", "jockey": "D. J. O'Keeffe",
             "odds": "9/1", "age": 7, "form": "322-2B2", "rating": 146,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Wingmen", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "11/1", "age": 9, "form": "206-232", "rating": 142,
             "cheltenham_record": None,
             "last_run": "2nd Chase Jan 2026", "days_off": 42},
            {"name": "Kiss Will", "trainer": "Willie Mullins", "jockey": "J. J. Slevin",
             "odds": "14/1", "age": 7, "form": "171-322", "rating": 141,
             "cheltenham_record": None,
             "last_run": "3rd Chase Feb 2026", "days_off": 28},
            {"name": "The Bluesman", "trainer": "Olly Murphy", "jockey": "Sean Bowen",
             "odds": "14/1", "age": 8, "form": "1/13-121", "rating": 134,
             "cheltenham_record": "CD winner",
             "last_run": "Won Novice Chase Feb 2026 (CD)", "days_off": 28},
            {"name": "Kdeux Saint Fray", "trainer": "Anthony Honeyball", "jockey": "Rex Dingle",
             "odds": "16/1", "age": 8, "form": "2-F1243", "rating": 131,
             "cheltenham_record": "CD winner",
             "last_run": "2nd Chase Jan 2026", "days_off": 42},
            {"name": "Ol Man Dingle", "trainer": "Eoin Griffin", "jockey": "R. A. Doyle",
             "odds": "20/1", "age": 8, "form": "145-115", "rating": 145,
             "cheltenham_record": "CD winner",
             "last_run": "Won Novice Chase Jan 2026 (CD)", "days_off": 42},
            {"name": "Ben Solo", "trainer": "Rebecca Curtis", "jockey": "Brian Hughes",
             "odds": "25/1", "age": 7, "form": "28-512U", "rating": 132,
             "cheltenham_record": None,
             "last_run": "2nd Chase Feb 2026", "days_off": 28},
            {"name": "Gold Dancer", "trainer": "Willie Mullins", "jockey": "A. McGuinness(7)",
             "odds": "25/1", "age": 7, "form": "111224", "rating": 152,
             "cheltenham_record": None,
             "last_run": "4th Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "King Alexander", "trainer": "Willie Mullins", "jockey": "D. E. Mullins",
             "odds": "20/1", "age": 7, "form": "903-231", "rating": 144,
             "cheltenham_record": None,
             "last_run": "3rd Chase Feb 2026", "days_off": 28},
            {"name": "Western Knight", "trainer": "Joe Tizzard", "jockey": "Brendan Powell",
             "odds": "40/1", "age": 7, "form": "U8-4112", "rating": 136,
             "cheltenham_record": None,
             "last_run": "2nd Chase Feb 2026", "days_off": 28},
            {"name": "Intense Approach", "trainer": "John McConnell", "jockey": "Alex Harvey(3)",
             "odds": "50/1", "age": 8, "form": "P8-15U5", "rating": 137,
             "cheltenham_record": None,
             "last_run": "Won Chase Feb 2026", "days_off": 28},
            {"name": "Wheres My Jet", "trainer": "Willie Mullins", "jockey": "S. F. O'Keeffe",
             "odds": "50/1", "age": 7, "form": "U47F06", "rating": 125,
             "cheltenham_record": None,
             "last_run": "Fell Chase Jan 2026", "days_off": 42},
            {"name": "Dr Eggman", "trainer": "Willie Mullins", "jockey": "J. P. Shinnick(3)",
             "odds": "40/1", "age": 6, "form": "129-833", "rating": 128,
             "cheltenham_record": None,
             "last_run": "3rd Chase Feb 2026", "days_off": 28},
            {"name": "Moon Rocket", "trainer": "Kim Bailey & Mat Nicholls", "jockey": "Tom Bellamy",
             "odds": "20/1", "age": 8, "form": "22P-126", "rating": 140,
             "cheltenham_record": None,
             "last_run": "6th Chase Jan 2026", "days_off": 42},
        ]
    },
    "day3_race3": {   # David Nicholson / Close Brothers Mares' Hurdle  (Grade 1, 2m4f — 7 runners, Thu 12 Mar 14:40)
        # UPDATED 11/03/2026 from live racecard. E/W: 1/4 odds, 2 PLACES ONLY.
        # Wodhooh dominant favourite — model + market agrees. 8/11 with Kennedy/Elliott.
        "entries": [
            {"name": "Wodhooh", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "8/11", "age": 7, "form": "1/112-11", "rating": 162,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Mares Hurdle Jan 2026", "days_off": 42},
            {"name": "Jade De Grugy", "trainer": "Willie Mullins", "jockey": "P. Townend",
             "odds": "11/4", "age": 7, "form": "12-1321", "rating": 152,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Mares Hurdle Jan 2026", "days_off": 42},
            {"name": "Take No Chances", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "8/1", "age": 7, "form": "35-6233", "rating": 147,
             "cheltenham_record": None,
             "last_run": "3rd Grade 2 Mares Hurdle Feb 2026", "days_off": 28},
            {"name": "Feet Of A Dancer", "trainer": "Paul Nolan", "jockey": "S. F. O'Keeffe",
             "odds": "9/1", "age": 7, "form": "343-121", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Mares Hurdle Feb 2026", "days_off": 28},
            {"name": "Dream On Baby", "trainer": "Emmet Mullins", "jockey": "Donagh Meyler",
             "odds": "28/1", "age": 8, "form": "P22132", "rating": 138,
             "cheltenham_record": None,
             "last_run": "2nd Mares Hurdle Jan 2026", "days_off": 42},
            {"name": "Jetara", "trainer": "Mrs J. Harrington", "jockey": "Sam Ewing",
             "odds": "28/1", "age": 7, "form": "43-3373", "rating": 135,
             "cheltenham_record": None,
             "last_run": "3rd Mares Hurdle Jan 2026", "days_off": 42},
            {"name": "Sunset Marquesa", "trainer": "Joe Tizzard", "jockey": "Brendan Powell",
             "odds": "33/1", "age": 7, "form": "1F-3143", "rating": 130,
             "cheltenham_record": None,
             "last_run": "3rd Mares Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day3_race6": {   # Pertemps Network Final Handicap Hurdle  (Grade 3, 3m — 26 runners, Thu 12 Mar 16:40)
        # UPDATED 11/03/2026 from live racecard. E/W: 1/5 odds, 6 PLACES (paying 6 not 4).
        # Impose Toi confirmed STAYERS' HURDLE — not in this field.
        # KEY MOVE: Supremely West 14/1 -> 16/5 favourite — massive gamble, Harry Skelton, OR 148.
        # Staffordshire Knot drifted 8/1 -> 14/1. Cest Different 12/1 -> 15/2 (movers).
        # Claimers in field: Yeah Man (Stone-Walsh 3lb), Duke Silver (Horgan 5lb),
        #   Gowel Road (McCain-Mitchell 5lb), Onewaywest (England 7lb) — all HANDICAP so NO bonus fires.
        "entries": [
            {"name": "Supremely West", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "16/5", "age": 8, "form": "63-3546", "rating": 148,
             "cheltenham_record": "D",
             "last_run": "Won Pertemps Qualifier Feb 2026", "days_off": 28},
            {"name": "Cest Different", "trainer": "Sam Thomas", "jockey": "Dylan Johnston",
             "odds": "15/2", "age": 9, "form": "4711-11", "rating": 131,
             "cheltenham_record": "D",
             "last_run": "Won Pertemps Qual Feb 2026 (CD)", "days_off": 28},
            {"name": "Bold Endeavour", "trainer": "Nicky Henderson", "jockey": "James Bowen",
             "odds": "10/1", "age": 8, "form": "0/07PP-3", "rating": 130,
             "cheltenham_record": None,
             "last_run": "3rd Pertemps Qualifier Feb 2026", "days_off": 28},
            {"name": "Electric Mason", "trainer": "Chris Gordon", "jockey": "Freddie Gordon",
             "odds": "9/1", "age": 8, "form": "5107-21", "rating": 139,
             "cheltenham_record": "D",
             "last_run": "Won Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Ace Of Spades", "trainer": "Dan Skelton", "jockey": "Kielan Woods",
             "odds": "9/1", "age": 7, "form": "42-1421", "rating": 139,
             "cheltenham_record": "C",
             "last_run": "Won Pertemps Qualifier Feb 2026", "days_off": 28},
            {"name": "Minella Emperor", "trainer": "Emmet Mullins", "jockey": "Mr M. J. O'Neill(7)",
             "odds": "12/1", "age": 7, "form": "1P4322", "rating": 146,
             "cheltenham_record": None,
             "last_run": "Won Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Lavida Adiva", "trainer": "Ruth Jefferson", "jockey": "Brian Hughes",
             "odds": "14/1", "age": 8, "form": "2-34143", "rating": 135,
             "cheltenham_record": "D",
             "last_run": "3rd Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Kikijo", "trainer": "Philip Hobbs & Johnson White", "jockey": "Callum Pritchard(3)",
             "odds": "12/1", "age": 8, "form": "412-411", "rating": 134,
             "cheltenham_record": "CD winner",
             "last_run": "Won Pertemps Qualifier Feb 2026 (CD)", "days_off": 28},
            {"name": "Absolutely Doyen", "trainer": "Paul Nicholls", "jockey": "Harry Cobden",
             "odds": "12/1", "age": 8, "form": "2-11111", "rating": 135,
             "cheltenham_record": "D",
             "last_run": "Won Pertemps Qualifier Feb 2026", "days_off": 28},
            {"name": "Melbourne Shamrock", "trainer": "Emmet Mullins", "jockey": "Donagh Meyler",
             "odds": "20/1", "age": 8, "form": "3P-4241", "rating": 132,
             "cheltenham_record": None,
             "last_run": "2nd Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Letos", "trainer": "Anthony Mullins", "jockey": "D. E. Mullins",
             "odds": "20/1", "age": 7, "form": "42-2120", "rating": 135,
             "cheltenham_record": None,
             "last_run": "Won Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Staffordshire Knot", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "14/1", "age": 7, "form": "9-31121", "rating": 152,
             "cheltenham_record": "D",
             "last_run": "Won Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Yeah Man", "trainer": "Gavin Patrick Cromwell", "jockey": "C. Stone-Walsh(3)",
             "odds": "18/1", "age": 8, "form": "9622P6", "rating": 128,
             "cheltenham_record": None,
             "last_run": "6th Hurdle Jan 2026", "days_off": 42},
            {"name": "Minella Sixo", "trainer": "Gordon Elliott", "jockey": "Sam Ewing",
             "odds": "20/1", "age": 8, "form": "F0-9762", "rating": 130,
             "cheltenham_record": None,
             "last_run": "2nd Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Champagne Chic", "trainer": "Jeremy Scott", "jockey": "Lorcan Williams",
             "odds": "16/1", "age": 7, "form": "40-6211", "rating": 131,
             "cheltenham_record": "D",
             "last_run": "Won Pertemps Qualifier Feb 2026", "days_off": 28},
            {"name": "Gowel Road", "trainer": "Nigel & Willy Twiston-Davies", "jockey": "Toby McCain-Mitchell(5)",
             "odds": "25/1", "age": 10, "form": "037442", "rating": 148,
             "cheltenham_record": "CD winner",
             "last_run": "4th Hurdle Jan 2026", "days_off": 42},
            {"name": "Classic King", "trainer": "Emma Lavelle", "jockey": "Ben Jones",
             "odds": "25/1", "age": 8, "form": "132-464", "rating": 132,
             "cheltenham_record": None,
             "last_run": "4th Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Duke Silver", "trainer": "Joseph Patrick O'Brien", "jockey": "H. J. Horgan(5)",
             "odds": "20/1", "age": 6, "form": "241017", "rating": 133,
             "cheltenham_record": "D",
             "last_run": "2nd Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Onewaywest", "trainer": "Ben Pauling", "jockey": "Elliott England(7)",
             "odds": "25/1", "age": 7, "form": "52-11F2", "rating": 130,
             "cheltenham_record": None,
             "last_run": "2nd Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Red Dirt Road", "trainer": "Jonjo & A.J. O'Neill", "jockey": "Jonjo O'Neill Jr.",
             "odds": "33/1", "age": 8, "form": "511P-P4", "rating": 128,
             "cheltenham_record": None,
             "last_run": "Pulled up Pertemps Qualifier Jan 2026", "days_off": 42},
            {"name": "Ikarak", "trainer": "Olly Murphy", "jockey": "Sean Bowen",
             "odds": "14/1", "age": 7, "form": "152-131", "rating": 133,
             "cheltenham_record": "D",
             "last_run": "Won Pertemps Qualifier Feb 2026", "days_off": 28},
            {"name": "Idy Wood", "trainer": "Jamie Snowden", "jockey": "Gavin Sheehan",
             "odds": "40/1", "age": 7, "form": "41-1410", "rating": 130,
             "cheltenham_record": None,
             "last_run": "4th Hurdle Jan 2026", "days_off": 42},
            {"name": "Idem", "trainer": "Lucinda Russell & Michael Scudamore", "jockey": "Patrick Wadge",
             "odds": "50/1", "age": 8, "form": "40-2582", "rating": 125,
             "cheltenham_record": None,
             "last_run": "5th Hurdle Jan 2026", "days_off": 42},
            {"name": "Ike Sport", "trainer": "Neil Mulholland", "jockey": "Conor O'Farrell",
             "odds": "50/1", "age": 8, "form": "205266", "rating": 122,
             "cheltenham_record": None,
             "last_run": "6th Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day3_race4": {   # Stayers' Hurdle  (Grade 1, 3m — 11 runners, Thu 12 Mar 15:20)
        # UPDATED 11/03/2026 from live racecard. E/W: 1/5 odds, 3 PLACES.
        # Impose Toi dual declared with Pertemps — almost certainly runs here (OR 159, much better horse).
        # KEY MOVE: Teahupoo 11/4 fav, Kabral Du Mathan 16/5 — very tight at top.
        # Ma Shantou dark horse — third STRING but won NH Chase and hurdle/chase form excellent
        "entries": [
            {"name": "Teahupoo", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "11/4", "age": 10, "form": "122-111", "rating": 170,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Stayers Hurdle Jan 2026", "days_off": 42},
            {"name": "Kabral Du Mathan", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "16/5", "age": 8, "form": "1222-11", "rating": 165,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Hurdle Feb 2026", "days_off": 28},
            {"name": "Ma Shantou", "trainer": "Emma Lavelle", "jockey": "Harry Cobden",
             "odds": "6/1", "age": 9, "form": "37-1011", "rating": 157,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Hurdle Feb 2026", "days_off": 28},
            {"name": "Ballyburn", "trainer": "Willie Mullins", "jockey": "P. Townend",
             "odds": "17/2", "age": 8, "form": "215-223", "rating": 163,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Hurdle Jan 2026", "days_off": 42},
            {"name": "Bob Olinger", "trainer": "Henry de Bromhead", "jockey": "D. J. O'Keeffe",
             "odds": "7/1", "age": 10, "form": "22/221-2", "rating": 160,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Hurdle Jan 2026", "days_off": 42},
            {"name": "Honesty Policy", "trainer": "Gordon Elliott", "jockey": "M. P. Walsh",
             "odds": "13/2", "age": 7, "form": "2111-23", "rating": 158,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Hurdle Jan 2026", "days_off": 42},
            {"name": "Impose Toi", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "11/1", "age": 7, "form": "4-21112", "rating": 159,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Stayers Trial Jan 2026", "days_off": 42},
            {"name": "Hewick", "trainer": "John Joseph Hanlon", "jockey": "P. Hanlon",
             "odds": "35/1", "age": 12, "form": "18-7145", "rating": 155,
             "cheltenham_record": None,
             "last_run": "5th Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Home By The Lee", "trainer": "Joseph Patrick O'Brien", "jockey": "J. J. Slevin",
             "odds": "33/1", "age": 8, "form": "1UP-641", "rating": 148,
             "cheltenham_record": None,
             "last_run": "4th Hurdle Feb 2026", "days_off": 28},
            {"name": "Doddiethegreat", "trainer": "Nicky Henderson", "jockey": "James Bowen",
             "odds": "66/1", "age": 8, "form": "1-23453", "rating": 145,
             "cheltenham_record": None,
             "last_run": "3rd Hurdle Jan 2026", "days_off": 42},
            {"name": "Gwennie May Boy", "trainer": "Christian Williams", "jockey": "Charlie Todd",
             "odds": "110/1", "age": 9, "form": "5196-7P", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Pulled up Hurdle Jan 2026", "days_off": 42},
        ]
    },
    "day3_race5": {   # Festival Trophy Chase (fka Ryanair Chase)  (Grade 1, 2m4f — 9 runners, Thu 12 Mar 16:00)
        # UPDATED 11/03/2026 from live racecard.
        # KEY: Walsh on Fact To File (not Townend!). Townend opts for Impaire Et Passe — rare split.
        # Il Etait Temps NOT in field — won QMCC Day 2. Confirmed 9 runners.
        "entries": [
            {"name": "Fact To File", "trainer": "Willie Mullins", "jockey": "M. P. Walsh",
             "odds": "8/13", "age": 8, "form": "31-4261", "rating": 174,
             "cheltenham_record": "Won 2024 Ryanair Chase; Won 2025 Ryanair Chase",
             "last_run": "Won Grade 1 Chase Trial Jan 2026", "days_off": 42},
            {"name": "Banbridge", "trainer": "Joseph Patrick O'Brien", "jockey": "Sean Bowen",
             "odds": "13/2", "age": 10, "form": "U17-442", "rating": 167,
             "cheltenham_record": "CD winner",
             "last_run": "2nd Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Impaire Et Passe", "trainer": "Willie Mullins", "jockey": "P. Townend",
             "odds": "13/2", "age": 8, "form": "1131-B1", "rating": 160,
             "cheltenham_record": "CD winner",
             "last_run": "Won Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Jonbon", "trainer": "Nicky Henderson", "jockey": "Nico de Boinville",
             "odds": "7/1", "age": 10, "form": "12-2211", "rating": 166,
             "cheltenham_record": "CD winner",
             "last_run": "Won Grade 1 Chase Dec 2025", "days_off": 70},
            {"name": "Heart Wood", "trainer": "Henry de Bromhead", "jockey": "D. J. O'Keeffe",
             "odds": "9/1", "age": 8, "form": "42P-141", "rating": 160,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Chase Feb 2026", "days_off": 28},
            {"name": "JPR One", "trainer": "Joe Tizzard", "jockey": "Brendan Powell",
             "odds": "40/1", "age": 9, "form": "05-3321", "rating": 160,
             "cheltenham_record": "D",
             "last_run": "Won Grade 1 Chase Feb 2026", "days_off": 28},
            {"name": "Matata", "trainer": "Nigel & Willy Twiston-Davies", "jockey": "J. J. Slevin",
             "odds": "40/1", "age": 8, "form": "3-73315", "rating": 155,
             "cheltenham_record": "CD winner",
             "last_run": "3rd Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Master Chewy", "trainer": "Nigel & Willy Twiston-Davies", "jockey": "Sam Twiston-Davies",
             "odds": "150/1", "age": 9, "form": "6-24725", "rating": 148,
             "cheltenham_record": None,
             "last_run": "5th Chase Jan 2026", "days_off": 42},
            {"name": "Croke Park", "trainer": "Gordon Elliott", "jockey": "J. W. Kennedy",
             "odds": "20/1", "age": 8, "form": "27-3330", "rating": 150,
             "cheltenham_record": None,
             "last_run": "3rd Chase Jan 2026", "days_off": 42},
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
    "day3_race7": {   # Kim Muir Challenge Cup Amateur Chase  (Class 2, 3m2f — 24 runners, Thu 12 Mar 17:20)
        # UPDATED 11/03/2026 from live racecard. E/W: 1/5 odds, 5 PLACES. All amateur jockeys.
        # HANDICAP — claimer bonuses do not fire.
        # Jeriko Du Reponet (7/2 fav) — Henderson, Mr D. O'Connor up.
        "entries": [
            {"name": "Jeriko Du Reponet", "trainer": "Nicky Henderson", "jockey": "Mr D. O'Connor",
             "odds": "7/2", "age": 9, "form": "32-1225", "rating": 145,
             "cheltenham_record": None,
             "last_run": "5th Grade 1 Chase Jan 2026", "days_off": 42},
            {"name": "Waterford Whispers", "trainer": "Henry de Bromhead", "jockey": "Mr Alan O'Sullivan(3)",
             "odds": "14/1", "age": 9, "form": "27-4363", "rating": 137,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Kim Roque", "trainer": "Joseph Patrick O'Brien", "jockey": "Mr J. L. Gleeson",
             "odds": "8/1", "age": 8, "form": "B42245", "rating": 140,
             "cheltenham_record": None,
             "last_run": "5th Chase Jan 2026", "days_off": 42},
            {"name": "Herakles Westwood", "trainer": "Warren Greatrex", "jockey": "Mr Finian Maguire",
             "odds": "9/1", "age": 9, "form": "37-5241", "rating": 137,
             "cheltenham_record": "C",
             "last_run": "Won Handicap Chase Feb 2026 (C)", "days_off": 28},
            {"name": "Daily Present", "trainer": "Paul Nolan", "jockey": "Mr B. T. Stone(5)",
             "odds": "20/1", "age": 9, "form": "331P-0P", "rating": 135,
             "cheltenham_record": "CD winner",
             "last_run": "Pulled up Chase Jan 2026", "days_off": 42},
            {"name": "Prends Garde A Toi", "trainer": "Gordon Elliott", "jockey": "Mr B. O'Neill",
             "odds": "12/1", "age": 9, "form": "2P14F4", "rating": 137,
             "cheltenham_record": None,
             "last_run": "4th Chase Jan 2026", "days_off": 42},
            {"name": "Road To Home", "trainer": "Willie Mullins", "jockey": "Mr P. W. Mullins",
             "odds": "14/1", "age": 9, "form": "F-3533P", "rating": 136,
             "cheltenham_record": None,
             "last_run": "Pulled up Chase Jan 2026", "days_off": 42},
            {"name": "The Enabler", "trainer": "Gordon Elliott", "jockey": "Mr R. James",
             "odds": "20/1", "age": 8, "form": "06-3143", "rating": 140,
             "cheltenham_record": None,
             "last_run": "3rd Chase Jan 2026", "days_off": 42},
            {"name": "Sandor Clegane", "trainer": "Paul Nolan", "jockey": "Mr J. W. Hendrick(3)",
             "odds": "25/1", "age": 8, "form": "08-7760", "rating": 130,
             "cheltenham_record": None,
             "last_run": "0 Chase Jan 2026", "days_off": 42},
            {"name": "Il Ridoto", "trainer": "Paul Nicholls", "jockey": "Miss Olive Nicholls",
             "odds": "20/1", "age": 8, "form": "07-2872", "rating": 132,
             "cheltenham_record": "C",
             "last_run": "2nd Chase Jan 2026", "days_off": 42},
            {"name": "Weveallbeencaught", "trainer": "Eric McNamara", "jockey": "Mr J. C. Barry",
             "odds": "12/1", "age": 9, "form": "544-420", "rating": 137,
             "cheltenham_record": "C",
             "last_run": "0 Handicap Chase Feb 2026", "days_off": 28},
            {"name": "Excello", "trainer": "Nicky Henderson", "jockey": "Mr Henry Main(5)",
             "odds": "20/1", "age": 8, "form": "740-30F", "rating": 134,
             "cheltenham_record": None,
             "last_run": "3rd Chase Jan 2026", "days_off": 42},
            {"name": "Gericault Roque", "trainer": "David Pipe", "jockey": "Mr B. Lawless(7)",
             "odds": "25/1", "age": 8, "form": "53//30-82", "rating": 130,
             "cheltenham_record": None,
             "last_run": "2nd Chase Jan 2026", "days_off": 42},
            {"name": "Ask Brewster", "trainer": "Mrs C. Williams", "jockey": "Mr S. Cotter(7)",
             "odds": "16/1", "age": 9, "form": "P511-15", "rating": 138,
             "cheltenham_record": "C",
             "last_run": "Won Chase Feb 2026 (C)", "days_off": 28},
            {"name": "Kings Threshold", "trainer": "Emma Lavelle", "jockey": "Mr H. C. Swan",
             "odds": "14/1", "age": 8, "form": "11P-041", "rating": 137,
             "cheltenham_record": "D",
             "last_run": "Won Handicap Chase Dec 2025", "days_off": 77},
            {"name": "Glengouly", "trainer": "Faye Bramley", "jockey": "Mr Dara McGill",
             "odds": "33/1", "age": 8, "form": "0341PP", "rating": 128,
             "cheltenham_record": "C",
             "last_run": "Pulled up Chase Jan 2026", "days_off": 42},
            {"name": "Insurrection", "trainer": "Paul Nicholls", "jockey": "Miss Gina Andrews",
             "odds": "14/1", "age": 8, "form": "3188-38", "rating": 138,
             "cheltenham_record": "BF",
             "last_run": "Won Handicap Chase Dec 2025", "days_off": 77},
            {"name": "Olympic Man", "trainer": "John McConnell", "jockey": "Mr D. Doyle(3)",
             "odds": "25/1", "age": 8, "form": "17P-P6P", "rating": 130,
             "cheltenham_record": None,
             "last_run": "Pulled up Chase Jan 2026", "days_off": 42},
            {"name": "Monbeg Genius", "trainer": "Jonjo & A.J. O'Neill", "jockey": "Mr J. L. Scallan(5)",
             "odds": "40/1", "age": 9, "form": "1P6-P57", "rating": 141,
             "cheltenham_record": None,
             "last_run": "5th Chase Jan 2026", "days_off": 42},
            {"name": "Uncle Bert", "trainer": "Nigel & Willy Twiston-Davies", "jockey": "Miss Amber Jackson-Fennell(5)",
             "odds": "25/1", "age": 8, "form": "159-1F7", "rating": 135,
             "cheltenham_record": None,
             "last_run": "1st Chase Jan 2026", "days_off": 42},
            {"name": "No Time To Wait", "trainer": "John McConnell", "jockey": "Mr Josh Halford(3)",
             "odds": "25/1", "age": 8, "form": "9-22U04", "rating": 132,
             "cheltenham_record": None,
             "last_run": "4th Chase Jan 2026", "days_off": 42},
            {"name": "Lord Accord", "trainer": "Neil Mulholland", "jockey": "Mr N. McParlan",
             "odds": "33/1", "age": 8, "form": "062412", "rating": 128,
             "cheltenham_record": "CD winner",
             "last_run": "2nd Chase Jan 2026", "days_off": 42},
            {"name": "Cave Court", "trainer": "Noel C. Kelly", "jockey": "Mr O. McGill",
             "odds": "33/1", "age": 9, "form": "14-7208", "rating": 126,
             "cheltenham_record": None,
             "last_run": "2nd Chase Jan 2026", "days_off": 42},
            {"name": "Hung Jury", "trainer": "Martin Keighley", "jockey": "Mr James King",
             "odds": "33/1", "age": 9, "form": "4812P0", "rating": 125,
             "cheltenham_record": "C",
             "last_run": "Pulled up Chase Jan 2026", "days_off": 42},
        ]
    },
    "day4_race1": {   # JCB Triumph Hurdle  (Grade 1, 2m179yds — 25 runners, Fri 13 Mar 13:20)
        # UPDATED 09/03/2026 from official Friday racecard. Mange Tout NOT in racecard — removed.
        "entries": [
            {"name": "Proactif", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "7/2", "age": 4, "form": "1-1", "rating": 139,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Minella Study", "trainer": "Adam Nicol", "jockey": "Ryan Mania",
             "odds": "7/1", "age": 4, "form": "1-1-1", "rating": 139,
             "cheltenham_record": "CD winner",
             "last_run": "Won Grade 2 Juvenile Hurdle Feb 2026 (CD)", "days_off": 28},
            {"name": "Selma De Vary", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "9/2", "age": 4, "form": "2-1-5-2", "rating": 136,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Juvenile Hurdle Jan 2026 (dual dec Mares Novices)", "days_off": 42},
            {"name": "Maestro Conti", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "7/1", "age": 4, "form": "3-1-1-1", "rating": 135,
             "cheltenham_record": "CD winner",
             "last_run": "Won Juvenile Hurdle Jan 2026 (CD)", "days_off": 42},
            {"name": "Highland Crystal", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "9/1", "age": 4, "form": "1-1-1", "rating": 133,
             "cheltenham_record": "CD winner",
             "last_run": "Won Grade 2 Juvenile Hurdle Feb 2026 (CD, dual dec Mares Novices)", "days_off": 28},
            {"name": "Macho Man", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "8/1", "age": 4, "form": "1-2", "rating": 130,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Jan 2026", "days_off": 42},
            {"name": "One Horse Town", "trainer": "Harry Derham", "jockey": "Paul O'Brien",
             "odds": "10/1", "age": 4, "form": "2-2-1-1", "rating": 132,
             "cheltenham_record": "CD winner",
             "last_run": "Won Juvenile Hurdle Feb 2026 (CD)", "days_off": 28},
            {"name": "Madness D'elle", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "10/1", "age": 4, "form": "1-2-7", "rating": 127,
             "cheltenham_record": None,
             "last_run": "Won Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Manganese", "trainer": "Max Comley", "jockey": "David Bass",
             "odds": "14/1", "age": 4, "form": "1-1-7", "rating": 125,
             "cheltenham_record": None,
             "last_run": "Won Juvenile Hurdle Feb 2026 (dual dec Mares Novices)", "days_off": 28},
            {"name": "Indian River", "trainer": "Adrian Paul Keatley", "jockey": "TBD",
             "odds": "16/1", "age": 4, "form": "1-1", "rating": 122,
             "cheltenham_record": None,
             "last_run": "Won Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Barbizon", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "16/1", "age": 4, "form": "1-1-4-6", "rating": 128,
             "cheltenham_record": None,
             "last_run": "Won Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Lord Byron", "trainer": "Faye Bramley", "jockey": "TBD",
             "odds": "25/1", "age": 4, "form": "3-4-1-3", "rating": 123,
             "cheltenham_record": None,
             "last_run": "3rd Juvenile Hurdle Jan 2026", "days_off": 42},
            {"name": "Fantasy World", "trainer": "Nicky Henderson", "jockey": "TBD",
             "odds": "25/1", "age": 4, "form": "1-3-4", "rating": 120,
             "cheltenham_record": None,
             "last_run": "Won Juvenile Hurdle Feb 2026", "days_off": 28},
        ]
    },
    "day4_race2": {   # William Hill County Handicap Hurdle  (Grade 3, 2m179yds — 50 runners, Fri 13 Mar 14:00)
        # UPDATED 09/03/2026 from official Friday racecard. Key OR corrections: Sinnatra 133, Khrisma 128.
        # Storm Heart and Anzadam NOT in official County Hurdle racecard — removed.
        "entries": [
            {"name": "Ndaawi", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "8/1", "age": 6, "form": "3-4-6-1-2", "rating": 156,
             "cheltenham_record": None,
             "last_run": "3rd Grade 3 Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Absurde", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "8/1", "age": 9, "form": "3-2-3-1", "rating": 155,
             "cheltenham_record": "CD winner",
             "last_run": "3rd Grade 3 Handicap Hurdle Feb 2026 (CD)", "days_off": 28},
            {"name": "Bowensonfire", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "10/1", "age": 6, "form": "1-3-2-1", "rating": 153,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Karbau", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "10/1", "age": 6, "form": "2-3-0-3-1", "rating": 150,
             "cheltenham_record": None,
             "last_run": "3rd Grade 2 Handicap Jan 2026", "days_off": 42},
            {"name": "Murcia", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "12/1", "age": 5, "form": "4-3-4-1-8", "rating": 142,
             "cheltenham_record": None,
             "last_run": "8th Grade 3 Handicap Jan 2026", "days_off": 42},
            {"name": "Hello Neighbour", "trainer": "Gavin Cromwell", "jockey": "TBD",
             "odds": "16/1", "age": 5, "form": "1-3-0-5-7", "rating": 148,
             "cheltenham_record": None,
             "last_run": "7th Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Workahead", "trainer": "Henry De Bromhead", "jockey": "TBD",
             "odds": "16/1", "age": 7, "form": "4-2-0-3", "rating": 148,
             "cheltenham_record": None,
             "last_run": "4th Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Sinnatra", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "12/1", "age": 6, "form": "1-3-1-3-2", "rating": 133,
             "cheltenham_record": None,
             "last_run": "Won Betfair Hurdle Feb 2026", "days_off": 28},
            {"name": "Khrisma", "trainer": "Nicky Henderson", "jockey": "TBD",
             "odds": "14/1", "age": 6, "form": "1-2-1-2-3", "rating": 128,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Jump Allen", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "20/1", "age": 6, "form": "1-2-1-3-1", "rating": 133,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Jubilee Alpha", "trainer": "Paul Nicholls", "jockey": "Harry Cobden",
             "odds": "20/1", "age": 7, "form": "1-1-2-3-4", "rating": 139,
             "cheltenham_record": None,
             "last_run": "4th Handicap Hurdle Feb 2026", "days_off": 28},
        ]
    },
    "day4_race3": {   # Albert Bartlett Novices' Hurdle  (Grade 1, 3m — 32 runners, Fri 13 Mar 15:20)
        # UPDATED 09/03/2026: ratings/trainers corrected from official racecard; additional runners added
        "entries": [
            {"name": "Doctor Steinberg", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "9/4", "age": 6, "form": "1-1-1-51", "rating": 147,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "No Drama This End", "trainer": "Paul Nicholls", "jockey": "Harry Cobden",
             "odds": "6/1", "age": 6, "form": "1-1-1-91", "rating": 144,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Thedeviluno", "trainer": "Paul Nolan", "jockey": "Bryan Cooper",
             "odds": "5/1", "age": 7, "form": "1-2-1-22", "rating": 141,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 3m Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "Kazansky", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "7/1", "age": 6, "form": "1-1-U-2", "rating": 139,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Hurdle Feb 2026", "days_off": 28},
            {"name": "The Passing Wife", "trainer": "Gavin Cromwell", "jockey": "TBD",
             "odds": "8/1", "age": 6, "form": "1-1-2-1", "rating": 139,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Novice Hurdle 3m Feb 2026", "days_off": 28},
            {"name": "Kripticjim", "trainer": "Joe Tizzard", "jockey": "Brendan Powell",
             "odds": "10/1", "age": 5, "form": "1-1-1-2", "rating": 135,
             "cheltenham_record": "CD winner",
             "last_run": "2nd Grade 2 Novice Hurdle 3m Feb 2026 (CD)", "days_off": 28},
            {"name": "Spinningayarn", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "12/1", "age": 6, "form": "1-1-3-41", "rating": 135,
             "cheltenham_record": None,
             "last_run": "Won Grade 2 Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Mondoui'boy", "trainer": "Ben Pauling", "jockey": "Ben Jones",
             "odds": "14/1", "age": 6, "form": "1-2-1", "rating": 134,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle 3m Feb 2026", "days_off": 28},
            {"name": "Moneygarrow", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "16/1", "age": 5, "form": "1-1-2", "rating": 133,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle 3m Feb 2026", "days_off": 28},
            {"name": "I'll Sort That", "trainer": "Declan Queally", "jockey": "TBD",
             "odds": "20/1", "age": 6, "form": "1-1-1-12", "rating": 131,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle Jan 2026", "days_off": 42},
            {"name": "Park Princess", "trainer": "Henry De Bromhead", "jockey": "TBD",
             "odds": "16/1", "age": 5, "form": "1-2-1-1", "rating": 132,
             "cheltenham_record": None,
             "last_run": "Won Novice Hurdle 3m Jan 2026", "days_off": 42},
        ]
    },
    "day4_race4": {   # Mrs Paddy Power Mares' Chase  (Grade 2, 2m4f — 12 runners, Fri 13 Mar 14:40)
        # UPDATED 09/03/2026: Kala Conti NOT in official racecard — removed. ORs corrected.
        "entries": [
            {"name": "Dinoblue", "trainer": "Willie Mullins", "jockey": "Paul Townend",
             "odds": "6/4", "age": 9, "form": "1-2-1-1-1", "rating": 159,
             "cheltenham_record": "Won 2025 Mares Chase (CD)",
             "last_run": "Won Grade 1 Mares Chase Jan 2026", "days_off": 42},
            {"name": "Spindleberry", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "4/1", "age": 8, "form": "p-1-1-1-1", "rating": 153,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Mares Chase Jan 2026", "days_off": 42},
            {"name": "Panic Attack", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "5/1", "age": 10, "form": "5-1-2-2-1", "rating": 147,
             "cheltenham_record": "CD winner",
             "last_run": "Won Grade 1 Mares Chase Feb 2026 (CD)", "days_off": 28},
            {"name": "Telepathique", "trainer": "Mrs L Wadham", "jockey": "TBD",
             "odds": "8/1", "age": 8, "form": "1-1-2-4-2", "rating": 147,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Mares Chase Jan 2026", "days_off": 42},
            {"name": "Only By Night", "trainer": "Gavin Cromwell", "jockey": "TBD",
             "odds": "8/1", "age": 8, "form": "7-3-2-1-1", "rating": 148,
             "cheltenham_record": None,
             "last_run": "Won Grade 1 Mares Chase Jan 2026", "days_off": 42},
            {"name": "Diva Luna", "trainer": "Ben Pauling", "jockey": "Ben Jones",
             "odds": "10/1", "age": 7, "form": "1-2-3-1-2", "rating": 143,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Mares Chase Feb 2026", "days_off": 28},
            {"name": "July Flower", "trainer": "Henry De Bromhead", "jockey": "TBD",
             "odds": "10/1", "age": 7, "form": "3-1-1-5", "rating": 143,
             "cheltenham_record": None,
             "last_run": "3rd Grade 1 Mares Chase Jan 2026", "days_off": 42},
            {"name": "The Big Westerner", "trainer": "Henry De Bromhead", "jockey": "TBD",
             "odds": "12/1", "age": 7, "form": "1-p-2-1-2", "rating": 143,
             "cheltenham_record": None,
             "last_run": "2nd Grade 1 Mares Chase Feb 2026", "days_off": 28},
            {"name": "Jade De Grugy", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "14/1", "age": 7, "form": "1-2-1-3-2", "rating": 150,
             "cheltenham_record": None,
             "last_run": "Won Mares Chase Jan 2026", "days_off": 42},
            {"name": "Shakeyatailfeather", "trainer": "Dan Skelton", "jockey": "Tristan Durrell",
             "odds": "33/1", "age": 7, "form": "1-5-1-8-5", "rating": 125,
             "cheltenham_record": None,
             "last_run": "5th Grade 1 Mares Chase Jan 2026", "days_off": 42},
            {"name": "All The Glory", "trainer": "Jonjo O'Neill", "jockey": "TBD",
             "odds": "50/1", "age": 9, "form": "6-3-4-3-2", "rating": 127,
             "cheltenham_record": None,
             "last_run": "6th Mares Chase Jan 2026", "days_off": 42},
            {"name": "Piper Park", "trainer": "Tom Lacey", "jockey": "Stan Sheppard",
             "odds": "100/1", "age": 7, "form": "2-3-6-2", "rating": 130,
             "cheltenham_record": None,
             "last_run": "2nd Mares Chase Jan 2026", "days_off": 42},
        ]
    },
    "day4_race6": {   # Princess Royal Challenge Cup Open Hunters' Chase  (3m2f — 27 runners, Fri 13 Mar 16:40)
        # UPDATED 09/03/2026: ORs corrected from official Friday racecard; Barton Snow/Stattler/What A Glance/Solitary Man added
        "entries": [
            {"name": "Barton Snow", "trainer": "J J O'Shea", "jockey": "TBD",
             "odds": "5/1", "age": 8, "form": "1-1-2-1", "rating": 142,
             "cheltenham_record": "CD winner",
             "last_run": "Won Hunter Chase Feb 2026 (CD)", "days_off": 28},
            {"name": "Panda Boy", "trainer": "Martin Brassil", "jockey": "Keith Donoghue",
             "odds": "6/1", "age": 10, "form": "1-1-8-U3", "rating": 142,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Feb 2026", "days_off": 28},
            {"name": "Chemical Energy", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "8/1", "age": 10, "form": "1-1-1-14", "rating": 141,
             "cheltenham_record": "CD winner",
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
            {"name": "Its On The Line", "trainer": "Emmet Mullins", "jockey": "TBD",
             "odds": "7/1", "age": 9, "form": "1-1-2-32", "rating": 140,
             "cheltenham_record": "CD winner",
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
            {"name": "Stattler", "trainer": "Faye Bramley", "jockey": "TBD",
             "odds": "10/1", "age": 9, "form": "1-1-3-2", "rating": 137,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
            {"name": "What A Glance", "trainer": "Tom Britten", "jockey": "TBD",
             "odds": "12/1", "age": 9, "form": "1-2-1-3", "rating": 137,
             "cheltenham_record": "CD winner",
             "last_run": "3rd Hunter Chase Jan 2026 (CD)", "days_off": 42},
            {"name": "Wonderwall", "trainer": "S Curling", "jockey": "Rob James",
             "odds": "12/1", "age": 10, "form": "1-2-3-43", "rating": 136,
             "cheltenham_record": "Won 2025 Foxhunter Chase (at 28/1!) CD",
             "last_run": "3rd Hunter Chase Feb 2026", "days_off": 28},
            {"name": "Solitary Man", "trainer": "E Bolger", "jockey": "TBD",
             "odds": "14/1", "age": 10, "form": "1-1-4-1", "rating": 136,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
            {"name": "Con's Roc", "trainer": "Terence O'Brien", "jockey": "TBD",
             "odds": "14/1", "age": 9, "form": "3-1-1", "rating": 135,
             "cheltenham_record": None,
             "last_run": "Won Hunters Chase Jan 2026", "days_off": 42},
            {"name": "Golden Son", "trainer": "Paul Nicholls", "jockey": "Miss Olive Nicholls",
             "odds": "16/1", "age": 9, "form": "1-3-2-4", "rating": 132,
             "cheltenham_record": None,
             "last_run": "3rd Hunter Chase Feb 2026", "days_off": 28},
            {"name": "Music Drive", "trainer": "Kelly Morgan", "jockey": "TBD",
             "odds": "20/1", "age": 9, "form": "1-1-P-33", "rating": 132,
             "cheltenham_record": None,
             "last_run": "Won Hunter Chase Jan 2026", "days_off": 42},
        ]
    },
    "day4_race7": {   # Martin Pipe Conditional Jockeys' Handicap Hurdle  (2m179yds — 54 runners, Fri 13 Mar 17:20)
        # UPDATED 09/03/2026: Top-OR runners added from official Friday racecard
        "entries": [
            {"name": "Its Bilbo", "trainer": "Henry De Bromhead", "jockey": "TBD",
             "odds": "8/1", "age": 6, "form": "1-2-1-3", "rating": 141,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Jan 2026 (dual dec County)", "days_off": 42},
            {"name": "Sony Bill", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "8/1", "age": 5, "form": "1-1-2-3", "rating": 141,
             "cheltenham_record": None,
             "last_run": "3rd Grade 3 Handicap Hurdle Jan 2026 (dual dec County)", "days_off": 42},
            {"name": "Nurse Susan", "trainer": "Dan Skelton", "jockey": "Tristan Durrell",
             "odds": "9/1", "age": 7, "form": "1-1-2-1", "rating": 140,
             "cheltenham_record": "CD winner",
             "last_run": "Won Grade 2 Handicap Hurdle Feb 2026 (CD)", "days_off": 28},
            {"name": "Air Of Entitlement", "trainer": "Henry De Bromhead", "jockey": "TBD",
             "odds": "10/1", "age": 6, "form": "1-2-1-1-2", "rating": 139,
             "cheltenham_record": "CD winner",
             "last_run": "2nd Handicap Hurdle Jan 2026 (CD)", "days_off": 42},
            {"name": "Sa Fureur", "trainer": "Gordon Elliott", "jockey": "TBD",
             "odds": "10/1", "age": 7, "form": "2-1-1-3-2", "rating": 138,
             "cheltenham_record": None,
             "last_run": "Won Handicap Hurdle Feb 2026", "days_off": 28},
            {"name": "Fiercely Proud", "trainer": "Ben Pauling", "jockey": "TBD",
             "odds": "12/1", "age": 6, "form": "1-3-1-2", "rating": 137,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "East India Express", "trainer": "Nicky Henderson", "jockey": "Freddie Gordon",
             "odds": "12/1", "age": 6, "form": "1-1-2-3", "rating": 137,
             "cheltenham_record": "CD winner",
             "last_run": "Won Handicap Hurdle Feb 2026 (CD)", "days_off": 28},
            {"name": "Roc Dino", "trainer": "Willie Mullins", "jockey": "TBD",
             "odds": "14/1", "age": 5, "form": "2-2-3-27", "rating": 131,
             "cheltenham_record": None,
             "last_run": "2nd Handicap Hurdle Dec 2025", "days_off": 77},
            {"name": "A Pai De Nom", "trainer": "Dan Skelton", "jockey": "Harry Skelton",
             "odds": "16/1", "age": 6, "form": "1-5-3-31", "rating": 130,
             "cheltenham_record": None,
             "last_run": "3rd Handicap Jan 2026", "days_off": 42},
            {"name": "The Passing Wife", "trainer": "Gavin Cromwell", "jockey": "Danny Mullins",
             "odds": "16/1", "age": 7, "form": "5-5-8-21", "rating": 139,
             "cheltenham_record": None,
             "last_run": "Won Conditional Handicap Hurdle Jan 2026", "days_off": 42},
            {"name": "Kel Histoire", "trainer": "Willie Mullins", "jockey": "Mark Walsh",
             "odds": "16/1", "age": 6, "form": "4-3-4-18", "rating": 129,
             "cheltenham_record": None,
             "last_run": "Won Handicap Jan 2026", "days_off": 42},
            {"name": "He Can't Dance", "trainer": "Gordon Elliott", "jockey": "Jack Kennedy",
             "odds": "20/1", "age": 6, "form": "1-3-4-22", "rating": 128,
             "cheltenham_record": None,
             "last_run": "2nd Grade 2 Hurdle Jan 2026", "days_off": 42},
            {"name": "Zanndabad", "trainer": "A J Martin", "jockey": "TBD",
             "odds": "20/1", "age": 7, "form": "1-1-2-62", "rating": 128,
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
            (
                "won" in (horse.get("cheltenham_record", "") or "").lower() or
                "winner" in (horse.get("cheltenham_record", "") or "").lower() or
                # Racing Post shorthand: 'C' = course winner (standalone token e.g. 'C D', 'C')
                bool(re.search(r'\bC\b', horse.get("cheltenham_record", "") or ""))
            )
        )
        results.append({
            "name":             horse["name"],
            "trainer":          horse.get("trainer", "?"),
            "jockey":           horse.get("jockey", "?"),
            "odds":             horse.get("odds", "sp"),
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
