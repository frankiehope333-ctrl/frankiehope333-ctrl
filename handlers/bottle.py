"""handlers/bottle.py — message-in-a-bottle guestbook (PROFILE-SPEC GAME 2).

Triggered by issues whose title starts with `bottle|`. This is the riskiest game
because it publishes stranger text onto a founder profile, so input is sanitized
HARD before it ever touches the README (BUILD.md §6, SPEC Safety note).

Flow:
  - moderation == "manual" (default): on first open, label the issue `pending`,
    comment, and stop. Nothing publishes until the owner adds the `approved`
    label, which re-triggers this handler.
  - moderation == "auto": publish immediately if it passes the blocklist.
  - On publish: archive FIRST (running total + sequence #n, nothing ever lost),
    then prepend to the 10-item display, rebuild scrapbook + README, close issue.

Local test (no token -> dry-run API):
  FAKE_EVENT='{"issue":{"number":1,"title":"bottle|add","body":"hi from texas",
  "user":{"login":"octocat"},"labels":[]},"action":"opened"}' python handlers/bottle.py
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "render"))
sys.path.insert(0, os.path.join(ROOT, "handlers"))

import config            # noqa: E402
import build_readme      # noqa: E402
import scrapbook         # noqa: E402
import _gh as gh         # noqa: E402

STATE = os.path.join(ROOT, "state", "bottles.json")
ARCHIVE = os.path.join(ROOT, "scrapbook", "bottles_archive.json")

PENDING_LABEL = "pending"
APPROVED_LABEL = "approved"

# Small cute-ocean emoji whitelist; everything else in the symbol/emoji range is
# stripped. Plain text is allowed; markdown/HTML control chars are removed.
ALLOWED_EMOJI = set("🪸🐚🐠🐟🌊🫧🍾🐬🐙🦀🌙⭐✨💜🧡💖🩷😊🥰👋🌅🐳🐋🌴☀️🌞🐢🪼")
# markdown / HTML control characters we never let through
STRIP_CHARS = set('<>&`\\|*_~[](){}#@')
# keepable punctuation categories + space
_OK_PUNCT = {"Po", "Pd", "Ps", "Pe", "Pi", "Pf", "Pc"}

# A deliberately small blocklist; extend as needed. Word-boundary, case-insensitive.
BLOCKLIST = {
    "fuck", "shit", "bitch", "cunt", "nigger", "faggot", "retard", "rape", "slut",
    "whore", "kike", "spic", "chink",
}


def _import_json():
    import json
    return json


def _load(path, default):
    json = _import_json()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path, data):
    json = _import_json()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def extract_message(body: str) -> str:
    """Pull the user's line out of the issue body, dropping the template prompt."""
    if not body:
        return ""
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if "write your" in s.lower() and "message" in s.lower():
            continue
        return s
    return ""


def sanitize(text: str) -> tuple[str, bool]:
    """Return (clean_text, ok). ok is False if it's empty or trips the blocklist.

    Strips HTML/markdown control chars, URLs, links, mentions, and any emoji
    outside the whitelist. One line, length-capped. SPEC Safety note."""
    text = (text or "").splitlines()[0] if text else ""
    # remove markdown images/links but keep the visible text
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # remove bare URLs
    text = re.sub(r"https?://\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"www\.\S+", "", text, flags=re.IGNORECASE)

    out = []
    for ch in text:
        if ch in ALLOWED_EMOJI:
            out.append(ch)
            continue
        if ch in STRIP_CHARS:
            continue
        if ch in " \t":
            out.append(" ")
            continue
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "N") or cat in _OK_PUNCT:
            out.append(ch)
        # everything else (symbols So/Sk/Sm, other emoji, controls Cc/Cf) dropped

    clean = re.sub(r"\s+", " ", "".join(out)).strip()
    clean = clean[: config.BOTTLE_MAXLEN].strip()

    if not clean:
        return "", False
    words = set(re.findall(r"[a-z]+", clean.lower()))
    if words & BLOCKLIST:
        return clean, False
    return clean, True


def publish(msg: str, author: str) -> int:
    """Archive first (nothing lost), then update the trimmed display. Returns #n."""
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    archive = _load(ARCHIVE, {"total_ever": 0, "bottles": []})
    n = archive.get("total_ever", 0) + 1
    archive["total_ever"] = n
    archive["bottles"].insert(0, {"msg": msg, "from": author, "when": when, "n": n})
    _save(ARCHIVE, archive)

    data = _load(STATE, {"bottles": []})
    data["bottles"].insert(0, {"msg": msg, "from": author, "when": when, "n": n})
    data["bottles"] = data["bottles"][: config.BOTTLE_DISPLAY]
    _save(STATE, data)
    return n


def main() -> None:
    event = gh.load_event()
    issue = event.get("issue", {})
    number = issue.get("number")
    title = issue.get("title", "")
    if not title.startswith("bottle|"):
        print(f"not a bottle issue: {title!r}")
        return
    author = issue.get("user", {}).get("login", "someone")
    approved = gh.issue_has_label(issue, APPROVED_LABEL)

    # Manual moderation: hold until the owner approves.
    if config.BOTTLE_MODERATION == "manual" and not approved:
        gh.add_label(number, PENDING_LABEL)
        gh.comment(number,
                   "🌊 Thanks! Your bottle is held for a quick review and will bob "
                   "onto the profile once it's approved.")
        print(f"held bottle #{number} as pending")
        return

    msg, ok = sanitize(extract_message(issue.get("body", "")))
    if not ok:
        gh.comment(number, "🌫️ Sorry — I couldn't add that one. (It was empty or "
                           "tripped the filter.) Feel free to try another message.")
        gh.close_issue(number)
        print("rejected bottle (empty/blocklist)")
        return

    n = publish(msg, author)
    scrapbook.build_scrapbook()
    build_readme.main()
    gh.comment(number, f"🌊 Your bottle is bobbing on my profile now — that's #{n}. "
                       "Thanks for stopping by. 🐚")
    gh.close_issue(number)
    print(f"published bottle #{n}: {msg!r}")


if __name__ == "__main__":
    main()
