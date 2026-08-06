"""
Geocodes guests.city/state/country into lat/lon using OpenStreetMap's free
Nominatim service. Respects Nominatim's usage policy: max 1 request/second,
identifiable User-Agent, and results are cached in a `geocode_cache` table
so the same location (there are a lot of "Atlanta, Georgia, United States"
rows) is never looked up twice, on this run or any future one.

NOTE: this needs real internet access to nominatim.openstreetmap.org.
It will NOT run inside a restricted sandbox (e.g. Claude's bash tool) --
run it locally, or as a step in the GitHub Actions workflow, where it will
work fine.

Usage:
    pip install requests --break-system-packages
    python3 geocode_guests.py
"""
import sqlite3
import time
import requests

DB_PATH = "cbpc.db"
USER_AGENT = "cbpc-guest-map/1.0 (contact: info@mkm-consultancy.com)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
RATE_LIMIT_SECONDS = 1.1  # stay comfortably under Nominatim's 1 req/sec cap


def ensure_cache_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS geocode_cache (
            query_key   TEXT PRIMARY KEY,   -- normalized "city|state|country"
            lat         REAL,
            lon         REAL,
            found       INTEGER NOT NULL,   -- 0/1 -- cache misses too, so we don't retry every run
            looked_up_at TEXT
        )
    """)


def make_query_key(city, state, country):
    parts = [p.strip() for p in (city, state, country) if p and p.strip()]
    return "|".join(parts).lower()


def geocode(city, state, country):
    query = ", ".join(p for p in (city, state, country) if p)
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if results:
        return float(results[0]["lat"]), float(results[0]["lon"])
    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_cache_table(conn)

    guests = conn.execute("""
        SELECT guest_id, city, state, country FROM guests
        WHERE city IS NOT NULL AND lat IS NULL
    """).fetchall()

    print(f"Guests needing geocoding: {len(guests)}")

    updated, cache_hits, api_calls, failures = 0, 0, 0, []
    for guest_id, city, state, country in guests:
        key = make_query_key(city, state, country)
        cached = conn.execute(
            "SELECT lat, lon, found FROM geocode_cache WHERE query_key = ?", (key,)
        ).fetchone()

        if cached:
            cache_hits += 1
            lat, lon, found = cached
            if not found:
                failures.append((guest_id, city, state, country))
                continue
        else:
            api_calls += 1
            result = geocode(city, state, country)
            if result:
                lat, lon = result
                conn.execute(
                    "INSERT INTO geocode_cache (query_key, lat, lon, found, looked_up_at) "
                    "VALUES (?, ?, ?, 1, datetime('now'))",
                    (key, lat, lon),
                )
            else:
                conn.execute(
                    "INSERT INTO geocode_cache (query_key, lat, lon, found, looked_up_at) "
                    "VALUES (?, NULL, NULL, 0, datetime('now'))",
                    (key,),
                )
                failures.append((guest_id, city, state, country))
                time.sleep(RATE_LIMIT_SECONDS)
                continue
            time.sleep(RATE_LIMIT_SECONDS)  # only sleep on actual API calls, not cache hits

        conn.execute("UPDATE guests SET lat = ?, lon = ? WHERE guest_id = ?", (lat, lon, guest_id))
        updated += 1

    conn.commit()

    print(f"Updated: {updated}")
    print(f"Served from cache (no API call needed): {cache_hits}")
    print(f"Fresh API calls made: {api_calls}")
    print(f"Failed to geocode ({len(failures)}):")
    for guest_id, city, state, country in failures:
        print(f"  guest_id={guest_id}: '{city}, {state}, {country}' -- check for typos")


if __name__ == "__main__":
    main()
