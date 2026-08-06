"""
Merges the CBPC guest research spreadsheet (Google Sheets) into cbpc.db,
matched by Guest ID -- the one column the sheet's instructions say not to
edit, specifically so it stays a reliable join key back to guests.guest_id.

Re-runnable: safe to run again anytime the sheet is updated. Uses direct
value assignment (not COALESCE) for sheet-sourced fields, since the sheet
is the authoritative source for this data -- if a cell gets cleared in the
sheet, that should clear it here too, not preserve a stale value.

Usage:
    python3 merge_guest_sheet.py path/to/exported_sheet.tsv
    (tab- or comma-separated; header row required)
"""
import sqlite3
import json
import sys
import csv

DB_PATH = "cbpc.db"

REQUIRED_COLS = [
    "Guest ID", "Guest Name", "City", "State", "Country",
    "Instution/Company", "Company Website", "Instagram", "Tiktok",
    "Facebook", "LinkedIn", "Personal Website", "Status", "Notes",
]


def ensure_columns(conn):
    existing = {r[1] for r in conn.execute("PRAGMA table_info(guests)")}
    new_cols = {
        "country": "TEXT",
        "institution": "TEXT",
        "company_website": "TEXT",
        "status": "TEXT",
    }
    for col, coltype in new_cols.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE guests ADD COLUMN {col} {coltype}")


def clean(val):
    val = (val or "").strip()
    return None if val in ("", "N/A", "n/a", "N/a") else val


def main(rows):
    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)

    matched, unmatched, skipped_blank = 0, [], 0
    for row in rows:
        guest_id = clean(row.get("Guest ID"))
        if not guest_id:
            continue
        exists = conn.execute(
            "SELECT 1 FROM guests WHERE guest_id = ?", (guest_id,)
        ).fetchone()
        if not exists:
            unmatched.append((guest_id, row.get("Guest Name")))
            continue

        social_handles = {}
        for platform, col in [("instagram", "Instagram"), ("tiktok", "Tiktok"),
                               ("facebook", "Facebook"), ("linkedin", "LinkedIn")]:
            v = clean(row.get(col))
            if v:
                social_handles[platform] = v

        # skip rows that are entirely blank aside from the ID/name/episode
        # info that was already there from the RSS-sourced load
        if not any([clean(row.get("City")), clean(row.get("State")),
                    social_handles, clean(row.get("Personal Website"))]):
            skipped_blank += 1
            continue

        conn.execute(
            """UPDATE guests SET
               display_name = COALESCE(?, display_name),
               city = ?, state = ?, country = ?, institution = ?,
               company_website = ?, website_url = ?, social_handles = ?,
               status = ?, bio_notes = COALESCE(?, bio_notes)
               WHERE guest_id = ?""",
            (
                clean(row.get("Guest Name")),
                clean(row.get("City")), clean(row.get("State")), clean(row.get("Country")),
                clean(row.get("Instution/Company")), clean(row.get("Company Website")),
                clean(row.get("Personal Website")),
                json.dumps(social_handles) if social_handles else None,
                clean(row.get("Status")), clean(row.get("Notes")),
                guest_id,
            ),
        )
        matched += 1

    conn.commit()

    print(f"Updated: {matched}")
    print(f"Skipped (blank row, nothing new to merge): {skipped_blank}")
    print(f"Unmatched Guest IDs (not found in guests table -- check for typos): {len(unmatched)}")
    for gid, name in unmatched:
        print(f"  {gid}: {name}")

    total = conn.execute("SELECT COUNT(*) FROM guests").fetchone()[0]
    with_city = conn.execute("SELECT COUNT(*) FROM guests WHERE city IS NOT NULL").fetchone()[0]
    print(f"\nGuests with a city populated: {with_city} of {total}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 merge_guest_sheet.py <tsv_or_csv_file>")
        sys.exit(1)
    delimiter = "\t" if sys.argv[1].endswith(".tsv") else ","
    with open(sys.argv[1], newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        main(list(reader))
