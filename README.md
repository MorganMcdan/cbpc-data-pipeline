# Could Be Pretty Cool — Data Pipeline

Source-of-truth database and sync scripts behind the CBPC episode timeline
and guest map. Built from the show's Megaphone RSS feed:
`https://feeds.megaphone.fm/UUCUL7390370337`

## What's in here

| File | Purpose |
|---|---|
| `cbpc.db` | The live SQLite database — episodes, guests, keywords, and the category taxonomy. This is the actual source of truth; edit it directly for manual curation (Spotify links, guest categories, confirmed themes). |
| `schema.sql` | Full schema definition, including the self-referencing `categories` table (supports arbitrary nesting: category → sub-category → sub-sub-category, etc.) |
| `migrate_to_v2.py` | One-time migration script that built the current schema and loaded the confirmed taxonomy. Only needed again if the schema changes. |
| `sync_rss.py` | Run this to pull new episodes from the live feed. Upserts by episode `guid` — never overwrites curated fields (`spotify_url`, guest `category`, `manually_reviewed`). Runs automatically via GitHub Actions (see below), or manually: `python sync_rss.py <feed_url>` |
| `export_static.py` | Regenerates `cbpc_export.json` — the flat JSON snapshot that the timeline/guest-map HTML embeds actually read. Run this after any manual edit to `cbpc.db` that should show up on the live site. |
| `.github/workflows/sync.yml` | Scheduled GitHub Action — runs `sync_rss.py` + `export_static.py` automatically and commits the result. |

## How the automated sync works

Every Wednesday (adjustable in `sync.yml`), GitHub runs `sync_rss.py`
against the live feed, checks for new episodes, and commits the updated
`cbpc.db` + `cbpc_export.json` back to this repo automatically. No manual
re-pasting of the feed required going forward.

**What it does NOT do automatically:**
- Extract new guest names from episode descriptions (the feed doesn't tag
  guests in a structured field — see the `TODO` in `sync_rss.py`)
- Categorize new keywords against the taxonomy
- Populate guest location, socials, or Spotify links

Those still need a manual pass (or a follow-up script) after new episodes
land — new rows get inserted with `manually_reviewed = 0` specifically so
they're easy to find:

```sql
SELECT title FROM episodes WHERE manually_reviewed = 0;
```

## Local setup

```bash
pip install -r requirements.txt
python sync_rss.py https://feeds.megaphone.fm/UUCUL7390370337
python export_static.py
```

## Data provenance note

Episode keywords sourced before the Season 2 relaunch (roughly episodes
1–23) didn't have an explicit `Keywords:` line in the original RSS
description — those were paraphrased from the episode description text
rather than lifted verbatim. See `episode_keywords.source` for the flag
once backfilled; currently most rows are `'unknown'` pending that cleanup.

## Privacy

The guest data (names, socials, contact info, city/state) is sourced from
what guests themselves shared publicly in episode show notes, and is
treated as public information — the guest map is deployed publicly on
Vercel, serving `cbpc_guest_map.html` directly (see `vercel.json`).
