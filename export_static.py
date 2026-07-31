"""
Run this whenever you rebuild the timeline/guest-map HTML artifacts.
Reads from cbpc.db (the live source of truth) and writes a flat JSON
snapshot -- this is the only thing the static HTML/JS embeds ever read.
"""
import json
import sqlite3

DB_PATH = "cbpc.db"
OUT_PATH = "cbpc_export.json"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    episodes = []
    for ep in conn.execute("SELECT * FROM episodes ORDER BY pub_date"):
        guests = conn.execute(
            """
            SELECT g.display_name, g.category, g.guest_id
            FROM guests g
            JOIN episode_guests eg ON eg.guest_id = g.guest_id
            WHERE eg.episode_guid = ?
            """,
            (ep["guid"],),
        ).fetchall()

        themes = conn.execute(
            """
            SELECT t.theme_name, et.source
            FROM themes t
            JOIN episode_themes et ON et.theme_id = t.theme_id
            WHERE et.episode_guid = ?
            """,
            (ep["guid"],),
        ).fetchall()

        episodes.append({
            "guid": ep["guid"],
            "title": ep["title"],
            "pub_date": ep["pub_date"],
            "season": ep["season"],
            "episode_number": ep["episode_number"],
            "spotify_url": ep["spotify_url"],
            "guests": [
                {"name": g["display_name"], "category": g["category"], "id": g["guest_id"]}
                for g in guests
            ],
            "themes": [t["theme_name"] for t in themes],
            "needs_review": not bool(ep["manually_reviewed"]),
        })

    with open(OUT_PATH, "w") as f:
        json.dump(episodes, f, indent=2)

    needs_review = sum(1 for e in episodes if e["needs_review"])
    print(f"Exported {len(episodes)} episodes to {OUT_PATH} "
          f"({needs_review} still flagged needs_review)")


if __name__ == "__main__":
    main()
