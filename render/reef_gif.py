"""render/reef_gif.py — the reef board, an animated GIF (PROFILE-SPEC GAME 1).

A sunset lagoon that grows from real commits: swaying coral, bobbing fish, a
rising-bubble loop, kelp stalks. Rendered to an animated GIF because the wiggle
has to survive GitHub's image proxy (an SVG would freeze on frame 1).

Also home to the daily-tide logic (BUILD.md §5): month-end snapshot, fetch the
contribution count via GraphQL, grow, cap snapshot, render. The two snapshot
triggers share one `snapshot_reef()` so they behave identically.

Local test:  python render/reef_gif.py        # renders reef.gif from state/reef.json
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from sprites import (  # noqa: E402
    PALETTE, hex_to_rgb, sunset_sky, scale, sway_offset, export_gif,
    kawaii_face, draw_star,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state", "reef.json")
ARCHIVE = os.path.join(ROOT, "scrapbook", "reefs_archive.json")
REEFS_DIR = os.path.join(ROOT, "scrapbook", "reefs")
OUT = os.path.join(ROOT, "render", "reef.gif")

# logical scene size, scaled up blocky
W, H, FACTOR, N_FRAMES = 100, 32, 8, 16
BAR_H = 22          # cozy-window title bar (drawn at full res)
BORDER = 3


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def _pos(item, key, default, scale_to):
    """Read a coordinate that may be a percent (0–100) or absolute; map to px."""
    v = item.get(key, default)
    return int(round((v / 100.0) * scale_to)) if v is not None else default


def _draw_scene(reef: dict, frame: int) -> Image.Image:
    img = sunset_sky(W, H)
    d = ImageDraw.Draw(img)

    # sun low on the horizon + a soft reflection band
    sx, sy = int(W * 0.78), int(H * 0.30)
    d.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], fill=hex_to_rgb(PALETTE["ember"]))
    for ry in range(int(H * 0.66), H, 3):
        d.line([(sx - 3, ry), (sx + 3, ry)], fill=hex_to_rgb(PALETTE["peach"]))

    # ambient stars (twinkle) + a couple of soft clouds
    if frame % 6 < 3:
        draw_star(d, int(W * 0.12), int(H * 0.18))
    if frame % 6 >= 3:
        draw_star(d, int(W * 0.45), int(H * 0.12))
    cream = hex_to_rgb(PALETTE["cream"])
    for cx, cy in ((int(W * 0.25), int(H * 0.20)), (int(W * 0.60), int(H * 0.26))):
        # a soft pixel puff: a base row with two smaller bumps on top
        d.rectangle([cx, cy + 2, cx + 9, cy + 3], fill=cream)
        d.rectangle([cx + 2, cy, cx + 4, cy + 2], fill=cream)
        d.rectangle([cx + 5, cy + 1, cx + 7, cy + 2], fill=cream)

    items = reef.get("creatures", [])
    floor = H - 1

    # coral + kelp (sway), drawn from the floor up
    for i, it in enumerate(items):
        t = it.get("type")
        x = _pos(it, "x", (i * 13) % W, W)
        off = round(sway_offset(frame, N_FRAMES, 1.4, phase=i * 0.9))
        if t == "coral":
            size = max(2, int(it.get("size", 3)))
            col = [PALETTE["coral"], PALETTE["hotpink"], PALETTE["orchid"]][i % 3]
            for b in range(size):
                bx = x + off + (1 if b % 2 else -1)
                by = floor - b * 3
                d.rectangle([bx, by - 2, bx + 2, by], fill=hex_to_rgb(col))
            d.rectangle([x + off - 1, floor - size * 3 - 2, x + off + 3,
                         floor - size * 3 + 1], fill=hex_to_rgb(col))
        elif t == "kelp":
            ht = max(3, int(it.get("height", 4)))
            for b in range(ht * 2):
                bx = x + round(sway_offset(frame, N_FRAMES, 1.8, phase=i + b * 0.3))
                by = floor - b * 2
                d.point([(bx, by), (bx, by - 1)], fill=hex_to_rgb(PALETTE["plum"]))

    # fish (bob + drift) with kawaii faces
    for i, it in enumerate(items):
        if it.get("type") != "fish":
            continue
        x = _pos(it, "x", (i * 17) % W, W)
        y = _pos(it, "y", int(H * 0.45), H)
        dx = round(sway_offset(frame, N_FRAMES, 2.5, phase=i * 1.3))
        dy = round(sway_offset(frame, N_FRAMES, 1.5, phase=i * 0.7 + 1))
        bx, by = x + dx, y + dy
        body = [PALETTE["coral"], PALETTE["peach"], PALETTE["cream"]][i % 3]
        d.ellipse([bx - 3, by - 2, bx + 3, by + 2], fill=hex_to_rgb(body))
        d.polygon([(bx - 3, by), (bx - 6, by - 2), (bx - 6, by + 2)],
                  fill=hex_to_rgb(PALETTE["hotpink"]))
        kawaii_face(d, bx + 1, by, look="dot")

    # rising bubbles loop
    for k, bx0 in enumerate((int(W * 0.18), int(W * 0.5), int(W * 0.82))):
        prog = ((frame + k * 5) % N_FRAMES) / N_FRAMES
        by = int(floor - prog * (H - 4))
        d.ellipse([bx0, by, bx0 + 1, by + 1], outline=hex_to_rgb(PALETTE["cream"]))

    return scale(img, FACTOR)


def _frame_with_chrome(scene: Image.Image, title: str) -> Image.Image:
    """Wrap a scaled scene in the cozy retro window (cream border + title bar with
    the little decorative buttons). Title text drawn at full res so it stays crisp."""
    sw, sh = scene.size
    fw = sw + BORDER * 2
    fh = sh + BORDER * 2 + BAR_H
    card = Image.new("RGB", (fw, fh), hex_to_rgb(PALETTE["cream"]))
    d = ImageDraw.Draw(card)
    # title bar gradient band (hotpink -> coral)
    for x in range(BORDER, fw - BORDER):
        t = (x - BORDER) / max(1, sw)
        from sprites import mix
        d.line([(x, BORDER), (x, BORDER + BAR_H - 1)],
               fill=mix(PALETTE["hotpink"], PALETTE["coral"], t))
    # title text
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    d.text((BORDER + 8, BORDER + 4), title, fill=hex_to_rgb(PALETTE["cream"]), font=font)
    # decorative min/close buttons
    for i in range(2):
        bx = fw - BORDER - 16 - i * 16
        d.rectangle([bx, BORDER + 6, bx + 9, BORDER + 15], fill=hex_to_rgb(PALETTE["cream"]))
    # paste scene below the bar
    card.paste(scene, (BORDER, BORDER + BAR_H))
    return card


def render_reef(reef: dict, out_path: str = OUT, title: str = "frankie's reef <3") -> str:
    frames = [_frame_with_chrome(_draw_scene(reef, f), title) for f in range(N_FRAMES)]
    export_gif(frames, out_path, duration=90)
    return out_path


# ---------------------------------------------------------------------------
# state helpers
# ---------------------------------------------------------------------------
def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _counts(reef: dict) -> dict:
    c = {"coral": 0, "fish": 0, "kelp": 0}
    for it in reef.get("creatures", []):
        c[it.get("type", "fish")] = c.get(it.get("type", "fish"), 0) + 1
    return c


# ---------------------------------------------------------------------------
# growth + snapshot logic (BUILD.md §5)
# ---------------------------------------------------------------------------
def grow(reef: dict, contributions: int, today: str) -> dict:
    """Add fish / coral / kelp per REEF_MAP. 0 contributions => just reseed sway."""
    items = reef.setdefault("creatures", [])
    n = len(items)
    if contributions <= 0:
        reef["last_synced"] = today
        return reef
    for typ, (lo, hi) in config.REEF_MAP.items():
        if lo <= contributions <= hi:
            new = {"type": typ, "born": today,
                   "x": (n * 37 + 11) % 100, "y": 30 + (n * 23) % 50}
            if typ == "coral":
                new["size"] = 3
            elif typ == "kelp":
                new["height"] = 4
            items.append(new)
            break
    reef["last_synced"] = today
    return reef


def snapshot_reef(reef: dict, reason: str, contributions_total: int = 0) -> dict:
    """Render the current reef to the scrapbook, archive it, reset to empty.
    Shared by both the cap and month-end triggers so they behave identically."""
    archive = _load(ARCHIVE, {"total_reefs": 0, "reefs": []})
    month = (reef.get("last_synced") or date.today().isoformat())[:7]
    nn = sum(1 for r in archive["reefs"] if r["id"].startswith(month)) + 1
    reef_id = f"{month}-reef-{nn:02d}"

    os.makedirs(REEFS_DIR, exist_ok=True)
    img_path = os.path.join(REEFS_DIR, f"{reef_id}.gif")
    render_reef(reef, img_path, title=f"reef {reef_id}")

    born_dates = [it.get("born") for it in reef.get("creatures", []) if it.get("born")]
    archive["reefs"].append({
        "id": reef_id,
        "from": min(born_dates) if born_dates else None,
        "to": reef.get("last_synced"),
        "reason": reason,
        "contributions": contributions_total,
        "counts": _counts(reef),
        "image": f"scrapbook/reefs/{reef_id}.gif",
    })
    archive["total_reefs"] = archive.get("total_reefs", 0) + 1
    _save(ARCHIVE, archive)
    return {"last_synced": reef.get("last_synced"), "creatures": []}


def daily_tide(contributions: int, today: str | None = None) -> dict:
    """One day's run, in the CRITICAL order (BUILD.md §5 / SPEC GAME 1).
    Returns the resulting reef dict (already saved). Rendering + build_readme are
    done by the caller/workflow afterward (so this is unit-testable)."""
    today = today or datetime.now(timezone.utc).date().isoformat()
    reef = _load(STATE, {"last_synced": None, "creatures": []})

    # 1. MONTH-END CHECK (before growth) — only if it's the 1st AND reef non-empty
    if config.REEF_MONTH_END_SNAPSHOT and today.endswith("-01") and reef.get("creatures"):
        total = reef.get("contrib_total", 0)
        reef = snapshot_reef(reef, "month-end", total)

    # 2. FETCH happens outside (caller passes `contributions`).
    # 3. GROW
    reef = grow(reef, contributions, today)
    reef["contrib_total"] = reef.get("contrib_total", 0) + max(0, contributions)

    # 4. CAP CHECK (after growth)
    if len(reef.get("creatures", [])) > config.REEF_CAP:
        total = reef.get("contrib_total", 0)
        reef = snapshot_reef(reef, "cap", total)
        reef["contrib_total"] = 0

    _save(STATE, reef)
    return reef


# ---------------------------------------------------------------------------
# GraphQL — own public contribution count for a day (uses built-in GITHUB_TOKEN)
# ---------------------------------------------------------------------------
def fetch_contributions(day: str, token: str, user: str = config.GH_USER) -> int:
    """Total contributions for `user` on calendar day `day` (YYYY-MM-DD), via the
    GitHub GraphQL contributionsCollection. No PAT needed for own public data."""
    import requests

    start = f"{day}T00:00:00Z"
    end = f"{day}T23:59:59Z"
    query = """
    query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) {
        contributionsCollection(from:$from, to:$to) {
          contributionCalendar { totalContributions }
        }
      }
    }"""
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"login": user, "from": start, "to": end}},
        headers={"Authorization": f"bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return (data["data"]["user"]["contributionsCollection"]
            ["contributionCalendar"]["totalContributions"])


if __name__ == "__main__":
    reef = _load(STATE, {"last_synced": None, "creatures": []})
    if not reef.get("creatures"):
        # give the local test something to look at
        reef = {"last_synced": date.today().isoformat(), "creatures": [
            {"type": "coral", "x": 12, "y": 60, "size": 3, "born": "2026-06-10"},
            {"type": "coral", "x": 40, "y": 60, "size": 4, "born": "2026-06-11"},
            {"type": "fish", "x": 30, "y": 35, "born": "2026-06-14"},
            {"type": "fish", "x": 70, "y": 50, "born": "2026-06-15"},
            {"type": "kelp", "x": 6, "y": 60, "height": 5, "born": "2026-06-15"},
            {"type": "kelp", "x": 88, "y": 60, "height": 4, "born": "2026-06-16"},
        ]}
    out = render_reef(reef)
    print(f"wrote {out} ({os.path.getsize(out)/1024:.1f} KB)")
