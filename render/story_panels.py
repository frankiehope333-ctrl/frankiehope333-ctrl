"""render/story_panels.py — programmatic pixel scenes for "The Deep Dive".

One static PNG per story page, drawn with the SAME sprite system as the reef &
creature (render/sprites.py). No AI image gen — Marlowe is the same sprite data on
every page, so she never drifts (STORY-PANELS.md). Crisp grid pixels: draw small,
scale up with NEAREST.

  python render/story_panels.py start       # render one panel (verify it first)
  python render/story_panels.py             # render all panels
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import PALETTE, hex_to_rgb, scale, mix, vertical_gradient  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "adventure")

W, H, FACTOR = 160, 104, 5
BAR_H, BORDER = 16, 2

C = {k: hex_to_rgb(v) for k, v in PALETTE.items()}


# ---------------------------------------------------------------------------
# scene base
# ---------------------------------------------------------------------------
def draw_sky(depth: float) -> Image.Image:
    """Vertical gradient; depth 0 = bright surface sunset, 1 = deep plum dark."""
    top = mix("#3a2356", "#100a18", depth)
    umid = mix(PALETTE["purple"], "#1c1230", depth)
    lmid = mix(PALETTE["hotpink"], "#3a1d40", depth)
    bot = mix(PALETTE["peach"], PALETTE["plum"], depth)
    return vertical_gradient(W, H, [(0.0, _hx(top)), (0.34, _hx(umid)),
                                    (0.66, _hx(lmid)), (1.0, _hx(bot))])


def _hx(rgb):
    return "#%02X%02X%02X" % rgb


def draw_sun(d, x, y, r=7):
    d.ellipse([x - r - 1, y - r - 1, x + r + 1, y + r + 1], fill=mix(PALETTE["ember"], PALETTE["peach"], .4))
    d.ellipse([x - r, y - r, x + r, y + r], fill=C["ember"])


def draw_reflection(d, sun_x, y0, depth):
    """Full-width wavelet shimmer across the whole surface (not partial lines)."""
    rows = range(y0, min(y0 + 18, H - 18), 2)
    for i, y in enumerate(rows):
        fade = 1 - i / max(1, len(list(rows)))
        col = mix(PALETTE["peach"], PALETTE["hotpink"], 1 - fade)
        offset = (i * 3) % 6
        for x in range(offset, W, 6):
            # brighter near the sun column
            near = max(0, 1 - abs(x - sun_x) / 70)
            c = mix(_hx(col), PALETTE["ember"], near * 0.5)
            d.line([(x, y), (x + 2, y)], fill=c)


def draw_waterline(d, y):
    d.line([(0, y), (W, y)], fill=C["coral"])
    for x in range(0, W, 7):
        d.point([(x, y - 1), (x + 3, y - 1)], fill=C["cream"])
    d.line([(0, y + 1), (W, y + 1)], fill=mix(PALETTE["hotpink"], PALETTE["plum"], .3))


def draw_stars(d, pts):
    for (x, y) in pts:
        d.point([(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y), (x, y)], fill=C["peach"])


def draw_clouds(d, pts):
    for (x, y) in pts:
        d.rectangle([x, y + 2, x + 9, y + 3], fill=C["cream"])
        d.rectangle([x + 2, y, x + 4, y + 2], fill=C["cream"])
        d.rectangle([x + 5, y + 1, x + 7, y + 2], fill=C["cream"])


def draw_glow(d, cx, cy, r, inner="peach", outer="plum"):
    """Soft radial warm-light: concentric ellipses, dark at the edge -> bright
    center, so it blends into the deep water instead of being a flat blob."""
    for i in range(r, 0, -1):
        t = i / r
        col = mix(PALETTE[inner], PALETTE[outer], t ** 0.7)
        d.ellipse([cx - i, cy - int(i * 0.62), cx + i, cy + int(i * 0.62)], fill=col)


def draw_bubbles(d, x, y0, n=4):
    for i in range(n):
        y = y0 - i * 5
        r = 1 if i % 2 else 0
        d.ellipse([x - r, y - r, x + r, y + r], outline=C["cream"])


def _coral_cluster(d, x, floor, h, col):
    for b in range(h):
        bx = x + (1 if b % 2 else -1)
        by = floor - b * 3
        d.rectangle([bx, by - 2, bx + 2, by], fill=col)
    d.rectangle([x - 1, floor - h * 3 - 2, x + 3, floor - h * 3 + 1], fill=col)


def _kelp(d, x, floor, h):
    for b in range(h * 2):
        bx = x + (1 if b % 2 else 0)
        d.point([(bx, floor - b * 2), (bx, floor - b * 2 - 1)], fill=C["plum"])


def draw_reef_floor(d, depth, density=1.0):
    """A FULL sea floor: varied coral, kelp, a starfish — packed, not sparse."""
    floor = H - 2
    base = mix(PALETTE["purple"], PALETTE["plum"], 0.4 + depth * 0.4)
    d.rectangle([0, floor - 2, W, H], fill=base)
    cols = [C["coral"], C["hotpink"], C["orchid"], C["ember"], C["peach"]]
    spots = [(8, 5), (24, 7), (40, 4), (58, 6), (78, 5), (96, 8),
             (114, 4), (130, 6), (148, 5)]
    for i, (x, h) in enumerate(spots):
        if (i / len(spots)) > density:
            continue
        _coral_cluster(d, x, floor, max(3, int(h * (0.7 + 0.3 * (1 - depth)))), cols[i % len(cols)])
    for x in (16, 50, 88, 122, 152):
        _kelp(d, x, floor, 5)
    # a little starfish
    sx, sy = 68, floor - 2
    for dx, dy in [(0, -2), (-2, 0), (2, 0), (-1, 2), (1, 2)]:
        d.point([(sx + dx, sy + dy)], fill=C["peach"])


def draw_fish(d, x, y, hue="coral", flip=False):
    body = C.get(hue, C["coral"])
    s = -1 if flip else 1
    d.ellipse([x - 3, y - 2, x + 3, y + 2], fill=body)
    d.polygon([(x - 3 * s, y), (x - 6 * s, y - 2), (x - 6 * s, y + 2)], fill=C["hotpink"])
    d.point([(x + 1 * s, y - 1)], fill=C["plum"])  # eye


# ---------------------------------------------------------------------------
# MARLOWE — one sprite, posed per page. (STORY-PANELS.md §3)
# ---------------------------------------------------------------------------
def _limb(d, x0, y0, x1, y1, col):
    d.line([(x0, y0), (x1, y1)], fill=col, width=2)
    d.ellipse([x1 - 1, y1 - 1, x1 + 1, y1 + 1], fill=col)


def draw_marlowe(d, cx, afro_top, pose="curious"):
    pink, pinks = C["pastelpink"], C["pinkshadow"]
    brn, brs, brh = C["brown"], C["brownshadow"], C["brownhi"]

    if pose == "weary":
        afro_top += 2  # slumped

    # ---- Afro (big, round, signature) ----
    d.ellipse([cx - 10, afro_top + 3, cx + 10, afro_top + 19], fill=pinks)   # shadow
    d.ellipse([cx - 11, afro_top, cx + 9, afro_top + 17], fill=pink)         # main
    d.point([(cx + 5, afro_top + 2), (cx + 6, afro_top + 1),
             (cx + 4, afro_top + 1)], fill=C["cream"])                       # sparkle

    # ---- Face (brown, framed by afro) ----
    fy = afro_top + 9
    d.ellipse([cx - 6, fy, cx + 6, fy + 12], fill=brn)
    d.ellipse([cx - 6, fy, cx - 3, fy + 12], fill=brs)     # left shadow
    d.point([(cx + 4, fy + 4), (cx + 4, fy + 5)], fill=brh)  # cheek highlight
    eye_dx = 1 if pose == "pensive" else 0   # glance
    d.point([(cx - 2 + eye_dx, fy + 5), (cx + 3 + eye_dx, fy + 5)], fill=C["plum"])  # eyes
    d.point([(cx - 4, fy + 7), (cx + 4, fy + 7)], fill=C["coral"])                   # blush
    if pose == "weary":
        d.line([(cx - 2, fy + 8), (cx + 2, fy + 8)], fill=C["plum"])  # flat mouth
    else:
        d.point([(cx - 1, fy + 8), (cx, fy + 9), (cx + 1, fy + 8)], fill=C["plum"])  # smile

    # ---- Torso (plus-sized) + coral top ----
    ty = fy + 12
    d.ellipse([cx - 8, ty, cx + 8, ty + 11], fill=brn)        # soft round torso
    d.ellipse([cx - 8, ty, cx - 4, ty + 11], fill=brs)        # shadow side
    d.rectangle([cx - 8, ty + 3, cx + 8, ty + 6], fill=C["coral"])   # top band
    d.line([(cx - 5, ty), (cx - 5, ty + 3)], fill=C["coral"])        # straps
    d.line([(cx + 4, ty), (cx + 4, ty + 3)], fill=C["coral"])

    # ---- Tail (sunset gradient, scale dots, two-lobe fin) ----
    tail_top = ty + 10
    for i in range(16):
        y = tail_top + i
        w = max(2, 7 - i // 3)
        sway = 1 if (i // 3) % 2 else 0   # gentle S
        col = C["orchid"] if i < 5 else C["coral"] if i < 10 else C["peach"]
        d.line([(cx - w + sway, y), (cx + w + sway, y)], fill=col)
        if i % 3 == 1:
            d.point([(cx + sway, y)], fill=C["cream"])  # scale dot
    fy2 = tail_top + 16
    d.polygon([(cx, fy2 - 2), (cx - 9, fy2 + 4), (cx - 2, fy2 + 1)], fill=C["peach"])
    d.polygon([(cx, fy2 - 2), (cx + 9, fy2 + 4), (cx + 2, fy2 + 1)], fill=C["peach"])

    # ---- Arms (pose-dependent) ----
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
        # a small net bag of catch hanging from her hands
        nx, ny = cx, ty + 12
        d.line([(cx - 4, ty + 8), (nx - 4, ny)], fill=C["cream"])   # ropes
        d.line([(cx + 4, ty + 8), (nx + 4, ny)], fill=C["cream"])
        d.ellipse([nx - 5, ny, nx + 5, ny + 8], outline=C["cream"])  # bag
        for gx in range(nx - 3, nx + 4, 2):
            d.point([(gx, ny + 3), (gx, ny + 5)], fill=C["cream"])   # mesh
        draw_fish(d, nx - 1, ny + 4, "peach")


# ---------------------------------------------------------------------------
# CASS — blonde-ponytail diver, equal companion (never above Marlowe)
# ---------------------------------------------------------------------------
def draw_cass(d, cx, top, pose="meeting", face=-1):
    """White, blonde-ponytail diver — sized to match Marlowe (~50px tall), an
    equal companion. face = -1 looks left (toward Marlowe on her right), +1 right."""
    skin = (245, 208, 184)       # pale / white skin
    skin_sh = (214, 173, 150)
    blonde, blonde_sh = C["blonde"], hex_to_rgb("#D8B45C")
    suit, suit_sh = C["orchid"], C["purple"]

    # ---- ponytail out the back (opposite facing) ----
    px = cx - face * 7
    d.ellipse([px - 3, top + 1, px + 3, top + 9], fill=blonde)
    d.rectangle([px - 2, top + 7, px + 2, top + 17], fill=blonde)
    d.line([(px, top + 7), (px, top + 17)], fill=blonde_sh)
    d.point([(px, top + 16)], fill=C["peach"])

    # ---- head + blonde fringe + mask ----
    d.ellipse([cx - 6, top, cx + 6, top + 13], fill=skin)
    d.ellipse([cx - 6, top, cx - 3, top + 13], fill=skin_sh)          # shadow side
    d.ellipse([cx - 6, top - 1, cx + 6, top + 4], fill=blonde)        # fringe
    d.rectangle([cx - 6, top + 4, cx + 6, top + 9],
                fill=mix(PALETTE["cream"], PALETTE["orchid"], .35))   # mask glass
    d.rectangle([cx - 6, top + 4, cx + 6, top + 5], fill=C["coral"])  # strap
    d.point([(cx - 2, top + 6), (cx + 2, top + 6)], fill=C["plum"])   # eyes
    d.point([(cx - 4, top + 10), (cx + 4, top + 10)], fill=C["coral"])  # shy blush
    d.point([(cx - 1, top + 11), (cx, top + 11), (cx + 1, top + 11)], fill=C["plum"])  # smile

    # ---- torso (wetsuit) + tank ----
    ty = top + 13
    d.ellipse([cx - 6, ty, cx + 6, ty + 16], fill=suit)
    d.ellipse([cx - 6, ty, cx - 3, ty + 16], fill=suit_sh)
    tkx = cx - face * 6
    d.rectangle([tkx - 1, ty + 1, tkx + 1, ty + 11],
                fill=mix(PALETTE["cream"], PALETTE["plum"], .2))      # air tank
    d.point([(tkx, ty + 4)], fill=C["hotpink"])                      # heart sticker

    # ---- arms (pose) ----
    lsh, rsh = (cx - 5, ty + 2), (cx + 5, ty + 2)
    if pose == "offering-hand":
        hx, hy = cx + face * 12, ty + 6                              # reach toward Marlowe
        _limb(d, cx + face * 5, ty + 2, hx, hy, suit)
        d.ellipse([hx - 1, hy - 1, hx + 1, hy + 1], fill=skin)       # open hand
        _limb(d, cx - face * 5, ty + 2, cx - face * 7, ty + 10, suit)
    elif pose == "together-joyful":
        _limb(d, *lsh, cx - 11, ty - 2, suit)
        _limb(d, *rsh, cx + 11, ty - 2, suit)
    else:
        _limb(d, *lsh, cx - 8, ty + 10, suit)
        _limb(d, *rsh, cx + 8, ty + 10, suit)

    # ---- legs + fins ----
    ly = ty + 16
    d.line([(cx - 2, ly), (cx - 3, ly + 10)], fill=suit, width=2)
    d.line([(cx + 2, ly), (cx + 3, ly + 10)], fill=suit, width=2)
    d.polygon([(cx - 6, ly + 10), (cx - 1, ly + 9), (cx - 3, ly + 15)], fill=C["ember"])
    d.polygon([(cx + 1, ly + 9), (cx + 6, ly + 10), (cx + 3, ly + 15)], fill=C["ember"])

    draw_bubbles(d, cx + face * 8, ty, 3)


def draw_lanternfish(d, x, y):
    d.ellipse([x - 4, y - 3, x + 4, y + 3], fill=C["orchid"])
    d.polygon([(x - 4, y), (x - 7, y - 2), (x - 7, y + 2)], fill=C["purple"])
    d.point([(x + 2, y - 1)], fill=C["cream"])  # eye
    # lantern on a stalk, glowing
    d.line([(x + 4, y - 3), (x + 7, y - 6)], fill=C["cream"])
    d.ellipse([x + 6, y - 9, x + 10, y - 5], fill=C["ember"])
    d.ellipse([x + 5, y - 10, x + 11, y - 4], outline=mix(PALETTE["ember"], PALETTE["peach"], .5))


def draw_ray(d, x, y):
    d.polygon([(x, y - 3), (x - 11, y + 3), (x, y + 2), (x + 11, y + 3)], fill=C["orchid"])
    d.polygon([(x, y - 3), (x - 11, y + 3), (x - 6, y + 3)], fill=C["purple"])
    d.line([(x, y + 2), (x, y + 9)], fill=C["purple"])  # tail
    d.point([(x - 2, y - 1), (x + 2, y - 1)], fill=C["cream"])  # eyes
    d.point([(x - 1, y + 1), (x + 1, y + 1)], fill=C["plum"])


# ---------------------------------------------------------------------------
# frame + compose
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


def _save(img, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.png")
    img.save(path)
    return path, os.path.getsize(path)


# ---------------------------------------------------------------------------
# the panels
# ---------------------------------------------------------------------------
def panel_start():
    img = draw_sky(0.1)
    d = ImageDraw.Draw(img)
    draw_clouds(d, [(24, 12), (104, 8)])
    draw_stars(d, [(18, 10), (140, 14), (70, 8)])
    draw_sun(d, 122, 26)
    wl = 46
    draw_reflection(d, 122, wl + 2, 0.1)
    draw_waterline(d, wl)
    draw_reef_floor(d, 0.1, 1.0)
    draw_fish(d, 96, 70, "peach")
    draw_fish(d, 60, 80, "cream", flip=True)
    # the glint + bubble stream far below-right
    d.point([(140, 86), (141, 85), (139, 85)], fill=C["cream"])
    d.ellipse([138, 83, 143, 88], outline=C["peach"])
    draw_bubbles(d, 132, 84, 4)
    draw_marlowe(d, 44, 30, "hauling")
    return cozy_frame(scale(img, FACTOR), "🌙 the deep dive")


def panel_meet():
    img = draw_sky(0.4)
    d = ImageDraw.Draw(img)
    draw_stars(d, [(30, 16), (130, 22), (80, 12)])
    draw_reef_floor(d, 0.4, 1.0)
    draw_fish(d, 80, 60, "coral")
    draw_marlowe(d, 48, 34, "curious")
    draw_cass(d, 116, 34, "meeting", face=-1)
    return cozy_frame(scale(img, FACTOR), "🌙 the deep dive")


def panel_alone_early():
    img = draw_sky(0.2)
    d = ImageDraw.Draw(img)
    draw_sun(d, 120, 28)
    draw_waterline(d, 48)
    draw_reflection(d, 120, 50, 0.2)
    draw_reef_floor(d, 0.2, 1.0)
    draw_marlowe(d, 48, 32, "pensive")
    # Cass swimming away (facing away), full-size but off toward the edge
    draw_cass(d, 132, 40, "guiding", face=1)
    return cozy_frame(scale(img, FACTOR), "🌙 the deep dive")


def panel_deep():
    img = draw_sky(0.8)
    d = ImageDraw.Draw(img)
    draw_reef_floor(d, 0.8, 0.5)
    # faint chest below
    d.rectangle([72, 86, 88, 94], fill=mix(PALETTE["ember"], PALETTE["plum"], .4))
    d.line([(72, 89), (88, 89)], fill=C["peach"])
    draw_lanternfish(d, 96, 50)
    draw_ray(d, 30, 64)
    draw_marlowe(d, 70, 26, "straining")
    return cozy_frame(scale(img, FACTOR), "🌙 the deep dive")


def panel_together():
    img = draw_sky(0.7)
    d = ImageDraw.Draw(img)
    draw_glow(d, 80, 78, 46, inner="ember", outer="plum")  # warm light breaking the dark
    draw_reef_floor(d, 0.7, 0.6)
    draw_lanternfish(d, 30, 44)
    draw_ray(d, 128, 58)
    draw_marlowe(d, 56, 30, "swimming")
    draw_cass(d, 102, 30, "guiding", face=-1)
    return cozy_frame(scale(img, FACTOR), "🌙 the deep dive")


def panel_alone():
    img = draw_sky(0.9)
    d = ImageDraw.Draw(img)
    draw_reef_floor(d, 0.9, 0.4)
    # the treasure chest
    d.rectangle([62, 84, 86, 96], fill=mix(PALETTE["ember"], PALETTE["plum"], .5))
    d.rectangle([62, 84, 86, 87], fill=C["ember"])
    d.point([(74, 90)], fill=C["peach"])
    draw_marlowe(d, 56, 36, "weary")
    draw_cass(d, 106, 34, "offering-hand", face=-1)
    return cozy_frame(scale(img, FACTOR), "🌙 the deep dive")


def panel_end_pearl():
    img = draw_sky(0.55)  # warming back up
    d = ImageDraw.Draw(img)
    draw_glow(d, 80, 82, 52, inner="peach", outer="plum")  # pearl light flooding warm
    draw_reef_floor(d, 0.55, 0.6)
    draw_stars(d, [(24, 20), (138, 18)])
    # open chest + glowing pearl
    d.rectangle([66, 80, 94, 96], fill=mix(PALETTE["ember"], PALETTE["plum"], .5))
    d.polygon([(66, 80), (94, 80), (90, 74), (70, 74)], fill=C["orchid"])  # open lid
    d.ellipse([76, 80, 84, 88], fill=C["cream"])
    d.ellipse([74, 78, 86, 90], outline=mix(PALETTE["cream"], PALETTE["peach"], .5))
    draw_marlowe(d, 50, 28, "joyful")
    draw_cass(d, 106, 30, "together-joyful", face=-1)
    return cozy_frame(scale(img, FACTOR), "🌙 the deep dive")


def panel_end_tired():
    img = draw_sky(0.9)
    d = ImageDraw.Draw(img)
    draw_reef_floor(d, 0.9, 0.4)
    d.rectangle([56, 82, 80, 96], fill=mix(PALETTE["ember"], PALETTE["plum"], .55))
    d.polygon([(56, 82), (80, 82), (76, 76), (60, 76)], fill=C["purple"])
    d.ellipse([64, 83, 70, 89], fill=mix(PALETTE["cream"], PALETTE["plum"], .35))  # dull pearl
    draw_marlowe(d, 52, 42, "weary")
    draw_cass(d, 128, 34, "guiding", face=1)  # drifting away (facing away, toward the edge)
    return cozy_frame(scale(img, FACTOR), "🌙 the deep dive")


def panel_end_driftaway():
    img = draw_sky(0.15)
    d = ImageDraw.Draw(img)
    draw_clouds(d, [(30, 12), (110, 10)])
    draw_sun(d, 124, 26)
    draw_waterline(d, 48)
    draw_reflection(d, 124, 50, 0.15)
    draw_reef_floor(d, 0.15, 1.0)
    # the glint fading, bubbles moving on
    d.point([(132, 84)], fill=mix(PALETTE["cream"], PALETTE["plum"], .4))
    draw_bubbles(d, 120, 80, 3)
    draw_marlowe(d, 60, 40, "swimming")
    return cozy_frame(scale(img, FACTOR), "🌙 the deep dive")


PANELS = {
    "start": panel_start, "meet": panel_meet, "alone-early": panel_alone_early,
    "deep": panel_deep, "together": panel_together, "alone": panel_alone,
    "ending-pearl": panel_end_pearl, "ending-tired": panel_end_tired,
    "ending-driftaway": panel_end_driftaway,
}


def main(which=None):
    names = [which] if which else list(PANELS)
    for n in names:
        path, sz = _save(PANELS[n](), n)
        print(f"{n:18} -> {os.path.relpath(path, ROOT)} ({sz/1024:.1f} KB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
