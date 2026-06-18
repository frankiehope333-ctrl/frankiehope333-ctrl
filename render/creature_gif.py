"""render/creature_gif.py — the community creature (PROFILE-SPEC GAME 3).

Layered chunky-pixel sprites: body base + tail + color fill + eyes + accessory,
each authored once in the sunset palette. The community locks one layer per round
(body -> tail -> color -> eyes -> accessory); this renders the creature so-far,
with a gentle wiggle and the always-on kawaii face. When the final round locks,
the handler calls render_creature() with all features for the scrapbook GIF.

Local test:  python render/creature_gif.py   # renders a sample finished creature
"""

from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import (  # noqa: E402
    PALETTE, hex_to_rgb, sunset_sky, scale, sway_offset, export_gif, kawaii_face,
    draw_bubble, mix,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "render", "creature.gif")

W, H, FACTOR, N = 48, 44, 5, 16
BAR_H, BORDER = 20, 3

COLOR_MAP = {
    "coral-pink": "coral",
    "peach-glow": "peach",
    "orchid": "orchid",
}


def _color(features: dict) -> tuple:
    name = features.get("color")
    return hex_to_rgb(PALETTE[COLOR_MAP.get(name, "coral")])


def _body_seahorse(d, cx, cy, col, shade):
    # curved upright body + snout
    for i, (dx, w) in enumerate([(0, 5), (1, 5), (1, 4), (0, 4), (-1, 4), (-1, 5)]):
        y = cy - 9 + i * 3
        d.ellipse([cx + dx - w, y, cx + dx + w, y + 3], fill=col)
    d.rectangle([cx + 3, cy - 12, cx + 8, cy - 9], fill=col)   # snout
    d.line([(cx - 5, cy - 11), (cx - 3, cy - 13)], fill=shade)  # crest


def _body_jellyfish(d, cx, cy, col, shade):
    d.ellipse([cx - 8, cy - 12, cx + 8, cy + 2], fill=col)       # dome
    d.rectangle([cx - 8, cy - 4, cx + 8, cy], fill=col)
    for k, tx in enumerate(range(cx - 6, cx + 7, 3)):            # tentacles
        for ty in range(cy, cy + 12, 2):
            off = round(math.sin((ty + k) * 0.6))
            d.point([(tx + off, ty)], fill=shade)


def _body_eel(d, cx, cy, col, shade):
    for x in range(cx - 12, cx + 12):
        y = cy + round(4 * math.sin((x - cx) * 0.4))
        d.ellipse([x - 1, y - 2, x + 1, y + 2], fill=col)
    d.point([(cx - 12, cy)], fill=shade)


def _tail(d, cx, cy, col, shade, kind):
    bx, by = cx - 6, cy + 8
    if kind == "flowing":
        for i in range(5):
            d.ellipse([bx - i, by + i * 2, bx + 3 - i, by + 3 + i * 2], fill=col)
    elif kind == "fan":
        d.polygon([(bx, by), (bx - 6, by + 6), (bx + 6, by + 6)], fill=col)
        d.line([(bx, by), (bx, by + 6)], fill=shade)
    elif kind == "spiked":
        for i in range(4):
            d.polygon([(bx - 6 + i * 4, by + 6), (bx - 4 + i * 4, by),
                       (bx - 2 + i * 4, by + 6)], fill=col)


def _accessory(d, cx, cy, kind):
    cream = hex_to_rgb(PALETTE["cream"])
    if kind == "pearl-crown":
        for ox in (-4, 0, 4):
            d.ellipse([cx + ox - 1, cy - 16, cx + ox + 1, cy - 14], fill=cream)
    elif kind == "shell-clip":
        d.ellipse([cx + 6, cy - 8, cx + 11, cy - 3], fill=hex_to_rgb(PALETTE["hotpink"]))
        d.line([(cx + 8, cy - 7), (cx + 8, cy - 4)], fill=cream)
    elif kind == "bubble-ring":
        for a in range(0, 360, 45):
            rx = cx + int(13 * math.cos(math.radians(a)))
            ry = cy - 4 + int(13 * math.sin(math.radians(a)))
            draw_bubble(d, rx, ry, 1)


def _draw(features: dict, frame: int) -> Image.Image:
    img = sunset_sky(W, H, deep=True)
    d = ImageDraw.Draw(img)
    cx = W // 2 + round(sway_offset(frame, N, 1.5))
    cy = H // 2 + round(sway_offset(frame, N, 1.0, phase=1))

    body = features.get("body")
    col = _color(features)
    shade = mix(PALETTE["plum"], "#000000", 0.1)

    if not body:
        # round 1: a mystery egg, hatching soon, kawaii face on the shell
        d.ellipse([cx - 9, cy - 11, cx + 9, cy + 9], fill=hex_to_rgb(PALETTE["cream"]))
        d.ellipse([cx - 9, cy - 11, cx + 9, cy + 9], outline=hex_to_rgb(PALETTE["coral"]))
        kawaii_face(d, cx, cy - 1, look="sleepy", eye=PALETTE["plum"])
    else:
        if features.get("tail"):
            _tail(d, cx, cy, col, shade, features["tail"])
        {"seahorse": _body_seahorse, "jellyfish": _body_jellyfish,
         "eel": _body_eel}.get(body, _body_seahorse)(d, cx, cy, col, shade)
        kawaii_face(d, cx, cy - 3, look=features.get("eyes", "dot"))
        if features.get("accessory"):
            _accessory(d, cx, cy, features["accessory"])

    # a couple of ambient bubbles
    for k, ox in enumerate((-12, 12)):
        prog = ((frame + k * 6) % N) / N
        draw_bubble(d, cx + ox, int((H - 2) - prog * (H - 6)), 1)

    return scale(img, FACTOR)


def _chrome(scene: Image.Image, title: str) -> Image.Image:
    sw, sh = scene.size
    card = Image.new("RGB", (sw + BORDER * 2, sh + BORDER * 2 + BAR_H),
                     hex_to_rgb(PALETTE["cream"]))
    d = ImageDraw.Draw(card)
    for x in range(BORDER, sw + BORDER):
        t = (x - BORDER) / max(1, sw)
        d.line([(x, BORDER), (x, BORDER + BAR_H - 1)],
               fill=mix(PALETTE["hotpink"], PALETTE["coral"], t))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
    d.text((BORDER + 6, BORDER + 4), title, fill=hex_to_rgb(PALETTE["cream"]), font=font)
    for i in range(2):
        bx = sw + BORDER - 14 - i * 14
        d.rectangle([bx, BORDER + 5, bx + 8, BORDER + 13], fill=hex_to_rgb(PALETTE["cream"]))
    card.paste(scene, (BORDER, BORDER + BAR_H))
    return card


def render_creature(features: dict, out_path: str = OUT,
                    title: str = "creature lab <3") -> str:
    frames = [_chrome(_draw(features, f), title) for f in range(N)]
    export_gif(frames, out_path, duration=100)
    return out_path


if __name__ == "__main__":
    sample = {"body": "seahorse", "tail": "fan", "color": "coral-pink",
              "eyes": "sparkle", "accessory": "pearl-crown"}
    out = render_creature(sample)
    print(f"wrote {out} ({os.path.getsize(out)/1024:.1f} KB)")
