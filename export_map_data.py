"""
Exports guest map data from cbpc.db for the D3 map (cbpc_guest_map.html).

Unlike the earlier placeholder version, this reads guests.lat/lon directly
-- it assumes geocode_guests.py has already run and those columns are
populated with real, verified coordinates. No hardcoded city lookup table.

Guests still get a small deterministic jitter applied so same-city guests
(there are a lot of "Atlanta, Georgia" rows) don't render as one
indistinguishable overlapping dot -- this is a display-only offset, the
underlying stored lat/lon is untouched.
"""
import sqlite3
import json
import hashlib

DB_PATH = "cbpc.db"
OUT_PATH = "map_data.json"

# Countries an albersUsa (US-only) projection cannot plot -- shown in the
# "off the map" panel instead of silently dropped
NON_US_COUNTRIES = {"canada", "portugal", "united kingdom"}


def jitter(guest_id, lat, lon, spread=0.15):
    h = int(hashlib.md5(str(guest_id).encode()).hexdigest(), 16)
    dx = ((h % 1000) / 1000 - 0.5) * spread
    dy = (((h // 1000) % 1000) / 1000 - 0.5) * spread
    return lat + dy, lon + dx


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    on_map, off_map = [], []
    for g in conn.execute("SELECT * FROM guests ORDER BY display_name"):
        record = {
            "guest_id": g["guest_id"],
            "name": g["display_name"],
            "category": g["category"],
            "city": g["city"],
            "state": g["state"],
            "country": g["country"],
            "website": g["website_url"] or g["company_website"],
            "social": json.loads(g["social_handles"]) if g["social_handles"] else {},
        }

        if not g["city"]:
            record["reason"] = "no location yet"
            off_map.append(record)
            continue

        if (g["country"] or "").strip().lower() in NON_US_COUNTRIES:
            record["reason"] = f"outside the US ({g['country']})"
            off_map.append(record)
            continue

        if g["lat"] is None or g["lon"] is None:
            record["reason"] = "geocoding failed for this location -- check geocode_cache"
            off_map.append(record)
            continue

        lat, lon = jitter(g["guest_id"], g["lat"], g["lon"])
        record["lat"] = lat
        record["lon"] = lon
        on_map.append(record)

    with open(OUT_PATH, "w") as f:
        json.dump({"on_map": on_map, "off_map": off_map}, f, indent=2)

    print(f"On map: {len(on_map)}")
    print(f"Off map (international, unresolved, or failed geocoding): {len(off_map)}")
    for r in off_map:
        print(f"  {r['name']}: {r['reason']}")


if __name__ == "__main__":
    main()
