"""render/sprites.py — the palette + pixel-drawing primitives.

Single source of truth for color and for how we draw chunky pixel art. Every
renderer (reef_gif, bottle_gif, creature_gif, scrapbook) imports from here so the
whole world stays visually consistent. See PROFILE-SPEC.md "ILLUSTRATION STYLE".

The technique (BUILD.md §3a):
  1. Draw on a small, coarse logical grid (e.g. 24x24) with few colors.
  2. Scale up with Image.NEAREST so pixels stay crisp & blocky, never blurred.
  3. Animate with a sine offset per-sprite (different phase => not in lockstep).
  4. Export a small looping GIF (save_all=True, loop=0, duration~80ms).

Keep canvases modest and palettes tight so GIFs stay under ~1–2 MB.
"""

from __future__ import annotations

import math
from PIL import Image, ImageDraw

# ---- The locked palette (PROFILE-SPEC.md). Use these everywhere. ----------
PALETTE = {
    "plum":    "#2A1B3D",  # midnight water / deep sky, darkest anchor
    "purple":  "#6A2C70",  # mid gradient
    "orchid":  "#A64C9E",  # transition
    "hotpink": "#E84393",  # sun band / accents
    "coral":   "#FF7AA2",  # highlights, blush, fish
    "ember":   "#FF7B2E",  # CLEAVE Ember — sun core, ties to brand
    "peach":   "#FFB26B",  # water shimmer, soft fills
    "cream":   "#F5EFE8",  # text, foam, UI card face
    # --- Marlowe (story panels) ---
    "pastelpink":  "#FFC2DE",  # Marlowe's Afro (signature)
    "pinkshadow":  "#E89BBF",  # Afro shadow edge
    "brown":       "#7A4A32",  # Marlowe's skin midtone
    "brownshadow": "#5C3322",  # skin shadow
    "brownhi":     "#9E6347",  # skin highlight
    "blonde":      "#F2D27A",  # Cass's ponytail
}

# Convenience RGB tuples.
RGB = {name: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for name, h in PALETTE.items()}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c1: str, c2: str, t: float) -> tuple[int, int, int]:
    """Blend two palette hexes; t in [0,1]."""
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return (round(lerp(r1, r2, t)), round(lerp(g1, g2, t)), round(lerp(b1, b2, t)))


# ---- Canvas helpers -------------------------------------------------------

def new_canvas(w: int, h: int, fill="plum") -> Image.Image:
    """A small logical-resolution canvas in RGB (no alpha; GIF is opaque)."""
    color = PALETTE.get(fill, fill)
    return Image.new("RGB", (w, h), hex_to_rgb(color) if color.startswith("#") else color)


def vertical_gradient(w: int, h: int, stops: list[tuple[float, str]]) -> Image.Image:
    """Vertical gradient. `stops` = [(position 0..1, hex), ...] sorted by position.

    Used for the sunset sky: plum -> purple -> pink -> peach.
    """
    img = Image.new("RGB", (w, h))
    px = img.load()
    stops = sorted(stops, key=lambda s: s[0])
    for y in range(h):
        t = y / max(1, h - 1)
        # find bracketing stops
        lo = stops[0]
        hi = stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                lo, hi = stops[i], stops[i + 1]
                break
        span = max(1e-6, hi[0] - lo[0])
        local_t = (t - lo[0]) / span
        col = mix(lo[1], hi[1], local_t)
        for x in range(w):
            px[x, y] = col
    return img


def sunset_sky(w: int, h: int, deep: bool = False) -> Image.Image:
    """The shared sunset background. `deep` darkens it for the descent panels."""
    if deep:
        stops = [(0.0, "#1a1028"), (0.4, PALETTE["plum"]),
                 (0.75, PALETTE["purple"]), (1.0, PALETTE["orchid"])]
    else:
        stops = [(0.0, "#3a2356"), (0.28, PALETTE["purple"]), (0.50, PALETTE["orchid"]),
                 (0.70, PALETTE["hotpink"]), (0.84, PALETTE["coral"]), (1.0, PALETTE["peach"])]
    return vertical_gradient(w, h, stops)


