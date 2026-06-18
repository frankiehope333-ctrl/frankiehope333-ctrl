"""build_readme.py — the spine.

Concatenates the static section copy (sections/*.md) with the live game boards,
in this exact order (BUILD.md §3b), writing README.md:

    banner -> about -> reef board -> links -> bottle board -> building ->
    creature-intro -> creature board -> dashboard -> adventure(start)

Every handler and the daily cron call this LAST so README.md always reflects the
current state. Boards are either an <img> pointing at a committed GIF, or an
inline HTML/markdown block built from the JSON state files.

  NEVER hand-edit README.md — edit the sections or this script and re-run.
"""

from __future__ import annotations

import json
import os
import urllib.parse
from datetime import datetime, timezone

import config

ROOT = os.path.dirname(os.path.abspath(__file__))
SECTIONS = os.path.join(ROOT, "sections")
STATE = os.path.join(ROOT, "state")
SCRAPBOOK = os.path.join(ROOT, "scrapbook")

SCRAPBOOK_URL = "scrapbook/SCRAPBOOK.md"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _read(path: str, default: str = "") -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().rstrip() + "\n"
    except FileNotFoundError:
        return default


def _load_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def section(name: str) -> str:
    return _read(os.path.join(SECTIONS, name))


def issue_url(title: str, body: str = "") -> str:
    """Pre-filled 'new issue' link. The shared mechanic (PROFILE-SPEC §SHARED).

    e.g. issue_url("bottle|add", "...") ->
      https://github.com/{user}/{user}/issues/new?title=...&body=...
    """
    base = f"https://github.com/{config.REPO}/issues/new"
    q = {"title": title}
    if body:
        q["body"] = body
    return base + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)


def _fmt_when(when: str) -> str:
    """'2026-06-17' / ISO -> a friendly relative-ish stamp. Best-effort."""
    return (when or "").split("T")[0]


# ---------------------------------------------------------------------------
# boards
# ---------------------------------------------------------------------------
def reef_board() -> str:
    reef = _load_json(os.path.join(STATE, "reef.json"), {})
    archive = _load_json(os.path.join(SCRAPBOOK, "reefs_archive.json"), {"total_reefs": 0})
    reef_no = archive.get("total_reefs", 0) + 1
    last = _fmt_when(reef.get("last_synced", "")) or "—"
    gif = "render/reef.gif"
    has_gif = os.path.exists(os.path.join(ROOT, gif))

    img = (f'<img src="{gif}" alt="frankie\'s reef — a pixel-art sunset lagoon that '
           f'grows with my commits" width="560">') if has_gif else _placeholder(
        "🪸 frankie's reef &lt;3", "reef.gif renders on the next daily tide")

    past = ""
    if archive.get("total_reefs", 0) > 0:
        past = f' · [see past reefs 📖]({SCRAPBOOK_URL}#reefs)'
    return (
        "## 🪸 the reef\n\n"
        f"{img}\n\n"
        f"🪸 *This reef grows when I ship. Last tide: {last} · this is reef #{reef_no}.*"
        f"{past}\n"
    )


