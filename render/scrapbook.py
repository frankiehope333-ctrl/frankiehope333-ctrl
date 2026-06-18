"""render/scrapbook.py — builds scrapbook/SCRAPBOOK.md from the archives.

The scrapbook is the permanent record: every bottle ever sent, every finished
creature, every completed reef. Display and archive are separate — boards trim,
the archive keeps everything (PROFILE-SPEC §THE SCRAPBOOK). Handlers and the reef
cron call build_scrapbook() whenever an archive changes.

Sections: bottle wall · creature menagerie · reef timeline.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SB = os.path.join(ROOT, "scrapbook")
OUT = os.path.join(SB, "SCRAPBOOK.md")

# how many bottle cards to render on the page (full data stays in JSON regardless)
BOTTLE_PAGE_CAP = 200


def _load(name, default):
    try:
        with open(os.path.join(SB, name), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _img(path: str) -> str:
    """Archive paths are repo-root relative ('scrapbook/reefs/x.gif'); SCRAPBOOK.md
    lives inside scrapbook/, so drop the leading 'scrapbook/'."""
    return path[len("scrapbook/"):] if path.startswith("scrapbook/") else path


def _bottle_wall(out: list) -> None:
    data = _load("bottles_archive.json", {"total_ever": 0, "bottles": []})
    total = data.get("total_ever", 0)
    out.append('<a name="bottles"></a>\n\n## 🍾 the bottle wall\n')
    out.append(f"<h3 align=\"center\">{total} bottles tossed into the sea so far</h3>\n")
    bottles = sorted(data.get("bottles", []), key=lambda b: b.get("n", 0), reverse=True)
    if not bottles:
        out.append("\n*No bottles yet — be the first.*\n")
        return
    shown = bottles[:BOTTLE_PAGE_CAP]
    for b in shown:
        when = (b.get("when", "") or "").split("T")[0]
        out.append(f"> 🍾 *\"{b.get('msg','')}\"* — @{b.get('from','someone')} · "
                   f"{when} · #{b.get('n','?')}\n")
    if len(bottles) > len(shown):
        out.append(f"\n<sub>…and {len(bottles) - len(shown)} more in the archive.</sub>\n")


def _menagerie(out: list) -> None:
    data = _load("creatures_archive.json", {"total_finished": 0, "creatures": []})
    out.append('\n<a name="creatures"></a>\n\n## 🐠 the creature menagerie\n')
    out.append(f"<h3 align=\"center\">{data.get('total_finished', 0)} creatures finished</h3>\n")
    creatures = data.get("creatures", [])
    if not creatures:
        out.append("\n*No finished creatures yet — vote one into being on the profile.*\n")
        return
    out.append("<table><tr>\n")
    for i, c in enumerate(creatures):
        if i and i % 3 == 0:
            out.append("</tr><tr>\n")
        feats = c.get("features", {})
        flist = " · ".join(f"{k}: {v}" for k, v in feats.items())
        voters = ", ".join(f"@{v}" for v in c.get("top_voters", [])[:3])
        cap = (f"<b>{c.get('id','')}</b><br><sub>born {c.get('completed','')}<br>"
               f"{flist}" + (f"<br>built by {voters}" if voters else "") + "</sub>")
        out.append(f'<td align="center"><img src="{_img(c.get("image",""))}" '
                   f'width="150"><br>{cap}</td>\n')
    out.append("</tr></table>\n")


def _reef_timeline(out: list) -> None:
    data = _load("reefs_archive.json", {"total_reefs": 0, "reefs": []})
    out.append('\n<a name="reefs"></a>\n\n## 🪸 the reef timeline\n')
    out.append(f"<h3 align=\"center\">{data.get('total_reefs', 0)} reefs completed</h3>\n")
    reefs = data.get("reefs", [])
    if not reefs:
        out.append("\n*No completed reefs yet — the first closes at month-end or the 40 cap.*\n")
        return
    out.append("<table><tr>\n")
    for i, r in enumerate(reefs):
        if i and i % 2 == 0:
            out.append("</tr><tr>\n")
        counts = r.get("counts", {})
        reason = "month-end" if r.get("reason") == "month-end" else "filled up"
        cap = (f"<b>{r.get('id','')}</b> · {reason}<br>"
               f"<sub>{r.get('from','?')} → {r.get('to','?')}<br>"
               f"{r.get('contributions',0)} contributions · "
               f"🪸{counts.get('coral',0)} 🐟{counts.get('fish',0)} 🌿{counts.get('kelp',0)}</sub>")
        out.append(f'<td align="center"><img src="{_img(r.get("image",""))}" '
                   f'width="320"><br>{cap}</td>\n')
    out.append("</tr></table>\n")


def build_scrapbook(out_path: str = OUT) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = [
        "# 📖 The CLEAVE Scrapbook\n",
        "<sub>A living record of this profile's community and momentum. "
        "Boards on the profile show only what's recent — nothing here is ever "
        "trimmed.</sub>\n",
        "\n[🍾 bottles](#bottles) · [🐠 creatures](#creatures) · [🪸 reefs](#reefs)\n",
        "\n---\n",
    ]
    _bottle_wall(out)
    out.append("\n---\n")
    _menagerie(out)
    out.append("\n---\n")
    _reef_timeline(out)
    out.append(f"\n---\n\n<sub>🌊 Rebuilt {stamp} UTC by render/scrapbook.py.</sub>\n")
    text = "\n".join(out)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path


if __name__ == "__main__":
    p = build_scrapbook()
    print(f"wrote {p}")
