"""
Check Betfair for Days 2, 3, 4 Cheltenham runners and odds.
Prints full field for each race — no DynamoDB writes.
"""
import json, requests, time, sys, os
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
BETFAIR_API = "https://api.betfair.com/exchange/betting/rest/v1.0"

with open(os.path.join(ROOT, "betfair-creds.json")) as f:
    creds = json.load(f)

headers = {
    "X-Application":   creds["app_key"],
    "X-Authentication": creds["session_token"],
    "Content-Type":    "application/json",
}


def bf_post(endpoint, payload, timeout=30):
    r = requests.post(f"{BETFAIR_API}/{endpoint}/", headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def dec_to_frac(dec):
    if not dec:
        return "?"
    fracs = [
        (0.5,"1/2"),(0.75,"3/4"),(1.0,"Evs"),(1.25,"5/4"),(1.5,"6/4"),
        (1.75,"7/4"),(2.0,"2/1"),(2.25,"9/4"),(2.5,"5/2"),(2.75,"11/4"),
        (3.0,"3/1"),(3.5,"7/2"),(4.0,"4/1"),(4.5,"9/2"),(5.0,"5/1"),
        (6.0,"6/1"),(7.0,"7/1"),(8.0,"8/1"),(9.0,"9/1"),(10.0,"10/1"),
        (11.0,"11/1"),(12.0,"12/1"),(14.0,"14/1"),(16.0,"16/1"),(20.0,"20/1"),
        (25.0,"25/1"),(33.0,"33/1"),(40.0,"40/1"),(50.0,"50/1"),(66.0,"66/1"),
    ]
    n = dec - 1.0
    if n <= 0:
        return "EVS"
    return min(fracs, key=lambda x: abs(x[0] - n))[1]


# ── 1. Get event IDs (deduplicated) ─────────────────────────────────────────
events = bf_post("listEvents", {"filter": {"eventTypeIds": ["7"], "textQuery": "Cheltenham"}})
seen_ids = set()
chelt_ids = []
for ev in events:
    name = ev.get("event", {}).get("name", "")
    od   = ev.get("event", {}).get("openDate", "")
    eid  = ev["event"]["id"]
    if "2026" in od and "Cheltenham" in name and eid not in seen_ids:
        seen_ids.add(eid)
        chelt_ids.append(eid)
        print(f"  Event: {name}  id={eid}  date={od[:10]}")

print(f"\nUnique 2026 Cheltenham events: {len(chelt_ids)}\n")

# ── 2. Get WIN market catalogue — one event at a time (avoids DSC-0008) ──────
cat = []
for eid in chelt_ids:
    try:
        chunk = bf_post("listMarketCatalogue", {
            "filter": {
                "eventTypeIds":    ["7"],
                "eventIds":        [eid],
                "marketTypeCodes": ["WIN"],
            },
            "sort":             "FIRST_TO_START",
            "maxResults":       20,
            "marketProjection": ["MARKET_NAME", "RUNNER_DESCRIPTION", "RUNNER_METADATA",
                                 "EVENT", "MARKET_START_TIME"],
        })
        cat.extend(chunk)
        time.sleep(0.3)
    except Exception as e:
        print(f"  ⚠ Could not fetch event {eid}: {e}")

# Deduplicate by market ID
seen_mids = set()
cat_dedup = []
for m in cat:
    if m["marketId"] not in seen_mids:
        seen_mids.add(m["marketId"])
        cat_dedup.append(m)
cat = sorted(cat_dedup, key=lambda x: x.get("marketStartTime", ""))

print(f"Found {len(cat)} WIN markets:")
for m in cat:
    start  = m.get("marketStartTime", "")[:16].replace("T", " ")
    nrun   = len(m.get("runners", []))
    mname  = m.get("marketName", "")
    mid    = m["marketId"]
    print(f"  {start}  {mname:<52}  {mid}  ({nrun} runners)")

# ── 3. Get prices ────────────────────────────────────────────────────────────
market_ids = [m["marketId"] for m in cat]
all_books  = {}
for i in range(0, len(market_ids), 10):
    batch = market_ids[i:i+10]
    books = bf_post("listMarketBook", {
        "marketIds": batch,
        "priceProjection": {"priceData": ["EX_BEST_OFFERS"], "exBestOffersCnt": 1},
    })
    for book in books:
        all_books[book["marketId"]] = book
    time.sleep(0.2)

# ── 4. Print Days 2, 3, 4 fields ─────────────────────────────────────────────
DAY_FILTER = {
    "2026-03-11": "Day 2 — Wednesday",
    "2026-03-12": "Day 3 — Thursday",
    "2026-03-13": "Day 4 — Friday",
}

print("\n" + "=" * 80)
print("  CHELTENHAM 2026 — DAYS 2, 3, 4 RUNNERS (live Betfair odds)")
print("=" * 80)

total_runners = 0
for m in cat:
    start    = m.get("marketStartTime", "")[:10]
    day_label = DAY_FILTER.get(start)
    if not day_label:
        continue  # skip Day 1

    mname = m.get("marketName", "")
    mid   = m["marketId"]
    start_time = m.get("marketStartTime", "")[11:16]

    # Build runner price map
    book = all_books.get(mid, {})
    price_map = {}
    for r in book.get("runners", []):
        sid   = r["selectionId"]
        backs = r.get("ex", {}).get("availableToBack", [])
        price = backs[0]["price"] if backs else None
        price_map[sid] = {"status": r.get("status", ""), "price": price}

    # Build runner list
    runners = []
    for r in m.get("runners", []):
        sid   = r["selectionId"]
        name  = r.get("runnerName", "")
        meta  = r.get("metadata", {}) or {}
        pinfo = price_map.get(sid, {})
        if pinfo.get("status") == "REMOVED":
            continue
        cloth  = meta.get("CLOTH_NUMBER_ALPHA") or meta.get("CLOTH_NUMBER", "?")
        odds_d = pinfo.get("price")
        runners.append({
            "cloth":    str(cloth),
            "name":     name,
            "odds_d":   odds_d,
            "odds_f":   dec_to_frac(odds_d),
            "trainer":  meta.get("TRAINER_NAME", "?"),
            "jockey":   meta.get("JOCKEY_NAME", "?"),
            "form":     meta.get("FORM", "-"),
            "or_":      meta.get("OFFICIAL_RATING", "-"),
        })
    runners.sort(key=lambda x: (x["odds_d"] or 9999, x["cloth"]))
    total_runners += len(runners)

    print(f"\n  {day_label}  |  {start_time}  {mname}  [{mid}]")
    print(f"  {'':-<78}")
    print(f"  {'#':<4}{'HORSE':<32}{'ODDS':<9}{'TRAINER':<28}{'JOCKEY':<22}{'FORM':<10}OR")
    print(f"  {'':-<78}")
    for r in runners:
        print(f"  {r['cloth']:<4}{r['name']:<32}{r['odds_f']:<9}{r['trainer']:<28}{r['jockey']:<22}{r['form']:<10}{r['or_']}")

print(f"\n  Total active runners Days 2-4: {total_runners}")
print(f"  Fetched at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
