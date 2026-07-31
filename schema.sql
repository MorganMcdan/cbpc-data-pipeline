-- CBPC Data Schema (v2) -- sourced from the Megaphone RSS feed,
-- extended with a self-referencing taxonomy for keyword categorization.

-- ============================================================
-- CORE: episodes, guests, and the RSS-sourced join/keyword data
-- ============================================================

CREATE TABLE IF NOT EXISTS episodes (
    guid                TEXT PRIMARY KEY,      -- stable id from RSS <guid>
    title               TEXT NOT NULL,
    pub_date            TEXT NOT NULL,         -- ISO 8601
    season              INTEGER,
    episode_number      INTEGER,
    description         TEXT,
    megaphone_audio_url TEXT,
    spotify_url         TEXT,                  -- curated manually; RSS sync never overwrites
    duration_sec        INTEGER,
    last_synced_at      TEXT,                  -- last time the RSS sync job touched this row
    manually_reviewed   INTEGER DEFAULT 0      -- 0/1: has a human confirmed guests/themes for this episode?
);

CREATE TABLE IF NOT EXISTS guests (
    guest_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name    TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,      -- lowercased/punctuation-stripped, for dedup
    category        TEXT,                      -- guest-map category (Founder/Entrepreneur, Artist/Creative, etc.)
    city            TEXT,                      -- for the geographic dot map -- currently unpopulated
    state           TEXT,
    lat             REAL,
    lon             REAL,
    bio_notes       TEXT,
    website_url     TEXT,
    social_handles  TEXT                       -- JSON blob, e.g. {"instagram": "...", "linkedin": "..."}
);

CREATE TABLE IF NOT EXISTS episode_guests (
    episode_guid    TEXT NOT NULL REFERENCES episodes(guid),
    guest_id        INTEGER NOT NULL REFERENCES guests(guest_id),
    PRIMARY KEY (episode_guid, guest_id)
);

-- Raw keyword tags as they appear (or are inferred) from the RSS description.
-- source distinguishes keywords the feed itself tagged vs. ones inferred by
-- reading the description text, since not every episode has an explicit
-- "Keywords:" line -- see build notes from the keyword review workbook.
CREATE TABLE IF NOT EXISTS episode_keywords (
    episode_guid    TEXT NOT NULL REFERENCES episodes(guid),
    keyword         TEXT NOT NULL,
    source          TEXT DEFAULT 'unknown',    -- 'feed_verbatim' | 'inferred' | 'unknown'
    PRIMARY KEY (episode_guid, keyword)
);

-- ============================================================
-- TAXONOMY: self-referencing so it supports arbitrary nesting
-- (top-level category -> sub-category -> sub-sub-category, etc.)
-- without ever needing another schema migration.
-- ============================================================

CREATE TABLE IF NOT EXISTS categories (
    category_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    parent_category_id  INTEGER REFERENCES categories(category_id),  -- NULL = top-level
    description         TEXT,
    UNIQUE(name, parent_category_id)           -- allows same sub-category name under different parents if ever needed
);

-- Every keyword can map to one or more categories/sub-categories.
-- match_method records how the link was made, so rule-based matches stay
-- distinguishable from manual corrections or a later embedding-based pass.
CREATE TABLE IF NOT EXISTS keyword_category_map (
    keyword         TEXT NOT NULL,
    category_id     INTEGER NOT NULL REFERENCES categories(category_id),
    match_method    TEXT DEFAULT 'rule_based', -- 'rule_based' | 'manual' | 'embedding_cluster'
    PRIMARY KEY (keyword, category_id)
);

-- ============================================================
-- THEMES: the host-defined narrative arcs (separate from the
-- keyword taxonomy above -- themes are qualitative/editorial,
-- not derived from keyword frequency)
-- ============================================================

CREATE TABLE IF NOT EXISTS themes (
    theme_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_name          TEXT NOT NULL UNIQUE,   -- e.g. "The First Dollar"
    theme_description   TEXT,
    confirmed_by_host   INTEGER DEFAULT 0       -- 0/1
);

CREATE TABLE IF NOT EXISTS episode_themes (
    episode_guid    TEXT NOT NULL REFERENCES episodes(guid),
    theme_id        INTEGER NOT NULL REFERENCES themes(theme_id),
    confidence      REAL,
    source          TEXT,                       -- 'manual' | 'llm_transcript' | 'keyword_heuristic'
    PRIMARY KEY (episode_guid, theme_id)
);

-- ============================================================
-- Helpful views
-- ============================================================

-- Every keyword with its full category path, e.g. "Creative Practice & Arts > Music"
CREATE VIEW IF NOT EXISTS v_keyword_full_path AS
SELECT
    kcm.keyword,
    c.category_id,
    c.name AS category_name,
    parent.name AS parent_category_name,
    CASE WHEN parent.name IS NOT NULL
         THEN parent.name || ' > ' || c.name
         ELSE c.name
    END AS full_path
FROM keyword_category_map kcm
JOIN categories c ON c.category_id = kcm.category_id
LEFT JOIN categories parent ON parent.category_id = c.parent_category_id;
