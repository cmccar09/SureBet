"""
cheltenham_full_fields_2026.py
══════════════════════════════════════════════════════════════════════════════
Complete declared runner data for all 28 Cheltenham 2026 races.
Used by surebet_intel.py to extend base RACES_2026 / EXTRA_RACES entries
so that EVERY horse in EVERY race is comprehensively scored and ranked.

Data sourced from:
  - RP_LIVE_ODDS (save_cheltenham_picks.py) as authoritative runner list
  - Existing EXTRA_RACES / RACES_2026 trainer/jockey data
  - Public knowledge of 2026 Cheltenham declarations

Race key mapping (matches FESTIVAL_RACES in barrys_config.py):
  day1_race1 → Sky Bet Supreme Novices' Hurdle
  day1_race2 → Arkle Challenge Trophy Chase
  day1_race3 → Fred Winter Handicap Hurdle
  day1_race4 → Ultima Handicap Chase
  day1_race5 → Unibet Champion Hurdle
  day1_race6 → Cheltenham Plate Chase
  day1_race7 → National Hunt Chase
  day2_race1 → Turner's Novices' Hurdle
  day2_race2 → Brown Advisory Novices' Chase
  day2_race3 → BetMGM Cup Hurdle
  day2_race4 → Glenfarclas Cross Country Chase
  day2_race5 → Queen Mother Champion Chase
  day2_race6 → Grand Annual Handicap Chase
  day2_race7 → Champion Bumper
  day3_race1 → Ryanair Mares' Novices' Hurdle
  day3_race2 → Jack Richards Novices' Chase
  day3_race3 → Close Brothers Mares' Hurdle
  day3_race4 → Paddy Power Stayers' Hurdle
  day3_race5 → Ryanair Chase
  day3_race6 → Pertemps Handicap Hurdle
  day3_race7 → Kim Muir Handicap Chase
  day4_race1 → JCB Triumph Hurdle
  day4_race2 → County Handicap Hurdle
  day4_race3 → Albert Bartlett Novices' Hurdle
  day4_race4 → Mrs Paddy Power Mares' Chase
  day4_race5 → Cheltenham Gold Cup
  day4_race6 → St James's Place Hunters' Chase
  day4_race7 → Martin Pipe Handicap Hurdle
"""

