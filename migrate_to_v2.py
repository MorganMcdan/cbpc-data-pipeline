"""
Rebuilds cbpc.db on schema_v2.sql, carrying over episodes/guests/keywords
from the current database and loading the confirmed taxonomy (8 top-level
categories, each with the sub-categories you'd defined -- "Wellness &
Sustainability" kept top-level only, per your call on the duplicate).
"""
import sqlite3
import re

OLD_DB = "cbpc_old.db"
NEW_DB = "cbpc_v2.db"
SCHEMA_PATH = "schema_v2.sql"

# Confirmed taxonomy: top-level -> [sub-categories]. Empty list = no
# sub-categories defined yet (still a valid leaf-level category).
TAXONOMY = {
    "Creative Practice & Arts": [
        "Music", "Film/TV/Media", "Literature", "Gaming",
        "Drawing/Painting/Illustration", "Culinary Arts",
        "Dance/Choreography", "Fashion",
    ],
    "Entrepreneurship & Business": ["Non-profit", "Grants/Funding", "Operations"],
    "Community, Policy & Advocacy": ["Research", "Cultural preservation"],
    "Technology & AI": ["Data"],
    "Career & Life Transitions": [],
    "Media & Platforms": ["Conferences", "Digital Platforms", "Content Creators"],
    "Wellness & Sustainability": ["Navigating Disability", "Mental Health"],
    "Education & Mentorship": ["Higher Education", "Students"],
}

BOUNDARY_ONLY = {"ai", "art", "tv", "dj"}

# trigger substrings per category/sub-category name, reused from the tested pass
TRIGGERS = {
    "Creative Practice & Arts": ["art", "arts", "artist", "artistic", "artwork", "music", "film",
        "theatre", "theater", "dance", "illustrat", "poetry", "comedy", "design", "animat",
        "photograph", "puppet", "costume", "choreograph", "voice", "sketch", "filmmak",
        "composition", "creative", "storytelling", "visual", "documentary"],
    "Music": ["music", "dj", "opera", "song", "band", "concert", "synth"],
    "Film/TV/Media": ["film", "tv", "cinema", "movie", "documentary", "screening"],
    "Literature": ["poetry", "book", "publish", "literary", "writing", "author"],
    "Gaming": ["gaming", "esports", "video game", "robotics"],
    "Drawing/Painting/Illustration": ["illustrat", "painting", "drawing", "mural", "visual art"],
    "Culinary Arts": ["culinary", "chef", "dining", "food"],
    "Dance/Choreography": ["dance", "choreograph"],
    "Fashion": ["fashion", "costume", "textile"],

    "Entrepreneurship & Business": ["entrepreneur", "business", "monetiz", "marketing", "branding",
        "brand ", "strategy", "strategic", "startup", "small business", "solo entrepreneur",
        "fashion manufacturing", "culinary entrepreneurship", "quantum wealth", "pricing",
        "authenticity in business", "operations"],
    "Non-profit": ["nonprofit", "non-profit"],
    "Grants/Funding": ["grant", "funding", "fundraising", "fiscal sponsorship", "philanthrop"],
    "Operations": ["operations", "workflow", "business systems"],

    "Community, Policy & Advocacy": ["communit", "advocacy", "coalition", "nonprofit", "policy",
        "funding", "equity", "diversity", "grant", "fellowship", "philanthrop", "government",
        "tax-deductible", "fiscal sponsorship", "representation", "activis", "board of directors",
        "social justice", "social change"],
    "Research": ["research", "data analysis", "demographic"],
    "Cultural preservation": ["cultural preservation", "traditional ecological", "heritage",
        "indigenous", "lakota"],

    "Technology & AI": ["ai", "artificial intelligence", "tech", "digital", "data", "blockchain",
        "software", "robotics", "gaming", "esports", "synthesizer", "open source", "hacker",
        "video game", "deepfake", "agentic", "generative", "media ownership", "media database",
        "web design", "app"],
    "Data": ["data"],

    "Career & Life Transitions": ["career", "transition", "portfolio career", "job search",
        "growth mindset", "overcoming adversity", "industry evolution", "industry transitions",
        "reinvention", "side project"],

    "Media & Platforms": ["podcast", "streaming", "newsletter", "publish", "sms marketing",
        "email marketing", "media industry", "audio storytelling", "content creation",
        "content monetization"],
    "Conferences": ["conference", "sxsw", "south by southwest", "summit"],
    "Digital Platforms": ["platform", "streaming", "newsletter", "app"],
    "Content Creators": ["content creator", "creator economy", "influencer"],

    "Wellness & Sustainability": ["mental health", "sobriety", "addiction", "wellness",
        "self-care", "sustainab", "circular economy", "renewable energy", "mushroom", "fungi",
        "adhd", "anxiety", "depression", "holiday stress", "wellbeing", "burnout"],
    "Navigating Disability": ["disability"],
    "Mental Health": ["mental health", "anxiety", "depression", "adhd", "addiction", "sobriety"],

    "Education & Mentorship": ["education", "mentorship", "training", "learning", "student",
        "collegiate", "academy", "alumni", "arts education"],
    "Higher Education": ["college", "university", "scad", "higher education"],
    "Students": ["student"],
}


