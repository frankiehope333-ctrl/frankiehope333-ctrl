"""render/story_panels.py — animated pixel scenes for "The Deep Dive".

One looping GIF per story page, drawn with the SAME sprite system as the reef &
creature (render/sprites.py). No AI image gen — Marlowe is the same sprite data on
every page, so she never drifts (STORY-PANELS.md). Crisp grid pixels: draw small,
scale up with NEAREST. Gentle wiggle: swaying kelp, rising bubbles, bobbing fish &
creatures, floating characters, twinkling stars, pulsing glow.

  python render/story_panels.py start       # render one panel (verify it first)
  python render/story_panels.py             # render all panels
"""

from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import (  # noqa: E402
    PALETTE, hex_to_rgb, scale, mix, vertical_gradient, export_gif,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "adventure")
TITLE = "🌙 the deep dive"

W, H, FACTOR = 160, 104, 5
BAR_H, BORDER = 16, 2
N, DUR = 14, 100   # frames, ms per frame

C = {k: hex_to_rgb(v) for k, v in PALETTE.items()}
SKIN = (245, 208, 184)      # Cass — pale / white skin
SKIN_SH = (214, 173, 150)


def wob(f, amp, phase=0.0):
    return amp * math.sin(2 * math.pi * f / N + phase)


def _hx(rgb):
    return "#%02X%02X%02X" % rgb


# ---------------------------------------------------------------------------
# sky / light
# ---------------------------------------------------------------------------
def draw_sky(depth: float) -> Image.Image:
    top = mix("#3a2356", "#100a18", depth)
    umid = mix(PALETTE["purple"], "#1c1230", depth)
    lmid = mix(PALETTE["hotpink"], "#3a1d40", depth)
    bot = mix(PALETTE["peach"], PALETTE["plum"], depth)
    return vertical_gradient(W, H, [(0.0, _hx(top)), (0.34, _hx(umid)),
                                    (0.66, _hx(lmid)), (1.0, _hx(bot))])


def draw_sun(d, x, y, r=7):
    d.ellipse([x - r - 1, y - r - 1, x + r + 1, y + r + 1], fill=mix(PALETTE["ember"], PALETTE["peach"], .4))
    d.ellipse([x - r, y - r, x + r, y + r], fill=C["ember"])


def draw_godrays(d, sun_x, top_y, f, wl=46):
    """Faint diagonal light shafts from the sun — soft continuous, slowly drifting.
    Only over the sky (above the waterline) so they read as light, not scratches."""
    soft = mix(PALETTE["peach"], PALETTE["hotpink"], .35)
    for k in range(3):
        x0 = sun_x - 22 + k * 18 + round(wob(f, 2, k))
        for t in range(0, 40):
            x, y = x0 - t, top_y + t
            if 0 <= x < W and y < wl and (x + y) % 2 == 0:   # 50% dither = soft
                d.point([(x, y)], fill=soft)


def draw_reflection(d, sun_x, y0, depth, f):
    rows = list(range(y0, min(y0 + 18, H - 18), 2))
    for i, y in enumerate(rows):
        fade = 1 - i / max(1, len(rows))
        col = mix(PALETTE["peach"], PALETTE["hotpink"], 1 - fade)
        offset = (i * 3 + f) % 6
        for x in range(offset, W, 6):
            near = max(0, 1 - abs(x - sun_x) / 70)
            c = mix(_hx(col), PALETTE["ember"], near * 0.5)
            d.line([(x, y), (x + 2, y)], fill=c)


def draw_waterline(d, y):
    d.line([(0, y), (W, y)], fill=C["coral"])
    for x in range(0, W, 7):
        d.point([(x, y - 1), (x + 3, y - 1)], fill=C["cream"])
    d.line([(0, y + 1), (W, y + 1)], fill=mix(PALETTE["hotpink"], PALETTE["plum"], .3))


def draw_glow(d, cx, cy, r, f, inner="peach", outer="plum"):
    pulse = 1 + 0.06 * math.sin(2 * math.pi * f / N)
    r = int(r * pulse)
    for i in range(r, 0, -1):
        t = i / r
        col = mix(PALETTE[inner], PALETTE[outer], t ** 0.7)
        d.ellipse([cx - i, cy - int(i * 0.62), cx + i, cy + int(i * 0.62)], fill=col)


