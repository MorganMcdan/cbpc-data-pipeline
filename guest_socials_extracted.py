"""
Guest website/social data extracted directly from the "Connect with..."
sections of the episode descriptions pasted earlier in this conversation --
not web-searched, not guessed. Only guests where the show notes explicitly
gave a URL or handle are included here; everyone else needs a manual look
or a future automated re-extraction once episode descriptions are properly
stored in the database (see note at bottom of this file).

Format: normalized_name -> {"website": ..., "social_handles": {...}}
Normalization matches guests.normalized_name in cbpc.db (lowercase,
punctuation stripped) so this can be joined directly against that table.
"""

GUEST_SOCIALS = {
    "hogan shrum": {"website": "gopippa.ai"},
    "greg hemmings": {"website": "hemmingshouse.com", "also": "hemmingsfilms.com",
                       "social_handles": {"youtube": "Greg Hemmings Official"}},
    "rakia seaborn": {"website": "group36.org"},
    "djmichelle": {"social_handles": {"instagram": "@DJMichelleB2.4Productions",
                                       "facebook": "@DJMichelleB2.4Productions",
                                       "tiktok": "@DJMichelleB2.4Productions"},
                   "contact_email": "djmichelleb2.4productions@gmail.com"},
    "morris robinson": {"website": "morrisrobinson.com", "social_handles": {"instagram": "@mdrbass"}},
    "aj carolyn": {"website": "ajcarolyn.com", "social_handles": {"instagram": "@starryfawns"}},
    "calida jones": {"website": "creativeevolutions.com", "also": "momentumrevolutions.com",
                      "social_handles": {"instagram": "@creativeevolutionsecosystem"}},
    "douglas clayton": {"website": "creativeevolutions.com"},
    "anthony frasier": {"website": "abfc.co", "social_handles": {"instagram": "@AnthonyFrasier"}},
    "lauren knabel": {"website": "laurenknable.com", "social_handles": {"instagram": "@laurenknable"}},
    "eric renzwhitmore": {"social_handles": {"linkedin": "linkedin.com/in/ewhitmore"}},
    "kristelle siarza moon": {"social_handles": {"linkedin": "linkedin.com/in/kristellesiarza"}},
    "aseloka smith": {"website": "aaainfo.link/cbpc",
                       "social_handles": {"linkedin": "linkedin.com/in/aseloka-smith-55820436"}},
    "brian reitz": {"social_handles": {"linkedin": "linkedin.com/in/brianmreitz"}},
    "joao baptista": {"website": "iftomorrow.institute",
                       "social_handles": {"linkedin": "linkedin.com/in/joaobaptistafuture",
                                           "instagram": "@joaobaptistafuture"}},
    "laura hennighausen": {"website": "artscapitalatlanta.org"},
    "jasmine bianca": {"website": "jbientertainment.com", "social_handles": {"instagram": "@JaBiEntertainment"}},
    "danielle desir corbett": {"website": "grantsforcreators.com"},
    "rachel meade smith": {"website": "wordsofmouth.org"},
    "rocco shapiro": {"website": "reelfriendsfilms.com", "social_handles": {"instagram": "@roccoshapiro"}},
    "akshay bhatia": {"website": "reelfriendsfilms.com", "social_handles": {"instagram": "@bokomaru00"}},
    "tim packer": {"website": "timpackerartacademy.com"},
    "david claassen": {"website": "atlantamushroomfestival.com"},
    "paul grzybowski": {"website": "atlantamushroomfestival.com"},
    "maggie": {"social_handles": {"instagram": "@commoncircuitsfestival"}},
    "aaron": {"social_handles": {"instagram": "@commoncircuitsfestival"}},  # Common Circuits Aaron, distinct from Aaron Neal
    "dr anuli akanegbu": {"website": "anuliwashere.com", "social_handles": {"instagram": "@anuliwashere"}},
    "emmolei sankofa": {"website": "e-sankofa.com", "social_handles": {"instagram": "@emmolei"}},
    "john carnwath": {"website": "wolfbrown.com"},
    "tamara stands and looks back-spotted tail": {"website": "lakotawomenbusinessllc.com"},
    "jonelle dawkins": {"social_handles": {"instagram": "@scrapATL", "facebook": "@scrapatlanta", "tiktok": "@scrapatl"}},
    "dani dufresne": {"website": "theauxiliaryco.com", "social_handles": {"linkedin": "linkedin.com/in/danidufresne"}},
    "bill worley": {"website": "coolcoolcoolpro.com", "social_handles": {"instagram": "@worleybirdpictures"}},
    "jazz jackson": {"website": "unearthlystudios.com", "social_handles": {"instagram": "@allthatjazzxx"}},
    "purser": {"website": "pursermusic.com", "social_handles": {"instagram": "@pursermusic"}},
    "nikkia adolphe": {"website": "brandsavor.co"},
    "ekaette kern": {"website": "brandsavor.co"},
    "sasha revolus": {"website": "iamsashar.com", "also": "thisishowisunday.com"},
    "darius evans": {"website": "georgiaproduction.org"},
    "elaine stephenson": {"website": "artsyelaine.com"},
    "zakiya whatley": {"website": "zakiyawhatley.com", "also": "dopelabspodcast.com"},
    "rob greenlee": {"social_handles": {"instagram": "@robwgreenlee"}},
    "jaron johnson": {"social_handles": {"instagram": "@jaronjolt"}},
    "luther ocasio": {"social_handles": {"instagram": "@florapapi_"}},
    "charis sellick": {"social_handles": {"instagram": "@charissellick", "youtube": "youtube.com/@CharisSellick"}},
    "jazmine valencia": {"social_handles": {"instagram": "@jvagency"}},
    "lnre": {"social_handles": {"instagram": "@lanre.official"}},  # Lánre -- accented char normalizes oddly, verify match manually
    "lee ann scotto adams": {"social_handles": {"linkedin": "linkedin.com/in/leeannscottoadams",
                                                  "instagram": "instagram.com/leeannscottoadams"}},
    "b sonenreich": {"website": "atlfilmparty.com",
                      "social_handles": {"linkedin": "linkedin.com/in/brookesonenreich"}},
}

# NOTE ON SCOPE: this covers guests whose episode explicitly included a
# "Connect with..." section with a real URL/handle. A meaningful chunk of
# guests -- especially the pre-2025 "Ep. 1-23" era and anyone in a group
# panel episode -- had no such section in the original show notes at all,
# and are not fabricated here. Those either need direct manual research or
# a wait until `episodes.description` is properly populated in the live db
# (currently it isn't -- see the sync_rss.py guid-mismatch check first)
# so this same extraction logic can run as a repeatable script instead of
# a one-time manual compile.