def kw_matches(keyword_lower, trigger):
    if trigger in BOUNDARY_ONLY:
        return re.search(r"\b" + re.escape(trigger) + r"\b", keyword_lower) is not None
    return trigger in keyword_lower


def main():
    old = sqlite3.connect(OLD_DB)
    old.row_factory = sqlite3.Row

    new = sqlite3.connect(NEW_DB)
    new.executescript(open(SCHEMA_PATH).read())

    # --- carry over episodes ---
    for ep in old.execute("SELECT * FROM episodes"):
        new.execute(
            """INSERT INTO episodes (guid, title, pub_date, season, episode_number,
               description, megaphone_audio_url, spotify_url, duration_sec,
               last_synced_at, manually_reviewed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ep["guid"], ep["title"], ep["pub_date"], ep["season"], ep["episode_number"],
             ep["description"], ep["megaphone_audio_url"], ep["spotify_url"],
             ep["duration_sec"], ep["last_synced_at"], ep["manually_reviewed"]),
        )

    # --- carry over guests ---
    for g in old.execute("SELECT * FROM guests"):
        new.execute(
            """INSERT INTO guests (guest_id, display_name, normalized_name, category,
               bio_notes, website_url, social_handles)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (g["guest_id"], g["display_name"], g["normalized_name"], g["category"],
             g["bio_notes"], g["website_url"], g["social_handles"]),
        )

    # --- carry over episode_guests ---
    for row in old.execute("SELECT * FROM episode_guests"):
        new.execute(
            "INSERT INTO episode_guests (episode_guid, guest_id) VALUES (?, ?)",
            (row["episode_guid"], row["guest_id"]),
        )

    # --- carry over keywords (source unknown until backfilled) ---
    for row in old.execute("SELECT * FROM episode_keywords"):
        new.execute(
            "INSERT INTO episode_keywords (episode_guid, keyword, source) VALUES (?, ?, 'unknown')",
            (row["episode_guid"], row["keyword"]),
        )

    # --- load taxonomy ---
    category_ids = {}
    for parent_name, subs in TAXONOMY.items():
        cur = new.execute(
            "INSERT INTO categories (name, parent_category_id) VALUES (?, NULL)",
            (parent_name,),
        )
        parent_id = cur.lastrowid
        category_ids[parent_name] = parent_id
        for sub_name in subs:
            cur = new.execute(
                "INSERT INTO categories (name, parent_category_id) VALUES (?, ?)",
                (sub_name, parent_id),
            )
            category_ids[sub_name] = cur.lastrowid

    # --- populate keyword_category_map: match every keyword against every
    #     category/sub-category name that has trigger rules ---
    keywords = [r[0] for r in new.execute("SELECT DISTINCT keyword FROM episode_keywords")]
    for kw in keywords:
        kw_lower = kw.lower()
        for cat_name, triggers in TRIGGERS.items():
            if cat_name not in category_ids:
                continue
            if any(kw_matches(kw_lower, t) for t in triggers):
                new.execute(
                    """INSERT OR IGNORE INTO keyword_category_map
                       (keyword, category_id, match_method) VALUES (?, ?, 'rule_based')""",
                    (kw, category_ids[cat_name]),
                )

    new.commit()

    n_ep = new.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    n_guests = new.execute("SELECT COUNT(*) FROM guests").fetchone()[0]
    n_cats = new.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    n_map = new.execute("SELECT COUNT(*) FROM keyword_category_map").fetchone()[0]
    print(f"Migrated: {n_ep} episodes, {n_guests} guests, {n_cats} categories "
          f"({len(TAXONOMY)} top-level), {n_map} keyword-category links")
    new.close()
    old.close()


if __name__ == "__main__":
    main()