# ---------------------------------------------------------------------------
# ambient
# ---------------------------------------------------------------------------
def draw_stars(d, pts, f):
    for j, (x, y) in enumerate(pts):
        if (f + j * 3) % N < N * 0.6:      # twinkle on/off
            bright = (f + j * 2) % 4 < 2
            col = C["cream"] if bright else C["peach"]
            d.point([(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y), (x, y)], fill=col)


def draw_clouds(d, pts):
    for (x, y) in pts:
        d.rectangle([x, y + 2, x + 9, y + 3], fill=C["cream"])
        d.rectangle([x + 2, y, x + 4, y + 2], fill=C["cream"])
        d.rectangle([x + 5, y + 1, x + 7, y + 2], fill=C["cream"])


def draw_bubbles(d, x, y0, f, n=4, rng=26, phase=0):
    for i in range(n):
        prog = ((f + i * (N // n) + phase) % N) / N
        y = int(y0 - prog * rng)
        drift = round(wob(f + i * 3, 1))
        r = 1 if i % 2 else 0
        d.ellipse([x + drift - r, y - r, x + drift + r, y + r], outline=C["cream"])


def draw_particles(d, pts, f):
    """Drifting plankton sparks in deep water."""
    for j, (x, y0) in enumerate(pts):
        prog = ((f + j * 2) % N) / N
        y = int(y0 - prog * 12)
        if (f + j) % 3:
            d.point([(x + round(wob(f, 1, j)), y)], fill=mix(PALETTE["cream"], PALETTE["peach"], .4))


def draw_fish(d, x, y, f, hue="coral", flip=False, phase=0.0):
    body = C.get(hue, C["coral"])
    s = -1 if flip else 1
    y = y + round(wob(f, 2, phase))
    x = x + round(wob(f * 0.5, 3, phase))
    d.ellipse([x - 3, y - 2, x + 3, y + 2], fill=body)
    d.polygon([(x - 3 * s, y), (x - 6 * s, y - 2), (x - 6 * s, y + 2)], fill=C["hotpink"])
    d.point([(x + 1 * s, y - 1)], fill=C["plum"])


def draw_school(d, cx, cy, f, hue="peach", flip=False):
    for i, (dx, dy) in enumerate([(0, 0), (-7, 3), (-5, -4), (-13, 0)]):
        draw_fish(d, cx + dx, cy + dy, f, hue, flip, phase=i * 1.3)


def draw_jelly(d, x, y0, f, hue="orchid"):
    y = y0 + round(wob(f, 2, x))
    col = C[hue]
    d.ellipse([x - 6, y - 5, x + 6, y + 2], fill=col)
    d.rectangle([x - 6, y - 1, x + 6, y + 1], fill=col)
    d.point([(x - 3, y - 2), (x + 3, y - 2)], fill=C["cream"])   # little eyes
    for k, tx in enumerate(range(x - 5, x + 6, 3)):              # tentacles
        for ty in range(y + 1, y + 9, 2):
            d.point([(tx + round(math.sin((ty + k + f) * 0.5)), ty)], fill=mix(PALETTE[hue], PALETTE["coral"], .4))


# ---------------------------------------------------------------------------
# reef
# ---------------------------------------------------------------------------
def _coral_cluster(d, x, floor, h, col, f, i=0):
    sway = round(wob(f, 1, i))
    for b in range(h):
        bx = x + (1 if b % 2 else -1) + round(sway * b / max(1, h))
        by = floor - b * 3
        d.rectangle([bx, by - 2, bx + 2, by], fill=col)
    tx = x + sway
    d.rectangle([tx - 1, floor - h * 3 - 2, tx + 3, floor - h * 3 + 1], fill=col)


def _kelp(d, x, floor, h, f, i=0):
    for b in range(h * 2):
        bx = x + round(wob(f, 1.6, i + b * 0.3) * b / (h * 2)) + (1 if b % 2 else 0)
        d.point([(bx, floor - b * 2), (bx, floor - b * 2 - 1)], fill=C["plum"])


def draw_bg_reef(d, depth, f):
    """Distant, darker silhouette reef behind the main floor — adds depth."""
    base_y = H - 7
    col = mix(PALETTE["purple"], PALETTE["plum"], 0.55 + depth * 0.2)
    for i, x in enumerate(range(4, W, 12)):
        h = 2 + (i * 3 % 4)
        sway = round(wob(f, 0.7, i))
        for b in range(h):
            d.rectangle([x + sway, base_y - b * 2 - 2, x + sway + 1, base_y - b * 2], fill=col)


def draw_reef_floor(d, depth, f, density=1.0):
    floor = H - 2
    base = mix(PALETTE["purple"], PALETTE["plum"], 0.4 + depth * 0.4)
    d.rectangle([0, floor - 2, W, H], fill=base)
    cols = [C["coral"], C["hotpink"], C["orchid"], C["ember"], C["peach"]]
    spots = [(8, 5), (24, 7), (40, 4), (58, 6), (78, 5), (96, 8),
             (114, 4), (130, 6), (148, 5)]
    for i, (x, h) in enumerate(spots):
        if (i / len(spots)) > density:
            continue
        _coral_cluster(d, x, floor, max(3, int(h * (0.7 + 0.3 * (1 - depth)))), cols[i % len(cols)], f, i)
    for j, x in enumerate((16, 50, 88, 122, 152)):
        _kelp(d, x, floor, 5, f, j)
    sx, sy = 68, floor - 2          # starfish
    for dx, dy in [(0, -2), (-2, 0), (2, 0), (-1, 2), (1, 2)]:
        d.point([(sx + dx, sy + dy)], fill=C["peach"])
    d.ellipse([34, floor - 3, 38, floor], outline=C["coral"])   # snail shell
    d.point([(36, floor - 1)], fill=C["cream"])


# ---------------------------------------------------------------------------
# helper creatures
# ---------------------------------------------------------------------------
def draw_lanternfish(d, x, y, f):
    y = y + round(wob(f, 2, x))
    d.ellipse([x - 4, y - 3, x + 4, y + 3], fill=C["orchid"])
    d.polygon([(x - 4, y), (x - 7, y - 2), (x - 7, y + 2)], fill=C["purple"])
    d.point([(x + 2, y - 1)], fill=C["cream"])
    d.line([(x + 4, y - 3), (x + 7, y - 6)], fill=C["cream"])
    glow = 1 if f % 6 < 3 else 0
    d.ellipse([x + 6, y - 9, x + 10, y - 5], fill=C["ember"])
    d.ellipse([x + 5 - glow, y - 10 - glow, x + 11 + glow, y - 4 + glow],
              outline=mix(PALETTE["ember"], PALETTE["peach"], .5))


def draw_ray(d, x, y, f):
    x = x + round(wob(f, 3))
    flap = round(wob(f, 1))
    d.polygon([(x, y - 3), (x - 11, y + 3 + flap), (x, y + 2), (x + 11, y + 3 + flap)], fill=C["orchid"])
    d.polygon([(x, y - 3), (x - 11, y + 3 + flap), (x - 6, y + 3)], fill=C["purple"])
    d.line([(x, y + 2), (x, y + 9)], fill=C["purple"])
    d.point([(x - 2, y - 1), (x + 2, y - 1)], fill=C["cream"])
    d.point([(x - 1, y + 1), (x + 1, y + 1)], fill=C["plum"])


# ---------------------------------------------------------------------------
# MARLOWE — one sprite, posed + gently floating
# ---------------------------------------------------------------------------
def _limb(d, x0, y0, x1, y1, col):
    d.line([(x0, y0), (x1, y1)], fill=col, width=2)
    d.ellipse([x1 - 1, y1 - 1, x1 + 1, y1 + 1], fill=col)


def draw_marlowe(d, cx, afro_top, pose, f=0):
    afro_top += round(wob(f, 1.5))            # gentle float
    pink, pinks = C["pastelpink"], C["pinkshadow"]
    brn, brs, brh = C["brown"], C["brownshadow"], C["brownhi"]
    if pose == "weary":
        afro_top += 2

    d.ellipse([cx - 10, afro_top + 3, cx + 10, afro_top + 19], fill=pinks)
    d.ellipse([cx - 11, afro_top, cx + 9, afro_top + 17], fill=pink)
    d.point([(cx + 5, afro_top + 2), (cx + 6, afro_top + 1), (cx + 4, afro_top + 1)], fill=C["cream"])

    fy = afro_top + 9
    d.ellipse([cx - 6, fy, cx + 6, fy + 12], fill=brn)
    d.ellipse([cx - 6, fy, cx - 3, fy + 12], fill=brs)
    d.point([(cx + 4, fy + 4), (cx + 4, fy + 5)], fill=brh)
    eye_dx = 1 if pose == "pensive" else 0
    d.point([(cx - 2 + eye_dx, fy + 5), (cx + 3 + eye_dx, fy + 5)], fill=C["plum"])
    d.point([(cx - 4, fy + 7), (cx + 4, fy + 7)], fill=C["coral"])
    if pose == "weary":
        d.line([(cx - 2, fy + 8), (cx + 2, fy + 8)], fill=C["plum"])
    else:
        d.point([(cx - 1, fy + 8), (cx, fy + 9), (cx + 1, fy + 8)], fill=C["plum"])

    ty = fy + 12
    d.ellipse([cx - 8, ty, cx + 8, ty + 11], fill=brn)
    d.ellipse([cx - 8, ty, cx - 4, ty + 11], fill=brs)
    d.rectangle([cx - 8, ty + 3, cx + 8, ty + 6], fill=C["coral"])
    d.line([(cx - 5, ty), (cx - 5, ty + 3)], fill=C["coral"])
    d.line([(cx + 4, ty), (cx + 4, ty + 3)], fill=C["coral"])

    tail_top = ty + 10
    for k in range(16):
        y = tail_top + k
        w = max(2, 7 - k // 3)
        sway = round(wob(f, 1.2, k * 0.5)) if k > 4 else (1 if (k // 3) % 2 else 0)
        col = C["orchid"] if k < 5 else C["coral"] if k < 10 else C["peach"]
        d.line([(cx - w + sway, y), (cx + w + sway, y)], fill=col)
        if k % 3 == 1:
            d.point([(cx + sway, y)], fill=C["cream"])
    fy2 = tail_top + 16
    tsway = round(wob(f, 1.5, 8))
    d.polygon([(cx + tsway, fy2 - 2), (cx - 9 + tsway, fy2 + 4), (cx - 2 + tsway, fy2 + 1)], fill=C["peach"])
    d.polygon([(cx + tsway, fy2 - 2), (cx + 9 + tsway, fy2 + 4), (cx + 2 + tsway, fy2 + 1)], fill=C["peach"])

    lsh, rsh = (cx - 6, ty + 2), (cx + 6, ty + 2)
    hands = {
        "hauling":  ((cx - 4, ty + 9), (cx + 4, ty + 9)),
        "curious":  ((cx - 9, ty + 6), (cx + 9, ty - 1)),
        "pensive":  ((cx - 9, ty + 6), (cx + 4, fy + 9)),
        "straining":((cx - 5, afro_top - 3), (cx + 5, afro_top - 3)),
        "joyful":   ((cx - 12, afro_top + 1), (cx + 12, afro_top + 1)),
        "weary":    ((cx - 8, ty + 9), (cx + 8, ty + 9)),
        "swimming": ((cx - 10, ty + 8), (cx + 12, afro_top + 6)),
    }.get(pose, ((cx - 9, ty + 6), (cx + 9, ty + 6)))
    _limb(d, *lsh, *hands[0], brn)
    _limb(d, *rsh, *hands[1], brn)

    if pose == "hauling":
        nx, ny = cx, ty + 12
        d.line([(cx - 4, ty + 8), (nx - 4, ny)], fill=C["cream"])
        d.line([(cx + 4, ty + 8), (nx + 4, ny)], fill=C["cream"])
        d.ellipse([nx - 5, ny, nx + 5, ny + 8], outline=C["cream"])
        for gx in range(nx - 3, nx + 4, 2):
            d.point([(gx, ny + 3), (gx, ny + 5)], fill=C["cream"])
        draw_fish(d, nx - 1, ny + 4, f, "peach")


# ---------------------------------------------------------------------------
# CASS — white, blonde-ponytail diver, sized to match Marlowe, floating
# ---------------------------------------------------------------------------
def draw_cass(d, cx, top, pose="meeting", face=-1, f=0):
    top += round(wob(f, 1.5, 1.0))
    blonde, blonde_sh = C["blonde"], hex_to_rgb("#D8B45C")
    suit, suit_sh = C["orchid"], C["purple"]

    px = cx - face * 7
    d.ellipse([px - 3, top + 1, px + 3, top + 9], fill=blonde)
    d.rectangle([px - 2, top + 7, px + 2, top + 17], fill=blonde)
    d.line([(px, top + 7), (px, top + 17)], fill=blonde_sh)
    d.point([(px, top + 16)], fill=C["peach"])

    d.ellipse([cx - 6, top, cx + 6, top + 13], fill=SKIN)
    d.ellipse([cx - 6, top, cx - 3, top + 13], fill=SKIN_SH)
    d.ellipse([cx - 6, top - 1, cx + 6, top + 4], fill=blonde)
    d.rectangle([cx - 6, top + 4, cx + 6, top + 9], fill=mix(PALETTE["cream"], PALETTE["orchid"], .35))
    d.rectangle([cx - 6, top + 4, cx + 6, top + 5], fill=C["coral"])
    d.point([(cx - 2, top + 6), (cx + 2, top + 6)], fill=C["plum"])
    d.point([(cx - 4, top + 10), (cx + 4, top + 10)], fill=C["coral"])
    d.point([(cx - 1, top + 11), (cx, top + 11), (cx + 1, top + 11)], fill=C["plum"])

    ty = top + 13
    d.ellipse([cx - 6, ty, cx + 6, ty + 16], fill=suit)
    d.ellipse([cx - 6, ty, cx - 3, ty + 16], fill=suit_sh)
    tkx = cx - face * 6
    d.rectangle([tkx - 1, ty + 1, tkx + 1, ty + 11], fill=mix(PALETTE["cream"], PALETTE["plum"], .2))
    d.point([(tkx, ty + 4)], fill=C["hotpink"])

    lsh, rsh = (cx - 5, ty + 2), (cx + 5, ty + 2)
    if pose == "offering-hand":
        hx, hy = cx + face * 12, ty + 6
        _limb(d, cx + face * 5, ty + 2, hx, hy, suit)
        d.ellipse([hx - 1, hy - 1, hx + 1, hy + 1], fill=SKIN)
        _limb(d, cx - face * 5, ty + 2, cx - face * 7, ty + 10, suit)
    elif pose == "together-joyful":
        _limb(d, *lsh, cx - 11, ty - 2, suit)
        _limb(d, *rsh, cx + 11, ty - 2, suit)
    else:
        _limb(d, *lsh, cx - 8, ty + 10, suit)
        _limb(d, *rsh, cx + 8, ty + 10, suit)

    ly = ty + 16
    d.line([(cx - 2, ly), (cx - 3, ly + 10)], fill=suit, width=2)
    d.line([(cx + 2, ly), (cx + 3, ly + 10)], fill=suit, width=2)
    d.polygon([(cx - 6, ly + 10), (cx - 1, ly + 9), (cx - 3, ly + 15)], fill=C["ember"])
    d.polygon([(cx + 1, ly + 9), (cx + 6, ly + 10), (cx + 3, ly + 15)], fill=C["ember"])
    draw_bubbles(d, cx + face * 8, ty, f, 3, rng=18)


# ---------------------------------------------------------------------------
# frame + emit
# ---------------------------------------------------------------------------
def cozy_frame(scene: Image.Image, title: str) -> Image.Image:
    sw, sh = scene.size
    card = Image.new("RGB", (sw + BORDER * 2, sh + BORDER * 2 + BAR_H), C["cream"])
    d = ImageDraw.Draw(card)
    for x in range(BORDER, sw + BORDER):
        t = (x - BORDER) / max(1, sw)
        d.line([(x, BORDER), (x, BORDER + BAR_H - 1)], fill=mix(PALETTE["hotpink"], PALETTE["coral"], t))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
    d.text((BORDER + 6, BORDER + 3), title, fill=C["cream"], font=font)
    for i in range(2):
        bx = sw + BORDER - 12 - i * 12
        d.rectangle([bx, BORDER + 5, bx + 7, BORDER + 12], fill=C["cream"])
    card.paste(scene, (BORDER, BORDER + BAR_H))
    return card


def emit(name, builder):
    frames = [cozy_frame(scale(builder(f), FACTOR), TITLE) for f in range(N)]
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.gif")
    export_gif(frames, path, duration=DUR)
    return path, os.path.getsize(path)


# ---------------------------------------------------------------------------
# the panels  (each builder(f) -> one logical frame)
# ---------------------------------------------------------------------------
def b_start(f):
    img = draw_sky(0.1)
    d = ImageDraw.Draw(img)
    draw_clouds(d, [(24, 12), (104, 8)])
    draw_stars(d, [(18, 10), (140, 14), (70, 8)], f)
    draw_sun(d, 122, 26)
    draw_godrays(d, 122, 30, f)
    wl = 46
    draw_reflection(d, 122, wl + 2, 0.1, f)
    draw_waterline(d, wl)
    draw_bg_reef(d, 0.1, f)
    draw_reef_floor(d, 0.1, f, 1.0)
    draw_school(d, 96, 66, f, "peach")
    draw_fish(d, 60, 80, f, "cream", flip=True, phase=2)
    d.point([(140, 86), (141, 85), (139, 85)], fill=C["cream"])
    d.ellipse([138, 83, 143, 88], outline=C["peach"])
    draw_bubbles(d, 132, 84, f, 4, rng=22)
    draw_marlowe(d, 44, 30, "hauling", f)
    return img


def b_meet(f):
    img = draw_sky(0.4)
    d = ImageDraw.Draw(img)
    draw_stars(d, [(30, 16), (130, 22), (80, 12), (60, 20)], f)
    draw_particles(d, [(46, 50), (140, 44), (90, 60)], f)
    draw_bg_reef(d, 0.4, f)
    draw_reef_floor(d, 0.4, f, 1.0)
    draw_jelly(d, 24, 40, f, "coral")
    draw_school(d, 84, 58, f, "coral")
    draw_marlowe(d, 48, 34, "curious", f)
    draw_cass(d, 116, 34, "meeting", -1, f)
    draw_bubbles(d, 70, 70, f, 3, rng=30, phase=4)
    return img


def b_alone_early(f):
    img = draw_sky(0.2)
    d = ImageDraw.Draw(img)
    draw_sun(d, 120, 28)
    draw_godrays(d, 120, 32, f)
    draw_waterline(d, 48)
    draw_reflection(d, 120, 50, 0.2, f)
    draw_bg_reef(d, 0.2, f)
    draw_reef_floor(d, 0.2, f, 1.0)
    draw_school(d, 80, 74, f, "peach", flip=True)
    draw_marlowe(d, 48, 32, "pensive", f)
    draw_cass(d, 132, 40, "guiding", 1, f)
    return img


def b_deep(f):
    img = draw_sky(0.8)
    d = ImageDraw.Draw(img)
    draw_particles(d, [(40, 50), (120, 44), (90, 60), (60, 40), (130, 70)], f)
    draw_bg_reef(d, 0.8, f)
    draw_reef_floor(d, 0.8, f, 0.5)
    d.rectangle([72, 86, 88, 94], fill=mix(PALETTE["ember"], PALETTE["plum"], .4))
    d.line([(72, 89), (88, 89)], fill=C["peach"])
    draw_lanternfish(d, 96, 50, f)
    draw_ray(d, 30, 64, f)
    draw_jelly(d, 138, 54, f, "orchid")
    draw_marlowe(d, 70, 26, "straining", f)
    draw_bubbles(d, 50, 80, f, 3, rng=40)
    return img


def b_together(f):
    img = draw_sky(0.7)
    d = ImageDraw.Draw(img)
    draw_glow(d, 80, 78, 46, f, "ember", "plum")
    draw_particles(d, [(40, 50), (120, 50), (70, 40)], f)
    draw_bg_reef(d, 0.7, f)
    draw_reef_floor(d, 0.7, f, 0.6)
    draw_lanternfish(d, 30, 44, f)
    draw_ray(d, 128, 58, f)
    draw_school(d, 100, 30, f, "peach")
    draw_marlowe(d, 56, 30, "swimming", f)
    draw_cass(d, 102, 30, "guiding", -1, f)
    return img


def b_alone(f):
    img = draw_sky(0.9)
    d = ImageDraw.Draw(img)
    draw_particles(d, [(40, 50), (120, 44), (90, 60), (70, 70)], f)
    draw_bg_reef(d, 0.9, f)
    draw_reef_floor(d, 0.9, f, 0.4)
    d.rectangle([62, 84, 86, 96], fill=mix(PALETTE["ember"], PALETTE["plum"], .5))
    d.rectangle([62, 84, 86, 87], fill=C["ember"])
    d.point([(74, 90)], fill=C["peach"])
    draw_marlowe(d, 56, 36, "weary", f)
    draw_cass(d, 106, 34, "offering-hand", -1, f)
    return img


def b_end_pearl(f):
    img = draw_sky(0.55)
    d = ImageDraw.Draw(img)
    draw_glow(d, 80, 82, 52, f, "peach", "plum")
    draw_stars(d, [(24, 20), (138, 18), (44, 14)], f)
    draw_particles(d, [(40, 50), (120, 50)], f)
    draw_bg_reef(d, 0.55, f)
    draw_reef_floor(d, 0.55, f, 0.6)
    d.rectangle([66, 80, 94, 96], fill=mix(PALETTE["ember"], PALETTE["plum"], .5))
    d.polygon([(66, 80), (94, 80), (90, 74), (70, 74)], fill=C["orchid"])
    pr = 4 + (1 if f % 6 < 3 else 0)
    d.ellipse([80 - pr, 84 - pr, 80 + pr, 84 + pr], fill=C["cream"])
    d.ellipse([74, 78, 86, 90], outline=mix(PALETTE["cream"], PALETTE["peach"], .5))
    draw_school(d, 120, 40, f, "coral")
    draw_marlowe(d, 50, 28, "joyful", f)
    draw_cass(d, 106, 30, "together-joyful", -1, f)
    return img


def b_end_tired(f):
    img = draw_sky(0.9)
    d = ImageDraw.Draw(img)
    draw_particles(d, [(40, 50), (120, 44), (90, 60)], f)
    draw_bg_reef(d, 0.9, f)
    draw_reef_floor(d, 0.9, f, 0.4)
    d.rectangle([56, 82, 80, 96], fill=mix(PALETTE["ember"], PALETTE["plum"], .55))
    d.polygon([(56, 82), (80, 82), (76, 76), (60, 76)], fill=C["purple"])
    d.ellipse([64, 83, 70, 89], fill=mix(PALETTE["cream"], PALETTE["plum"], .35))
    draw_marlowe(d, 52, 42, "weary", f)
    draw_cass(d, 128, 34, "guiding", 1, f)
    return img


def b_end_driftaway(f):
    img = draw_sky(0.15)
    d = ImageDraw.Draw(img)
    draw_clouds(d, [(30, 12), (110, 10)])
    draw_stars(d, [(20, 14), (96, 10)], f)
    draw_sun(d, 124, 26)
    draw_godrays(d, 124, 30, f)
    draw_waterline(d, 48)
    draw_reflection(d, 124, 50, 0.15, f)
    draw_bg_reef(d, 0.15, f)
    draw_reef_floor(d, 0.15, f, 1.0)
    draw_school(d, 90, 72, f, "peach")
    d.point([(132, 84)], fill=mix(PALETTE["cream"], PALETTE["plum"], .4))
    draw_bubbles(d, 120, 80, f, 3, rng=24)
    draw_marlowe(d, 60, 40, "swimming", f)
    return img


PANELS = {
    "start": b_start, "meet": b_meet, "alone-early": b_alone_early,
    "deep": b_deep, "together": b_together, "alone": b_alone,
    "ending-pearl": b_end_pearl, "ending-tired": b_end_tired,
    "ending-driftaway": b_end_driftaway,
}


def main(which=None):
    for n in ([which] if which else list(PANELS)):
        path, sz = emit(n, PANELS[n])
        print(f"{n:18} -> {os.path.relpath(path, ROOT)} ({sz/1024:.1f} KB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