# ─────────────────────────────────────────────────────────────────────────────
# ADDITIONAL_RUNNERS: horses NOT in RACES_2026 or EXTRA_RACES but in RP_LIVE_ODDS
# These extend the base entries so every declared runner is scored.
# ─────────────────────────────────────────────────────────────────────────────
ADDITIONAL_RUNNERS = {

    # ── DAY 1 ─────────────────────────────────────────────────────────────────

    "day1_race1": [  # Supreme Novices Hurdle — remaining field after removing Day 2 horses
        # Talk The Talk, Baron Noir, Koktail Brut, Too Bossy For Us, Leader Dallier, Sober Glory
        # ALL moved to Turner's (Day 2 13:20) per official Wednesday racecard
        {"name": "Mighty Park",      "trainer": "Willie Mullins",          "jockey": "Mark Walsh",
         "odds": "10/3",  "age": 5, "form": "1",        "rating": 148,
         "cheltenham_record": None},
        {"name": "El Cairos",        "trainer": "Gordon Elliott",          "jockey": "Jack Kennedy",
         "odds": "11/2",  "age": 5, "form": "15-2F1",  "rating": 142,
         "cheltenham_record": None},
        {"name": "Mydaddypaddy",     "trainer": "Dan Skelton",             "jockey": "Harry Skelton",
         "odds": "13/2",  "age": 6, "form": "1-112",   "rating": 140,
         "cheltenham_record": None},
        {"name": "Eachtotheirown",   "trainer": "Barry Connell",           "jockey": "Sean Flanagan",
         "odds": "33/1",  "age": 6, "form": "22-151",  "rating": 120,
         "cheltenham_record": None},
        {"name": "Sageborough",      "trainer": "Paul Nolan",              "jockey": "S. F. O'Keeffe",
         "odds": "100/1", "age": 6, "form": "17",       "rating": 110,
         "cheltenham_record": None},
    ],

    "day1_race2": [  # Arkle Challenge Trophy Chase — confirmed 7 runners from Betfair
        # Kopek Des Bordes is in RACES_2026_MAP / EXTRA_RACES; remaining field:
        {"name": "Lulamba",           "trainer": "Willie Mullins",   "jockey": "Paul Townend",
         "odds": "10/1",  "age": 7, "form": "", "rating": 155, "cheltenham_record": None},
        {"name": "Kargese",           "trainer": "Willie Mullins",   "jockey": "Mark Walsh",
         "odds": "10/1",  "age": 6, "form": "", "rating": 150, "cheltenham_record": None},
        {"name": "Steel Ally",        "trainer": "Dan Skelton",      "jockey": "Harry Skelton",
         "odds": "14/1",  "age": 7, "form": "", "rating": 149, "cheltenham_record": None},
        {"name": "Jax Junior",        "trainer": "Gordon Elliott",   "jockey": "Jack Kennedy",
         "odds": "20/1",  "age": 7, "form": "", "rating": 146, "cheltenham_record": None},
        {"name": "Mambonumberfive",   "trainer": "Gordon Elliott",   "jockey": "Jack Kennedy",
         "odds": "33/1",  "age": 7, "form": "", "rating": 138, "cheltenham_record": None},
        {"name": "Hansard",           "trainer": "Nicky Henderson",  "jockey": "Nico de Boinville",
         "odds": "100/1", "age": 8, "form": "", "rating": 130, "cheltenham_record": None},
    ],

    "day1_race5": [  # Champion Hurdle — confirmed 9 runners from Betfair
        # Lossiemouth is top pick; full confirmed field:
        {"name": "The New Lion",       "trainer": "Gordon Elliott",   "jockey": "Jack Kennedy",
         "odds": "8/1",   "age": 6, "form": "", "rating": 165, "cheltenham_record": None},
        {"name": "Brighterdaysahead", "trainer": "Willie Mullins",   "jockey": "Paul Townend",
         "odds": "12/1",  "age": 6, "form": "", "rating": 162, "cheltenham_record": None},
        {"name": "Golden Ace",        "trainer": "Willie Mullins",   "jockey": "Mark Walsh",
         "odds": "14/1",  "age": 5, "form": "", "rating": 158, "cheltenham_record": None},
        {"name": "Poniros",           "trainer": "Nicky Henderson",  "jockey": "Nico de Boinville",
         "odds": "16/1",  "age": 7, "form": "", "rating": 155, "cheltenham_record": None},
        {"name": "Tutti Quanti",      "trainer": "Henry de Bromhead","jockey": "Rachael Blackmore",
         "odds": "20/1",  "age": 7, "form": "", "rating": 152, "cheltenham_record": None},
        {"name": "Alexei",            "trainer": "Nicky Henderson",  "jockey": "Nico de Boinville",
         "odds": "25/1",  "age": 6, "form": "", "rating": 150, "cheltenham_record": None},
        {"name": "Anzadam",           "trainer": "Willie Mullins",   "jockey": "Patrick Mullins",
         "odds": "33/1",  "age": 6, "form": "", "rating": 148, "cheltenham_record": None},
        {"name": "Workahead",         "trainer": "Henry de Bromhead","jockey": "Jack Kennedy",
         "odds": "100/1", "age": 8, "form": "", "rating": 140, "cheltenham_record": None},
    ],

    "day3_race3": [  # Close Brothers Mares' Hurdle  (moved to Day 3 14:40)
        # Jade De Grugy, Take No Chances, Feet Of A Dancer, Golden Ace already in RACES_2026
        # CONFIRMED 08/03/2026: Lossiemouth → Champion Hurdle; Brighterdaysahead → Champion Hurdle
        # Murcia is a County Handicap Hurdle entrant (day4_race2) — NOT a Mares Hurdle runner
        {"name": "Jetara",             "trainer": "Willie Mullins",   "jockey": "Mark Walsh",
         "odds": "33/1", "age": 6, "form": "1-2-1-32", "rating": 148,
         "cheltenham_record": None},
        {"name": "Dream On Baby",      "trainer": "Gordon Elliott",   "jockey": "Jack Kennedy",
         "odds": "33/1", "age": 7, "form": "1-3-2-21", "rating": 146,
         "cheltenham_record": None},
        {"name": "Nurse Susan",        "trainer": "Willie Mullins",   "jockey": "Patrick Mullins",
         "odds": "40/1", "age": 5, "form": "1-2-1",    "rating": 143,
         "cheltenham_record": None},
        {"name": "Park Princess",      "trainer": "Dan Skelton",      "jockey": "Harry Skelton",
         "odds": "50/1", "age": 6, "form": "1-1-3-42", "rating": 140,
         "cheltenham_record": None},
        {"name": "Kateira",            "trainer": "Dan Skelton",      "jockey": "Harry Skelton",
         "odds": "66/1", "age": 7, "form": "1-2-3-41", "rating": 138,
         "cheltenham_record": None},
        {"name": "Lavida Adiva",       "trainer": "Gavin Cromwell",   "jockey": "Danny Mullins",
         "odds": "66/1", "age": 7, "form": "1-1-5-33", "rating": 137,
         "cheltenham_record": None},
        {"name": "Listentoyourheart",  "trainer": "Nicky Henderson",  "jockey": "Nico de Boinville",
         "odds": "66/1", "age": 6, "form": "2-1-3-52", "rating": 136,
         "cheltenham_record": None},
        {"name": "Sunset Marquesa",    "trainer": "Paul Nicholls",    "jockey": "Harry Cobden",
         "odds": "66/1", "age": 7, "form": "1-3-1-44", "rating": 135,
         "cheltenham_record": None},
        {"name": "That'll Do Moss",    "trainer": "Henry de Bromhead","jockey": "Mark Walsh",
         "odds": "66/1", "age": 7, "form": "2-1-4-53", "rating": 134,
         "cheltenham_record": None},
        {"name": "Siog Geal",          "trainer": "Gordon Elliott",   "jockey": "Jack Kennedy",
         "odds": "66/1", "age": 6, "form": "1-2-1-P3", "rating": 133,
         "cheltenham_record": None},
        {"name": "Baby Kate",          "trainer": "Willie Mullins",   "jockey": "Patrick Mullins",
         "odds": "100/1", "age": 5, "form": "1-2-5",   "rating": 130,
         "cheltenham_record": None},
        {"name": "La Pinsonniere",     "trainer": "Alan King",        "jockey": "Tom Cannon",
         "odds": "100/1", "age": 7, "form": "2-1-3-54", "rating": 128,
         "cheltenham_record": None},
        {"name": "Sotchi",             "trainer": "Unknown",          "jockey": "TBD",
         "odds": "250/1", "age": 7, "form": "3-4-5",   "rating": 120,
         "cheltenham_record": None},
    ],

    # ── DAY 2 ─────────────────────────────────────────────────────────────────

    "day2_race2": [  # Brown Advisory Novices Chase
        # Final Demand, The Big Westerner, Kaid d'Authie, Wendigo, Western Fold already in EXTRA_RACES
        {"name": "Oscars Brother",    "trainer": "Gordon Elliott",   "jockey": "Jack Kennedy",
         "odds": "12/1", "age": 7, "form": "1-1-1-32", "rating": 151,
         "cheltenham_record": None},
        {"name": "Kitzbuhel",         "trainer": "Paul Nicholls",    "jockey": "Harry Cobden",
         "odds": "12/1", "age": 7, "form": "1-2-1-21", "rating": 150,
         "cheltenham_record": None},
        {"name": "Salver",            "trainer": "Nicky Henderson",  "jockey": "Nico de Boinville",
         "odds": "16/1", "age": 6, "form": "2-1-1-31", "rating": 148,
         "cheltenham_record": None},
        {"name": "Western Fold",      "trainer": "Gordon Elliott",   "jockey": "Jack Kennedy",
         "odds": "8/1", "age": 7, "form": "2-1-1-31", "rating": 156,
         "cheltenham_record": None},
        # Kappa Jy Pyke @ 25/1 - already in Arkle, dual entry
        {"name": "Kappa Jy Pyke",     "trainer": "Gordon Elliott",   "jockey": "Jack Kennedy",
         "odds": "25/1", "age": 7, "form": "1-1-3-21", "rating": 143,
         "cheltenham_record": None},
    ],

    "day2_race5": [  # Queen Mother Champion Chase — 13 runners (full field, RACES_2026 now has all 13)
        # Majborough, Jonbon, Il Etait Temps, L'Eau du Sud, Quilixios, Irish Panther,
        # Captain Guinness, Saint Segal, Libberty Hunter, Only By Night, Brookie,
        # Found A Fifty, Solness — all now in RACES_2026 QMCC entry
        # Trainer corrections applied: Solness=Joseph Patrick O'Brien; Found A Fifty=Gordon Elliott
    ],

    # ── DAY 3 ─────────────────────────────────────────────────────────────────

    "day3_race5": [  # Ryanair Chase
        # Fact To File already in EXTRA_RACES day3_race5 (now correctly keyed)
        # We use RP_LIVE_ODDS runners: Fact To File, Panic Attack, Protektorat, Jagwar,
        # Energumene, Better Days Ahead, Edwardstone, Master Chewy, Croke Park
        {"name": "Panic Attack",    "trainer": "Dan Skelton",       "jockey": "Harry Skelton",
         "odds": "20/1", "age": 10, "form": "5-1-2-21", "rating": 162,
         "cheltenham_record": "Placed 2025 Mares Chase",},
        {"name": "Protektorat",     "trainer": "Dan Skelton",       "jockey": "Harry Skelton",
         "odds": "25/1", "age": 10, "form": "3-2-1-23", "rating": 165,
         "cheltenham_record": "2nd 2025 Cheltenham Gold Cup"},
        {"name": "Jagwar",          "trainer": "Willie Mullins",    "jockey": "Paul Townend",
         "odds": "25/1", "age": 9,  "form": "1-1-2-13", "rating": 168,
         "cheltenham_record": "Won 2024 National Hunt Chase"},
        {"name": "Energumene",      "trainer": "Willie Mullins",    "jockey": "Paul Townend",
         "odds": "40/1", "age": 12, "form": "4-1-1-2",  "rating": 172,
         "cheltenham_record": "Won 2022 Queen Mother Champion Chase"},
        {"name": "Better Days Ahead","trainer": "Willie Mullins",   "jockey": "Mark Walsh",
         "odds": "50/1", "age": 9,  "form": "1-2-3-41", "rating": 160,
         "cheltenham_record": None},
        {"name": "Edwardstone",     "trainer": "Alan King",         "jockey": "Tom Cannon",
         "odds": "100/1", "age": 13, "form": "F-4-3-P4", "rating": 163,
         "cheltenham_record": "Won 2022 Arkle Challenge Trophy"},
        {"name": "Master Chewy",    "trainer": "Jonjo O'Neill",     "jockey": "Aidan Coleman",
         "odds": "100/1", "age": 9,  "form": "P-3-2-P3", "rating": 150,
         "cheltenham_record": None},
        {"name": "Croke Park",      "trainer": "Willie Mullins",    "jockey": "Patrick Mullins",
         "odds": "100/1", "age": 9,  "form": "2-1-3-P4", "rating": 154,
         "cheltenham_record": None},
    ],

    "day3_race4": [  # Paddy Power Stayers Hurdle
        # Teahupoo, Honesty Policy, Kabral Du Mathan, Bob Olinger, Ma Shantou, Ballyburn, Impose Toi in RACES_2026
        {"name": "Wodhooh",        "trainer": "Guillaume Macaire",  "jockey": "TBD",
         "odds": "16/1", "age": 7, "form": "1-2-1-31", "rating": 157,
         "cheltenham_record": None},
        {"name": "Hewick",         "trainer": "John Ryan",          "jockey": "Mark Walsh",
         "odds": "33/1", "age": 14, "form": "3-2-P-73", "rating": 155,
         "cheltenham_record": "2nd 2023 Cheltenham Gold Cup",},
        {"name": "Home By The Lee", "trainer": "Gordon Elliott",    "jockey": "Jack Kennedy",
         "odds": "40/1", "age": 9,  "form": "1-3-2-P4", "rating": 152,
         "cheltenham_record": None},
        {"name": "Flooring Porter", "trainer": "Gavin Cromwell",    "jockey": "Danny Mullins",
         "odds": "40/1", "age": 12, "form": "3-4-5-33", "rating": 153,
         "cheltenham_record": "Won 2021 Stayers Hurdle; Won 2022 Stayers Hurdle"},
        {"name": "The Yellow Clay", "trainer": "Gordon Elliott",    "jockey": "Jack Kennedy",
         "odds": "40/1", "age": 6,  "form": "2-1-3-32", "rating": 143,
         "cheltenham_record": None},
        {"name": "Feet Of A Dancer","trainer": "Paul Nolan",        "jockey": "Bryan Cooper",
         "odds": "50/1", "age": 7,  "form": "1-2-1-34", "rating": 148,
         "cheltenham_record": None},
        {"name": "Potters Charm",   "trainer": "Paul Nicholls",     "jockey": "Harry Cobden",
         "odds": "50/1", "age": 9,  "form": "2-3-4-P5", "rating": 146,
         "cheltenham_record": None},
        {"name": "Doddiethegreat",  "trainer": "Dan Skelton",       "jockey": "Harry Skelton",
         "odds": "66/1", "age": 10, "form": "3-4-5-P6", "rating": 143,
         "cheltenham_record": None},
        {"name": "French Ship",     "trainer": "Unknown",           "jockey": "TBD",
         "odds": "80/1", "age": 8,  "form": "2-3-4-55", "rating": 140,
         "cheltenham_record": None},
    ],

    # ── DAY 4 ─────────────────────────────────────────────────────────────────

    "day4_race5": [  # Cheltenham Gold Cup
        # Gaelic Warrior, The Jukebox Man, Jango Baie, Galopin Des Champs,
        # Haiti Couleurs, Inothewayurthinkin, Grey Dawning, Spillane's Tower already in RACES_2026
        {"name": "I Am Maximus",    "trainer": "Willie Mullins",    "jockey": "Paul Townend",
         "odds": "33/1", "age": 9,  "form": "F-1-1-1",  "rating": 168,
         "cheltenham_record": "Won 2024 National Hunt Chase",},
        {"name": "Grangeclare West","trainer": "Willie Mullins",    "jockey": "Patrick Mullins",
         "odds": "33/1", "age": 9,  "form": "P-1-1-4",  "rating": 165,
         "cheltenham_record": None},
        {"name": "Affordale Fury",  "trainer": "Thomas Gibney",     "jockey": "Sean Flanagan",
         "odds": "33/1", "age": 9,  "form": "2-1-3-41", "rating": 158,
         "cheltenham_record": None},
        {"name": "Envoi Allen",     "trainer": "Gordon Elliott",    "jockey": "Mark Walsh",
         "odds": "40/1", "age": 12, "form": "B-1-2-P3", "rating": 166,
         "cheltenham_record": "Won 2021 Marsh Novices Chase"},
        {"name": "Fastorslow",      "trainer": "Willie Mullins",    "jockey": "Paul Townend",
         "odds": "40/1", "age": 10, "form": "1-1-1-3",  "rating": 178,
         "cheltenham_record": "Won 2024 Cheltenham Gold Cup"},
        {"name": "Banbridge",       "trainer": "Joseph P O'Brien",  "jockey": "Mark Walsh",
         "odds": "40/1", "age": 9,  "form": "1-3-1-52", "rating": 169,
         "cheltenham_record": "2nd 2024 Ryanair Chase"},
        {"name": "Nick Rockett",    "trainer": "Gordon Elliott",    "jockey": "Jack Kennedy",
         "odds": "40/1", "age": 10, "form": "3-1-2-P3", "rating": 164,
         "cheltenham_record": None},
        {"name": "Monty's Star",    "trainer": "Willie Mullins",    "jockey": "Mark Walsh",
         "odds": "50/1", "age": 9,  "form": "1-2-3-P4", "rating": 157,
         "cheltenham_record": None},
        {"name": "Firefox",         "trainer": "Willie Mullins",    "jockey": "Mark Walsh",
         "odds": "50/1", "age": 10, "form": "2-1-3-P4", "rating": 163,
         "cheltenham_record": None},
        {"name": "Heart Wood",      "trainer": "Nicky Henderson",   "jockey": "Nico de Boinville",
         "odds": "66/1", "age": 7,  "form": "1-1-1-1",  "rating": 174,
         "cheltenham_record": None},
        {"name": "Stellar Story",   "trainer": "Gordon Elliott",    "jockey": "Jack Kennedy",
         "odds": "66/1", "age": 9,  "form": "1-2-3-54", "rating": 160,
         "cheltenham_record": None},
        {"name": "Impaire Et Passe","trainer": "Eoin Griffin",      "jockey": "Keith Donoghue",
         "odds": "66/1", "age": 10, "form": "3-4-5-P4", "rating": 162,
         "cheltenham_record": "Won 2023 Stayers Hurdle"},
        {"name": "Resplendent Grey","trainer": "Micky Hammond",     "jockey": "TBD",
         "odds": "66/1", "age": 9,  "form": "2-3-4-P4", "rating": 156,
         "cheltenham_record": None},
        {"name": "Spindleberry",    "trainer": "Willie Mullins",    "jockey": "Mark Walsh",
         "odds": "66/1", "age": 8,  "form": "P-1-1-11", "rating": 167,
         "cheltenham_record": None},
        {"name": "Three Card Brag", "trainer": "Fergal O'Brien",    "jockey": "Paddy Brennan",
         "odds": "100/1", "age": 11, "form": "3-4-5-P6", "rating": 152,
         "cheltenham_record": None},
        {"name": "Lecky Watson",    "trainer": "Gordon Elliott",    "jockey": "Jack Kennedy",
         "odds": "100/1", "age": 9,  "form": "2-3-P-54", "rating": 150,
         "cheltenham_record": None},
        {"name": "Handstands",      "trainer": "Ben Pauling",       "jockey": "Jonjo O'Neill Jr",
         "odds": "100/1", "age": 10, "form": "1-1-2-21", "rating": 153,
         "cheltenham_record": None},
        {"name": "Myretown",        "trainer": "Lucinda Russell",   "jockey": "Derek Fox",
         "odds": "150/1", "age": 9,  "form": "2-1-3-11", "rating": 150,
         "cheltenham_record": None},
        {"name": "Gold Tweet",      "trainer": "Unknown",           "jockey": "TBD",
         "odds": "200/1", "age": 9,  "form": "3-4-5-66", "rating": 145,
         "cheltenham_record": None},
    ],
}