def bottle_board() -> str:
    data = _load_json(os.path.join(STATE, "bottles.json"), {"bottles": []})
    archive = _load_json(os.path.join(SCRAPBOOK, "bottles_archive.json"), {"total_ever": 0})
    total = archive.get("total_ever", 0)
    bottles = data.get("bottles", [])[: config.BOTTLE_DISPLAY]

    gif = "render/bottle_bob.gif"
    has_gif = os.path.exists(os.path.join(ROOT, gif))
    bob = (f'<img src="{gif}" alt="a pixel bottle bobbing in the sea" width="64" '
           f'align="left">') if has_gif else "🫧"

    toss = issue_url(
        "bottle|add",
        "Write your one-line message below this line (~80 chars), then submit. "
        "It'll bob onto Frankie's profile.\n\n",
    )

    # Header row: bobbing GIF + running total (NO 🍾 emoji in the count text —
    # the GIF bottle IS the bottle). PROFILE-SPEC §GAME 2.
    out = ["## 🍾 message in a bottle\n"]
    out.append(
        '<table><tr>'
        f'<td width="72">{bob}</td>'
        f'<td><b>{total} bottles tossed into the sea so far</b><br>'
        f'<a href="{toss}">🍾 Toss a bottle into the sea</a> · '
        f'<a href="{SCRAPBOOK_URL}">open the scrapbook 📖</a></td>'
        '</tr></table>\n'
    )

    if not bottles:
        out.append("\n> 🌊 *The sea is calm. Be the first to toss a bottle.*\n")
    else:
        # Older ones "drift" — fade with a different glyph deeper down the list.
        glyphs = ["🍾", "🫧", "🌫️"]
        for i, b in enumerate(bottles):
            g = glyphs[min(i // 4, len(glyphs) - 1)]
            who = b.get("from", "someone")
            when = _fmt_when(b.get("when", ""))
            msg = b.get("msg", "")
            out.append(f"> {g} *\"{msg}\"* — @{who}, {when}\n")
    return "".join(out) + "\n"


def creature_board() -> str:
    creature = _load_json(os.path.join(STATE, "creature.json"), {})
    archive = _load_json(os.path.join(SCRAPBOOK, "creatures_archive.json"),
                         {"total_finished": 0})
    rnd = creature.get("round", config.CREATURE_ROUNDS[0])
    round_idx = (config.CREATURE_ROUNDS.index(rnd) + 1) if rnd in config.CREATURE_ROUNDS else 1
    n_rounds = len(config.CREATURE_ROUNDS)

    gif = "render/creature.gif"
    has_gif = os.path.exists(os.path.join(ROOT, gif))
    img = (f'<img src="{gif}" alt="the community-built sea creature, in progress" '
           f'width="360">') if has_gif else _placeholder(
        "🐠 creature lab &lt;3", "creature.gif renders after the first vote")

    # vote links for the current round
    votes = creature.get("features", {}).get(rnd, {}).get("votes", {})
    options = config.CREATURE_OPTIONS.get(rnd, [])
    lead = max(votes, key=votes.get) if votes else None
    links = []
    for opt in options:
        n = votes.get(opt, 0)
        url = issue_url(f"creature|vote|{rnd}|{opt}")
        tag = " ·lead" if opt == lead and n > 0 else ""
        links.append(f"[🗳️ {opt} — {n} votes{tag}]({url})")

    finished = archive.get("total_finished", 0)
    sb = (f"🐠 {finished} creatures finished · [see the menagerie 📖]"
          f"({SCRAPBOOK_URL}#creatures)") if finished else \
         f"🐠 [the menagerie 📖]({SCRAPBOOK_URL}#creatures) fills up as creatures finish"

    return (
        "## 🐠 community creature\n\n"
        f"{img}\n\n"
        f"**This round we're picking the `{rnd}`** (round {round_idx} of {n_rounds}). "
        "Vote one feature per visit:\n\n"
        + " · ".join(links) + "\n\n"
        f"{sb}\n"
    )


def _placeholder(title: str, note: str) -> str:
    """Graceful inline placeholder so the README never looks broken mid-build
    (BUILD.md §7). Renders as a small framed note."""
    return (
        '<table width="560"><tr>'
        f'<td align="center" style="padding:18px">'
        f'<b>{title}</b><br><sub>🎨 {note}</sub>'
        '</td></tr></table>'
    )


# ---------------------------------------------------------------------------
# assemble
# ---------------------------------------------------------------------------
def build() -> str:
    parts = [
        section("00-banner.md"),
        section("01-about.md"),
        reef_board(),
        section("02-links.md"),
        bottle_board(),
        section("03-building.md"),
        section("04-creature-intro.md"),
        creature_board(),
        section("05-dashboard.md"),
        section("adventure/start.md"),
    ]
    body = "\n---\n\n".join(p.strip() + "\n" for p in parts if p.strip())
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    footer = (
        "\n---\n\n"
        f"<sub>🌊 This profile is alive — the reef grows from my commits, the bottle "
        f"wall and creature are built by visitors like you. Last assembled {stamp} UTC · "
        f"generated by <code>build_readme.py</code>, never hand-edited.</sub>\n"
    )
    return body + footer


def main() -> None:
    readme = build()
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)
    print(f"wrote README.md ({len(readme)} chars)")


if __name__ == "__main__":
    main()
