"""
Applies GUEST_SOCIALS (extracted from CBPC's own show notes) to the guests
table. Uses COALESCE so it never overwrites a value that's already there --
safe to re-run if new entries get added to guest_socials_extracted.py later.

Usage:
    python3 apply_guest_socials.py
"""
import sqlite3
import json
from guest_socials_extracted import GUEST_SOCIALS

DB_PATH = "cbpc.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    all_guests = {r[0] for r in conn.execute("SELECT normalized_name FROM guests")}

    matched, unmatched = 0, []
    for norm_name, data in GUEST_SOCIALS.items():
        if norm_name not in all_guests:
            unmatched.append(norm_name)
            continue
        matched += 1
        website = data.get("website")
        socials = data.get("social_handles")
        conn.execute(
            """UPDATE guests SET
               website_url = COALESCE(website_url, ?),
               social_handles = COALESCE(social_handles, ?)
               WHERE normalized_name = ?""",
            (website, json.dumps(socials) if socials else None, norm_name),
        )
    conn.commit()

    print(f"Matched and updated: {matched} of {len(GUEST_SOCIALS)}")
    if unmatched:
        print(f"Unmatched (name mismatch -- check normalized_name in the guests table):")
        for k in unmatched:
            print(" ", k)

    total = conn.execute("SELECT COUNT(*) FROM guests").fetchone()[0]
    filled = conn.execute(
        "SELECT COUNT(*) FROM guests WHERE website_url IS NOT NULL OR social_handles IS NOT NULL"
    ).fetchone()[0]
    print(f"Guests with at least a website or social handle: {filled} of {total}")


if __name__ == "__main__":
    main()
