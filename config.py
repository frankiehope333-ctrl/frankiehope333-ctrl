# config.py — single source of truth for all tunable values.
# Everything (renderers, handlers, workflows-via-handlers) imports from here so
# behavior can be changed in ONE place without touching logic. See BUILD.md §1.

# ---- Reef ----------------------------------------------------------------
REEF_CAP = 40                 # snapshot + reset when the reef exceeds this many items
REEF_CRON = "0 6 * * *"       # daily 06:00 UTC contribution sync (mirrored in tides.yml)
REEF_MAP = {                  # contributions today -> what spawns
    "fish":  (1, 3),          # 1–3 contributions -> 1 fish
    "coral": (4, 8),          # 4–8 -> a coral cluster
    "kelp":  (9, 999),        # 9+ -> a kelp stalk
}
REEF_MONTH_END_SNAPSHOT = True   # also snapshot on the 1st (cap OR month-end)

# ---- Bottle --------------------------------------------------------------
BOTTLE_DISPLAY = 10           # how many bottles show on the live board
BOTTLE_MAXLEN = 80            # chars per message, one line
# "auto"   = blocklist filter only, post immediately if it passes
# "manual" = hold as `pending` until the owner adds the `approved` label
# Ship on "manual" for the first ~2 weeks, then flip to "auto" (BUILD.md §1 note).
BOTTLE_MODERATION = "manual"

# ---- Creature ------------------------------------------------------------
CREATURE_ROUNDS = ["body", "tail", "color", "eyes", "accessory"]
CREATURE_VOTE_THRESHOLD = 10  # votes to lock a round and advance
CREATURE_ONE_VOTE_PER_USER_PER_ROUND = True

# Per-round options the community votes between. Keep 3–4 each; these strings are
# what the renderer and the pre-filled issue links use, so keep them stable.
CREATURE_OPTIONS = {
    "body":      ["seahorse", "jellyfish", "eel"],
    "tail":      ["flowing", "fan", "spiked"],
    "color":     ["coral-pink", "peach-glow", "orchid"],
    "eyes":      ["sparkle", "dot", "sleepy"],
    "accessory": ["pearl-crown", "shell-clip", "bubble-ring"],
}

# ---- General -------------------------------------------------------------
TZ = "America/Chicago"        # owner's local time, used for date stamps

# ---- Identity (used to build links + GraphQL query) ----------------------
GH_USER = "frankiehope333-ctrl"   # the special profile repo is {user}/{user}
REPO = f"{GH_USER}/{GH_USER}"
