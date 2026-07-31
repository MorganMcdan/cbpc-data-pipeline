"""
Recurring sync job. Run this on a schedule (cron / GitHub Action / Airflow)
against the live Megaphone feed to pick up new episodes.

Design principles:
1. Upsert by <guid>, not by title -- titles can be edited after publish,
   guids are stable.
2. Only feed-sourced fields get overwritten on conflict. Curated fields
   (spotify_url, guest.category, theme tags, manually_reviewed) are
   preserved across syncs -- see the ON CONFLICT clause.
3. New episodes land with manually_reviewed = 0, so a human (or a
   downstream LLM enrichment step) knows which rows still need:
     - guest category confirmation
     - Spotify episode URL
     - theme tagging from transcript
4. New guest names are inserted with category = NULL until reviewed --
   the guest map build step should skip/flag ungrouped guests rather
   than silently defaulting them to a category.

Usage:
    pip install feedparser --break-system-packages
    python3 sync_rss.py https://feeds.megaphone.fm/UUCUL7390370337
"""
import sys
import sqlite3
import re
from datetime import datetime, timezone

DB_PATH = "cbpc.db"


def normalize_name(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n)
    return n


def upsert_episode(conn, guid, title, pub_date, season, episode_number,
                    description, audio_url):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO episodes (guid, title, pub_date, season, episode_number,
                               description, megaphone_audio_url,
                               last_synced_at, manually_reviewed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(guid) DO UPDATE SET
            title=excluded.title,
            pub_date=excluded.pub_date,
            season=excluded.season,
            episode_number=excluded.episode_number,
            description=excluded.description,
            megaphone_audio_url=excluded.megaphone_audio_url,
            last_synced_at=excluded.last_synced_at
            -- NOTE: spotify_url, manually_reviewed intentionally untouched
        """,
        (guid, title, pub_date, season, episode_number, description,
         audio_url, now),
    )


def upsert_guest(conn, display_name):
    norm = normalize_name(display_name)
    conn.execute(
        """
        INSERT INTO guests (display_name, normalized_name)
        VALUES (?, ?)
        ON CONFLICT(normalized_name) DO NOTHING
        """,
        (display_name, norm),
    )
    return conn.execute(
        "SELECT guest_id FROM guests WHERE normalized_name = ?", (norm,)
    ).fetchone()[0]


def link_guest(conn, episode_guid, guest_id):
    conn.execute(
        "INSERT OR IGNORE INTO episode_guests (episode_guid, guest_id) VALUES (?, ?)",
        (episode_guid, guest_id),
    )


def sync(feed_url):
    import feedparser  # pip install feedparser --break-system-packages

    conn = sqlite3.connect(DB_PATH)
    feed = feedparser.parse(feed_url)

    new_count = 0
    for entry in feed.entries:
        guid = entry.get("id") or entry.get("link")
        existing = conn.execute(
            "SELECT 1 FROM episodes WHERE guid = ?", (guid,)
        ).fetchone()
        if not existing:
            new_count += 1

        season = getattr(entry, "itunes_season", None)
        episode_number = getattr(entry, "itunes_episode", None)
        audio_url = entry.enclosures[0]["href"] if entry.enclosures else None

        upsert_episode(
            conn, guid, entry.title, entry.published, season,
            episode_number, entry.get("summary", ""), audio_url,
        )
        # NOTE: guest name extraction from description text needs a parser
        # (regex on "Featured Guest:" blocks, or an LLM call) -- the feed
        # doesn't tag guests in structured fields. Plug that in here, then:
        #   for name in extracted_guest_names:
        #       gid = upsert_guest(conn, name)
        #       link_guest(conn, guid, gid)

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    print(f"Sync complete: {new_count} new episode(s), {total} total in DB.")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 sync_rss.py <feed_url>")
        sys.exit(1)
    sync(sys.argv[1])