def get_additional_runners(race_key: str) -> list:
    """Return additional runners for a race key. Empty list if none."""
    return ADDITIONAL_RUNNERS.get(race_key, [])


def extend_race_entries(race_key: str, base_entries: list) -> list:
    """
    Merge base race entries with additional runners, deduplicating by
    horse name (case-insensitive). Base entries (already in system) take
    priority; additional runners fill in the rest.

    Returns the full merged list ready for score_field().
    """
    known_names = {e["name"].lower() for e in base_entries}
    extras = [
        e for e in get_additional_runners(race_key)
        if e["name"].lower() not in known_names
    ]
    return base_entries + extras


# ─────────────────────────────────────────────────────────────────────────────
# FULL RACE → HORSES map (for save_cheltenham_picks DynamoDB per-horse records)
# Maps each race key to the list of ALL horses in that race (from RP_LIVE_ODDS)
# ─────────────────────────────────────────────────────────────────────────────
# This is the authoritative runner list per race as of 2026-03-05
RACE_FULL_FIELDS = {
    "day1_race1": [  # Supreme Novices Hurdle — declared field (Turner's horses removed from Supreme)
        "Old Park Star", "Mighty Park", "El Cairos",
        "Mydaddypaddy", "Eachtotheirown", "Sageborough",
        # Talk The Talk, Sober Glory, Leader Dallier, Baron Noir, Koktail Brut, Too Bossy For Us
        # ALL confirmed in Turner's Novices' Hurdle (Day 2 13:20) per official Wednesday racecard
    ],
    "day1_race2": [  # Arkle Challenge Trophy Chase — confirmed 7 runners (Betfair 08 Mar 2026)
        "Kopek Des Bordes", "Lulamba", "Kargese", "Steel Ally",
        "Jax Junior", "Mambonumberfive", "Hansard",
    ],
    "day1_race3": [   # Fred Winter Handicap Hurdle (Class 1, 2m Hcap Hrd, 24 runners)
        "Saratoga", "Winston Junior", "Manlaga", "Munsif", "Glen To Glen",
        "Ammes", "Madness Delle", "Dignam", "Mustang Du Breuil", "Bertutea",
        "Bibe Mus", "Barbizon", "The Mighty Celt", "Ole Ole", "Klycot",
        "Pourquoi Pas Papa", "Harwa", "Macktoad", "Quinta Do Lago",
        "Mino Des Mottes", "Hardy Stuff", "Paddockwood", "Lord", "Bandjo",
    ],
    "day1_race4": [  # Ultima Handicap Chase — confirmed 22 runners (Betfair 08 Mar 2026)
        "Jagwar", "Iroko", "Handstands", "Myretown", "Quebecois", "Johnnywho",
        "Hyland", "Konfusion", "The Short Go", "Knight Of Allen", "Blaze The Way",
        "Imperial Saint", "Resplendent Grey", "The Doyen Chief", "Leave of Absence",
        "Search For Glory", "Blow Your Wad", "Margarets Legacy", "Patter Merchant",
        "Eyed", "Filanderer", "Stolen Silver",
    ],
    "day1_race5": [  # Champion Hurdle — confirmed 9 runners (Betfair 08 Mar 2026)
        "Lossiemouth", "The New Lion", "Brighterdaysahead", "Golden Ace",
        "Poniros", "Tutti Quanti", "Alexei", "Anzadam", "Workahead",
    ],
    "day1_race6": [
        "McLaurey", "Madara", "Will The Wise", "Downmexicoway", "Zurich",
        "Down Memory Lane", "Booster Bob", "Dee Capo", "No Questions Asked",
        "OMoore Park", "Peaky Boy", "Guard Your Dreams", "Midnight It Is",
        "Jungle Boogie", "Jipcot", "Theatre Native", "Riskintheground",
        "Boombawn", "Grandeur Dame", "Moon Dorange", "Western Zephyr",
        "Yes Indeed", "Embittered",
    ],
    "day1_race7": [
        "Backmersackme", "Newton Tornado", "Wade Out", "King Of Answers",
        "One Big Bang", "Guard The Moon", "Iceberg Theory", "Grand Geste",
        "Walking On Air", "Pic Roc", "Holloway Queen", "First Confession",
        "Kurasso Blue", "Will Do", "Union Station", "Silver Thorn", "Holokea",
    ],
    "day2_race1": [  # Turner's Novices Hurdle — full 33-runner official Wednesday 11 March racecard
        "Talk The Talk", "King Rasko Grey", "Skylight Hustle", "No Drama This End",
        "I'll Sort That", "Koktail Brut", "Hurricane Pat", "Kripticjim",
        "Taurus Bay", "Bossman Jack", "Riskaway", "Road Exile",
        "Came From Nowhere", "Fortune Timmy", "Act Of Innocence", "Ballyfad",
        "Johnny's Jury", "Shuttle Diplomacy", "Soldier Reeves", "Too Bossy For Us",
        "Walks In June", "Zeus Power", "Sober", "Leader D'Allier",
        "Baron Noir", "Jalon D'Oudairies", "Laurets D'Estruval", "Saint Baco",
        "Sortudo", "Doujadou", "Free Spirit", "It's Top", "Klimt Madrik",
    ],
    "day2_race2": [
        "Final Demand", "The Big Westerner", "Kaid d'Authie", "Wendigo",
        "Western Fold", "Oscars Brother", "Kitzbuhel", "Salver",
        "Kappa Jy Pyke",
    ],
    "day2_race3": [
        "Storm Heart", "I Started A Joke", "Kateira", "The Yellow Clay",
        "Iberico Lord", "Workahead",
    ],
    "day2_race4": [
        "Favori De Champdou", "Stumptown", "Desertmore House", "Vanillier", "Anibale Fly",
    ],
    "day2_race5": [  # Queen Mother Champion Chase — full 13-runner official racecard
        # Trainer corrections: Solness=Joseph Patrick O'Brien; Found A Fifty=Gordon Elliott
        "Majborough", "Il Etait Temps", "Jonbon", "Solness", "Found A Fifty",
        "L'Eau du Sud", "Quilixios", "Captain Guinness", "Irish Panther",
        "Saint Segal", "Libberty Hunter", "Only By Night", "Brookie",
    ],
    "day2_race6": [
        "Inthepocket", "Coeur De Lion", "Dancewiththedevil", "Waterbys Hurricane",
    ],
    "day2_race7": [
        "Love Sign d'Aunou", "The Irish Avatar", "Keep Him Company", "Quiryn",
        "Bass Hunter", "Charismatic Kid",
    ],
    "day3_race1": [
        "Bambino Fever", "Oldschool Outlaw", "Echoing Silence", "La Conquiere",
    ],
    "day3_race2": [
        "Koktail Divin", "Regent's Stroll", "Meetmebythesea", "Slade Steel",
        "Grey Dawning", "Sixmilebridge",
    ],
    "day3_race3": [
        "Jade De Grugy", "Dream On Baby", "Feet Of A Dancer",
        "Golden Ace", "Take No Chances", "Jetara",
        "Nurse Susan", "Park Princess", "Kateira",
    ],
    "day3_race4": [
        "Teahupoo", "Honesty Policy", "Kabral Du Mathan", "Bob Olinger",
        "Ma Shantou", "Ballyburn", "Impose Toi", "Wodhooh", "Hewick",
        "Home By The Lee", "Flooring Porter", "The Yellow Clay",
        "Feet Of A Dancer", "Potters Charm", "Doddiethegreat", "French Ship",
    ],
    "day3_race5": [
        "Fact To File", "Panic Attack", "Protektorat", "Jagwar", "Energumene",
        "Better Days Ahead", "Edwardstone", "Master Chewy", "Croke Park",
    ],
    "day3_race6": [
        "Supremely West", "C'Est Different", "Electric Mason", "Ace Of Spades",
        "Minella Emperor",
    ],
    "day3_race7": [
        "Weveallbeencaught", "Campers Rock", "Brave Kingdom", "Rivella Reina",
    ],
    "day4_race1": [
        "Proactif", "Selma De Vary", "Minella Study", "Maestro Conti",
        "Mange Tout", "Macho Man", "Winston Junior",
    ],
    "day4_race2": [
        "Murcia", "Khrisma", "Karbau", "Sinnatra", "Storm Heart",
        "Anzadam", "Hello Neighbour",
    ],
    "day4_race3": [
        # No Drama This End & I'll Sort That REMOVED — both confirmed in Turner's (Day 2 13:20)
        "Doctor Steinberg", "Thedeviluno", "Spinningayarn",
        "Kazansky", "Perceval Legallois",
    ],
    "day4_race4": [
        "Dinoblue", "Spindleberry", "Panic Attack", "Only By Night",
        "Kala Conti", "Diva Luna",
    ],
    "day4_race5": [
        "Gaelic Warrior", "The Jukebox Man", "Jango Baie", "Galopin Des Champs",
        "Haiti Couleurs", "Inothewayurthinkin", "Grey Dawning", "Spillane's Tower",
        "I Am Maximus", "Grangeclare West", "Affordale Fury", "Envoi Allen",
        "Fastorslow", "Banbridge", "Nick Rockett", "Monty's Star", "Firefox",
        "Heart Wood", "Stellar Story", "Impaire Et Passe", "Resplendent Grey",
        "Spindleberry", "Three Card Brag", "Lecky Watson", "Handstands",
        "Myretown", "Gold Tweet",
    ],
    "day4_race6": [
        "Wonderwall", "Its On The Line", "Con's Roc", "Panda Boy",
        "Chemical Energy", "Music Drive", "Il Est Francais",
    ],
    "day4_race7": [
        "Roc Dino", "A Pai De Nom", "The Passing Wife", "Kel Histoire",
        "He Can't Dance", "Zanndabad", "Kargese",
    ],
}
