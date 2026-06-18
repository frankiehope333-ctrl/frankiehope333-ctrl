"""render/bottle_gif.py — the single bobbing-bottle GIF (PROFILE-SPEC GAME 2).

ONE hero pixel bottle riding a sine bob on a couple of wavelets, in the sunset
palette. This is STATIC art — rendered ONCE and committed; the bottle handler
never touches it (BUILD.md §6). It just decorates the running total; the count
text stays plain (no 🍾 emoji — the GIF bottle IS the bottle).

Run once:  python render/bottle_gif.py   ->  render/bottle_bob.gif
"""

from __future__ import annotations

import math
import os
import sys

from PIL import ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import PALETTE, hex_to_rgb, new_canvas, scale, export_gif  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "render", "bottle_bob.gif")

W, H, FACTOR, N = 32, 28, 2, 18   # tiny ~64x56 loop (BUILD.md / SPEC)


def _frame(f: int):
    img = new_canvas(W, H, "plum")
    d = ImageDraw.Draw(img)

    # sky behind the bottle: orchid -> purple -> plum
    for y in range(H):
        t = y / (H - 1)
        from sprites import mix
        d.line([(0, y), (W, y)], fill=mix(PALETTE["orchid"], PALETTE["plum"], t))

    # bob offset (vertical) + gentle rotation feel via horizontal lean
    bob = round(2 * math.sin(f / N * 2 * math.pi))
    lean = round(1.5 * math.sin(f / N * 2 * math.pi))

    # waterline near the bottom (two wavelets, sunset caps + cream foam)
    wave_y = H - 8 + round(math.sin(f / N * 2 * math.pi))
    d.rectangle([0, wave_y, W, H], fill=hex_to_rgb(PALETTE["hotpink"]))
    d.line([(0, wave_y), (W, wave_y)], fill=hex_to_rgb(PALETTE["coral"]))
    d.rectangle([0, wave_y + 3, W, wave_y + 5], fill=hex_to_rgb(PALETTE["plum"]))
    for fx in range(2, W, 7):
        d.point([(fx, wave_y - 1)], fill=hex_to_rgb(PALETTE["cream"]))

    # the bottle (cork=ember, glass=mint, rolled note=cream), centered, bobbing
    cx = W // 2 + lean
    top = 6 + bob
    glass = (159, 230, 214)             # the mockup's mint glass
    cream = hex_to_rgb(PALETTE["cream"])
    # body
    d.rounded_rectangle([cx - 4, top + 6, cx + 4, top + 17], radius=2,
                        fill=glass, outline=cream)
    # neck
    d.rectangle([cx - 2, top + 1, cx + 1, top + 6], fill=glass, outline=cream)
    # cork
    d.rectangle([cx - 2, top - 2, cx + 1, top + 1], fill=hex_to_rgb(PALETTE["ember"]))
    # rolled note inside
    d.rectangle([cx - 2, top + 9, cx + 1, top + 14], fill=cream)

    # a rising bubble
    bub_y = (H - 6) - ((f * 2) % (H - 8))
    d.ellipse([cx + 6, bub_y, cx + 7, bub_y + 1], outline=cream)

    return scale(img, FACTOR)


def render_bottle(out_path: str = OUT) -> str:
    frames = [_frame(f) for f in range(N)]
    export_gif(frames, out_path, duration=110)
    return out_path


if __name__ == "__main__":
    out = render_bottle()
    print(f"wrote {out} ({os.path.getsize(out)/1024:.1f} KB)")