def scale(img: Image.Image, factor: int) -> Image.Image:
    """Blocky upscale — the whole point of the chunky-pixel look."""
    return img.resize((img.width * factor, img.height * factor), Image.NEAREST)


# ---- Animation helpers ----------------------------------------------------

def sway_offset(frame: int, n_frames: int, amplitude: float, phase: float = 0.0) -> float:
    """Sine wiggle. Give each sprite a different `phase` so they don't sync."""
    theta = (frame / n_frames) * 2 * math.pi + phase
    return amplitude * math.sin(theta)


def export_gif(frames: list[Image.Image], path: str, duration: int = 80) -> None:
    """Save a looping GIF. Caller passes already-scaled frames."""
    if not frames:
        raise ValueError("export_gif: no frames")
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=duration,
        optimize=True,
        disposal=2,
    )


# ---- Tiny shared sprite primitives ---------------------------------------

def kawaii_face(d: ImageDraw.ImageDraw, cx: int, cy: int, look: str = "dot",
                eye=PALETTE["plum"], blush=PALETTE["coral"]) -> None:
    """Draw the unifying kawaii face on a logical-pixel grid: two dot eyes, a
    little smile, optional blush. `cx,cy` is the face center in logical pixels."""
    e = hex_to_rgb(eye)
    # eyes
    if look == "sleepy":
        d.line([(cx - 3, cy), (cx - 1, cy)], fill=e)
        d.line([(cx + 1, cy), (cx + 3, cy)], fill=e)
    elif look == "sparkle":
        d.point([(cx - 2, cy), (cx + 2, cy)], fill=e)
        d.point([(cx - 3, cy - 1), (cx + 1, cy - 1)], fill=hex_to_rgb(PALETTE["cream"]))
    else:  # dot
        d.point([(cx - 2, cy), (cx + 2, cy)], fill=e)
    # smile
    d.point([(cx - 1, cy + 2), (cx, cy + 3), (cx + 1, cy + 2)], fill=e)
    # blush
    bl = hex_to_rgb(blush)
    d.point([(cx - 4, cy + 1), (cx + 4, cy + 1)], fill=bl)


def draw_star(d: ImageDraw.ImageDraw, x: int, y: int, color=PALETTE["peach"]) -> None:
    """A 5px pixel sparkle-star (a plus with a center)."""
    c = hex_to_rgb(color)
    d.point([(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y), (x, y)], fill=c)


def draw_bubble(d: ImageDraw.ImageDraw, x: int, y: int, r: int = 1,
                color=PALETTE["cream"]) -> None:
    c = hex_to_rgb(color)
    d.ellipse([x - r, y - r, x + r, y + r], outline=c)


if __name__ == "__main__":
    # BUILD.md §3a: render one test sprite, confirm crisp pixels + small file,
    # THEN build the real renderers on top. Run:  python render/sprites.py
    import os

    W, H, FACTOR, N = 24, 24, 12, 16
    frames = []
    for f in range(N):
        sky = sunset_sky(W, H)
        d = ImageDraw.Draw(sky)
        # a sun
        d.ellipse([15, 3, 21, 9], fill=hex_to_rgb(PALETTE["ember"]))
        # a sparkle that twinkles
        if f % 4 < 2:
            draw_star(d, 5, 4)
        # a little swaying fish body with a kawaii face
        dx = round(sway_offset(f, N, 2.0))
        bx, by = 8 + dx, 14
        d.ellipse([bx - 3, by - 2, bx + 3, by + 2], fill=hex_to_rgb(PALETTE["coral"]))
        d.polygon([(bx - 3, by), (bx - 6, by - 2), (bx - 6, by + 2)],
                  fill=hex_to_rgb(PALETTE["hotpink"]))  # tail
        kawaii_face(d, bx + 1, by, look="dot")
        frames.append(scale(sky, FACTOR))

    out = os.path.join(os.path.dirname(__file__), "_sprite_test.gif")
    export_gif(frames, out)
    size = os.path.getsize(out)
    print(f"wrote {out} ({size/1024:.1f} KB, {N} frames, {W*FACTOR}x{H*FACTOR})")
    assert size < 2 * 1024 * 1024, "GIF too big — reduce colors/size"
    print("OK: crisp-pixel test sprite rendered under 2MB")
