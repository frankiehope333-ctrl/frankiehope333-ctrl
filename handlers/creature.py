"""handlers/creature.py — community-built creature, Model A (PROFILE-SPEC GAME 3).

Triggered by issues whose title is `creature|vote|{round}|{option}`. Sequential
rounds (body -> tail -> color -> eyes -> accessory): visitors vote one option per
round, one vote per user per round. At CREATURE_VOTE_THRESHOLD the leader locks,
the round advances. When the final round locks, the finished creature is rendered
to the scrapbook and a fresh one hatches.

Local test (no token -> dry-run API):
  FAKE_EVENT='{"issue":{"number":2,"title":"creature|vote|body|seahorse",
  "user":{"login":"octocat"},"labels":[]},"action":"opened"}' python handlers/creature.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "render"))
sys.path.insert(0, os.path.join(ROOT, "handlers"))

import config            # noqa: E402
import build_readme      # noqa: E402
import scrapbook         # noqa: E402
import creature_gif      # noqa: E402
import _gh as gh         # noqa: E402

STATE = os.path.join(ROOT, "state", "creature.json")
ARCHIVE = os.path.join(ROOT, "scrapbook", "creatures_archive.json")
CREATURES_DIR = os.path.join(ROOT, "scrapbook", "creatures")
LIVE_GIF = os.path.join(ROOT, "render", "creature.gif")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _fresh() -> dict:
    return {
        "round": config.CREATURE_ROUNDS[0],
        "features": {r: {"votes": {}} for r in config.CREATURE_ROUNDS},
        "voters": {},
        "voter_counts": {},
        "history": [],
        "started": datetime.now(timezone.utc).date().isoformat(),
    }


def locked_features(state: dict) -> dict:
    """Flat {round: value} of everything locked so far — what the renderer draws."""
    return {r: f["locked"] for r, f in state.get("features", {}).items()
            if isinstance(f, dict) and "locked" in f}


def _finalize(state: dict) -> dict:
    """Render the finished creature to the scrapbook, archive it, return a fresh one."""
    feats = locked_features(state)
    archive = _load(ARCHIVE, {"total_finished": 0, "creatures": []})
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    nn = sum(1 for c in archive["creatures"] if c["id"].startswith(month)) + 1
    cid = f"{month}-creature-{nn:02d}"

    os.makedirs(CREATURES_DIR, exist_ok=True)
    img_rel = f"scrapbook/creatures/{cid}.gif"
    creature_gif.render_creature(feats, os.path.join(CREATURES_DIR, f"{cid}.gif"), title=cid)

    top = sorted(state.get("voter_counts", {}).items(), key=lambda kv: kv[1], reverse=True)
    archive["creatures"].append({
        "id": cid,
        "features": feats,
        "completed": datetime.now(timezone.utc).date().isoformat(),
        "image": img_rel,
        "top_voters": [u for u, _ in top[:5]],
    })
    archive["total_finished"] = archive.get("total_finished", 0) + 1
    _save(ARCHIVE, archive)
    return _fresh()


def main() -> None:
    event = gh.load_event()
    issue = event.get("issue", {})
    number = issue.get("number")
    title = issue.get("title", "")
    author = issue.get("user", {}).get("login", "someone")

    parts = title.split("|")
    if len(parts) != 4 or parts[0] != "creature" or parts[1] != "vote":
        print(f"not a creature vote: {title!r}")
        return
    _, _, rnd, option = parts

    state = _load(STATE, _fresh())
    current = state.get("round", config.CREATURE_ROUNDS[0])

    # stale link (round already advanced)
    if rnd != current:
        gh.comment(number, f"🐠 That vote was for the **{rnd}** round, but we're on "
                           f"**{current}** now. Hop back to the profile for the live "
                           "options!")
        gh.close_issue(number)
        return

    if option not in config.CREATURE_OPTIONS.get(current, []):
        gh.comment(number, f"🐠 \"{option}\" isn't an option for the {current} round. "
                           "Check the profile for the current choices.")
        gh.close_issue(number)
        return

    # one vote per user per round
    voters_round = state.setdefault("voters", {}).setdefault(current, [])
    if config.CREATURE_ONE_VOTE_PER_USER_PER_ROUND and author in voters_round:
        gh.comment(number, "🐚 You've already voted this round — one vote per visit. "
                           "Come back for the next feature!")
        gh.close_issue(number)
        return

    votes = state["features"][current].setdefault("votes", {})
    votes[option] = votes.get(option, 0) + 1
    voters_round.append(author)
    state.setdefault("voter_counts", {})[author] = \
        state.get("voter_counts", {}).get(author, 0) + 1

    finished = False
    locked_value = None
    if max(votes.values()) >= config.CREATURE_VOTE_THRESHOLD:
        leader = max(votes, key=votes.get)
        locked_value = leader
        state["features"][current] = {"locked": leader}
        state.setdefault("history", []).append(f"{current}->{leader}")
        idx = config.CREATURE_ROUNDS.index(current)
        if idx + 1 < len(config.CREATURE_ROUNDS):
            state["round"] = config.CREATURE_ROUNDS[idx + 1]
        else:
            state = _finalize(state)   # was the final round
            finished = True

    _save(STATE, state)

    # re-render the live creature (fresh egg if we just finalized)
    creature_gif.render_creature(locked_features(state), LIVE_GIF)
    scrapbook.build_scrapbook()
    build_readme.main()

    if finished:
        msg = ("🦄🐠 Your vote completed the creature — it's saved to the scrapbook 📖, "
               "and a brand-new one just hatched. Come name its body!")
    elif locked_value:
        msg = (f"🐠 Your vote **locked the {current} as `{locked_value}`**! "
               f"On to the next feature → check the profile.")
    else:
        cnt = votes[option]
        msg = (f"🐠 Your vote for **{option}** ({current}) is in — that's {cnt} so far. "
               "Thanks for shaping the creature!")
    gh.comment(number, msg)
    gh.close_issue(number)
    print(f"creature vote handled: {current}|{option} finished={finished}")


if __name__ == "__main__":
    main()
