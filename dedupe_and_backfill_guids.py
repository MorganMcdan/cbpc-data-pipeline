"""
Diagnoses and (optionally) fixes the guid-mismatch issue: the original
database was seeded with each episode's Megaphone AUDIO URL standing in as
its `guid`, but sync_rss.py upserts against the real RSS <guid> field.
If those differ, every scheduled sync inserts duplicate rows instead of
updating the existing ones.

DEFAULT MODE IS DRY RUN. It only prints what it would do. Re-run with
--apply to actually make changes. This is deliberate -- merging/deleting
episode rows is destructive, and the matching logic below (by title +
pub_date) could theoretically mis-pair two different episodes that happen
to share both, so the plan should be eyeballed before --apply is used.

Usage:
    python3 dedupe_and_backfill_guids.py            # dry run, just reports
    python3 dedupe_and_backfill_guids.py --apply    # actually applies the fix
"""
import sqlite3
import sys

DB_PATH = "cbpc.db"


def find_duplicate_pairs(conn):
    """
    Groups episodes by (title, pub_date). Any group with more than one row
    is a probable duplicate caused by the guid mismatch.
    """
    groups = {}
    for row in conn.execute("SELECT guid, title, pub_date, description, spotify_url, "
                             "manually_reviewed, last_synced_at FROM episodes"):
        key = (row[1], row[2])
        groups.setdefault(key, []).append({
            "guid": row[0], "title": row[1], "pub_date": row[2],
            "description": row[3], "spotify_url": row[4],
            "manually_reviewed": row[5], "last_synced_at": row[6],
        })
    return {k: v for k, v in groups.items() if len(v) > 1}


def choose_canonical(rows):
    """
    Of a duplicate group, prefer the row that has a populated description
    (a sign it came from a real sync_rss.py fetch with the correct feed
    guid) over the original seed row. If neither has a description, keep
    whichever was synced most recently.
    """
    with_desc = [r for r in rows if r["description"]]
    if with_desc:
        return with_desc[0]
    return sorted(rows, key=lambda r: r["last_synced_at"] or "", reverse=True)[0]


def main():
    apply_changes = "--apply" in sys.argv
    conn = sqlite3.connect(DB_PATH)

    total_before = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    dupes = find_duplicate_pairs(conn)

    print(f"Total episode rows: {total_before}")
    print(f"Duplicate groups found: {len(dupes)}")
    if not dupes:
        print("No duplicates detected -- guids are consistent. Nothing to do.")
        return

    print()
    print(f"{'MODE: DRY RUN (add --apply to execute)' if not apply_changes else 'MODE: APPLYING CHANGES'}")
    print()

    for (title, pub_date), rows in dupes.items():
        canonical = choose_canonical(rows)
        losers = [r for r in rows if r["guid"] != canonical["guid"]]
        print(f"'{title}' ({pub_date}): {len(rows)} rows -> keeping guid {canonical['guid'][:50]}...")
        for loser in losers:
            print(f"    merging from: {loser['guid'][:50]}...")

        if apply_changes:
            # carry forward curated fields from the loser row(s) if the
            # canonical row doesn't already have them
            for loser in losers:
                conn.execute(
                    """UPDATE episodes SET
                       spotify_url = COALESCE(spotify_url, ?),
                       manually_reviewed = MAX(manually_reviewed, ?)
                       WHERE guid = ?""",
                    (loser["spotify_url"], loser["manually_reviewed"], canonical["guid"]),
                )
                # repoint foreign keys before deleting the loser row
                conn.execute(
                    "UPDATE OR IGNORE episode_guests SET episode_guid = ? WHERE episode_guid = ?",
                    (canonical["guid"], loser["guid"]),
                )
                conn.execute(
                    "DELETE FROM episode_guests WHERE episode_guid = ?", (loser["guid"],)
                )  # cleans up any that couldn't be repointed due to a unique constraint clash
                conn.execute(
                    "UPDATE OR IGNORE episode_keywords SET episode_guid = ? WHERE episode_guid = ?",
                    (canonical["guid"], loser["guid"]),
                )
                conn.execute(
                    "DELETE FROM episode_keywords WHERE episode_guid = ?", (loser["guid"],)
                )
                conn.execute("DELETE FROM episodes WHERE guid = ?", (loser["guid"],))

    if apply_changes:
        conn.commit()
        total_after = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        print()
        print(f"Done. Episode count: {total_before} -> {total_after}")
    else:
        print()
        print("Dry run complete. Re-run with --apply to execute the above plan.")


if __name__ == "__main__":
    main()
