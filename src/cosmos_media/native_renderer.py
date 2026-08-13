from __future__ import annotations

"""First-party COSMOS visual synthesizer.

This renderer does not call an external image/video model. It creates
prompt-conditioned visual worlds from deterministic scene grammar, CST state,
procedural geometry, recursive structures, layered light/noise, reflections,
particles and animation phase. External neural renderers remain optional.
"""

from dataclasses import dataclass
import colorsys
import hashlib
import math
import random
import re
from typing import Sequence


@dataclass(slots=True)
class NativeSceneSpec:
    seed: int
    structure_seed: int
    width: int
    height: int
    horizon: float
    palette: tuple[tuple[int, int, int], ...]
    glow: float
    complexity: float
    surrealism: float
    motion: float
    has_water: bool
    has_tree: bool
    has_city: bool
    has_islands: bool
    moon_count: int
    star_density: int


def _stable_int(*parts: object) -> int:
    digest = hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _sv(state: Sequence[float], index: int, default: float = 0.0) -> float:
    if not state:
        return default
    return float(state[index % len(state)])


def _rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, _clamp(s), _clamp(v))
    return int(r * 255), int(g * 255), int(b * 255)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = _clamp(t)
    return tuple(int(x * (1.0 - t) + y * t) for x, y in zip(a, b))


def _prompt_words(prompt: str, context: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", f"{prompt} {context}".lower()))


def _palette(prompt: str, context: str, state: Sequence[float]) -> tuple[tuple[int, int, int], ...]:
    h0 = (_stable_int(prompt.lower(), context.lower(), "palette") / float(2**64 - 1)) % 1.0
    h0 = (h0 + 0.08 * _sv(state, 0)) % 1.0
    return (
        _rgb(h0, 0.70, 0.055),
        _rgb(h0 + 0.025, 0.66, 0.17 + 0.05 * abs(_sv(state, 1))),
        _rgb(h0 + 0.07, 0.58, 0.40),
        _rgb(h0 + 0.42 + 0.04 * _sv(state, 3), 0.68, 0.92),
        _rgb(h0 + 0.54, 0.52, 1.0),
        _rgb(h0 + 0.11, 0.60, 0.96),
    )


def build_scene_spec(
    prompt: str,
    context: str,
    seed: int,
    state: Sequence[float],
    width: int,
    height: int,
) -> NativeSceneSpec:
    words = _prompt_words(prompt, context)
    water_words = {"water", "ocean", "sea", "lake", "river", "reflection", "island", "shore"}
    tree_words = {"tree", "forest", "garden", "plant", "root", "branch", "grove", "nature"}
    city_words = {"city", "tower", "building", "station", "observatory", "temple", "architecture"}
    island_words = {"island", "floating", "sky", "cloud", "world", "planet", "multiverse"}
    return NativeSceneSpec(
        seed=int(seed),
        structure_seed=_stable_int(seed, prompt, context, tuple(round(v, 5) for v in state)),
        width=int(width),
        height=int(height),
        horizon=0.54 + 0.06 * _sv(state, 5),
        palette=_palette(prompt, context, state),
        glow=0.55 + 0.40 * abs(_sv(state, 2)),
        complexity=0.52 + 0.44 * abs(_sv(state, 8)),
        surrealism=0.40 + 0.56 * abs(_sv(state, 10)),
        motion=0.34 + 0.58 * abs(_sv(state, 6)),
        has_water=bool(words & water_words) or _sv(state, 4) > -0.25,
        has_tree=bool(words & tree_words) or _stable_int(prompt, "tree") % 3 == 0,
        has_city=bool(words & city_words),
        has_islands=bool(words & island_words) or _sv(state, 10) > 0.1,
        moon_count=1 + int((_stable_int(prompt, "moons") + int(abs(_sv(state, 9)) * 10)) % 3),
        star_density=120 + int(260 * (0.5 + 0.5 * abs(_sv(state, 11)))),
    )


def _gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]):
    from PIL import Image

    w, h = size
    image = Image.new("RGB", size)
    px = image.load()
    denom = max(1, h - 1)
    for y in range(h):
        t = y / denom
        c = _mix(top, bottom, t)
        for x in range(w):
            px[x, y] = c
    return image


def _glow_ellipse(base, box, color, alpha: int, blur: float) -> None:
    from PIL import Image, ImageDraw, ImageFilter

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    d.ellipse(box, fill=(*color, alpha))
    if blur > 0:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)


def _glow_line(base, points, color, width: int, alpha: int, blur: float) -> None:
    from PIL import Image, ImageDraw, ImageFilter

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    d.line(points, fill=(*color, alpha), width=max(1, width), joint="curve")
    if blur > 0:
        blurred = layer.filter(ImageFilter.GaussianBlur(blur))
        base.alpha_composite(blurred)
    base.alpha_composite(layer)


def _draw_stars(draw, rng: random.Random, spec: NativeSceneSpec, phase: float) -> None:
    w, h = spec.width, spec.height
    horizon = int(spec.horizon * h)
    for i in range(spec.star_density):
        x = rng.randrange(0, w)
        y = rng.randrange(0, max(1, horizon))
        r = 1 if rng.random() < 0.86 else rng.choice((2, 2, 3))
        twinkle = 0.58 + 0.42 * math.sin(phase * 2.0 + i * 1.618)
        alpha = int(80 + 170 * max(0.0, twinkle))
        color = spec.palette[4] if i % 11 == 0 else (235, 245, 255)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(*color, alpha))


def _draw_moons(base, draw, rng: random.Random, spec: NativeSceneSpec, phase: float) -> None:
    w, h = spec.width, spec.height
    for i in range(spec.moon_count):
        rr = int(min(w, h) * (0.035 + 0.035 * rng.random()) * (1.2 if i == 0 else 0.8))
        x = int(w * (0.58 + 0.26 * rng.random()))
        y = int(h * (0.12 + 0.17 * rng.random()))
        y += int(math.sin(phase * 0.12 + i) * 2)
        _glow_ellipse(base, (x - rr * 2, y - rr * 2, x + rr * 2, y + rr * 2), spec.palette[3], 55, rr * 0.8)
        draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(*_mix(spec.palette[4], (245, 250, 255), 0.40), 245))
        for _ in range(14):
            cr = rng.randint(max(1, rr // 14), max(2, rr // 5))
            cx = x + rng.randint(-rr + cr, rr - cr)
            cy = y + rng.randint(-rr + cr, rr - cr)
            draw.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=(*spec.palette[2], rng.randint(20, 65)))


def _draw_nebula(base, rng: random.Random, spec: NativeSceneSpec, phase: float) -> None:
    from PIL import Image, ImageDraw, ImageFilter

    w, h = spec.width, spec.height
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    for i in range(14 + int(spec.complexity * 12)):
        x = rng.randint(-w // 5, w + w // 5)
        y = rng.randint(0, int(h * spec.horizon * 0.9))
        rx = rng.randint(max(30, w // 14), max(60, w // 3))
        ry = rng.randint(max(12, h // 40), max(35, h // 10))
        x += int(math.sin(phase * 0.08 + i * 0.31) * 8)
        c = spec.palette[3 + (i % 2)]
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=(*c, rng.randint(8, 22)))
    layer = layer.filter(ImageFilter.GaussianBlur(max(18, int(w / 50))))
    base.alpha_composite(layer)


def _island_polygon(cx: int, cy: int, width: int, height: int, rng: random.Random):
    top = []
    for i in range(8):
        t = i / 7
        x = int(cx - width / 2 + width * t)
        y = int(cy + rng.uniform(-0.08, 0.08) * height)
        top.append((x, y))
    bottom = [(cx + width // 2, cy), (cx + int(width * 0.30), cy + int(height * 0.65)), (cx, cy + height), (cx - int(width * 0.26), cy + int(height * 0.58)), (cx - width // 2, cy)]
    return top + bottom


def _draw_islands(base, draw, rng: random.Random, spec: NativeSceneSpec, phase: float) -> None:
    if not spec.has_islands:
        return
    w, h = spec.width, spec.height
    count = 3 + int(spec.surrealism * 5)
    for i in range(count):
        scale = rng.uniform(0.05, 0.16)
        iw = int(w * scale)
        ih = int(h * scale * rng.uniform(0.6, 1.15))
        cx = int(w * rng.uniform(0.18, 0.92))
        cy = int(h * rng.uniform(0.28, spec.horizon - 0.04))
        cy += int(math.sin(phase * 0.18 + i * 0.9) * (2 + 5 * spec.motion))
        poly = _island_polygon(cx, cy, iw, ih, rng)
        draw.polygon(poly, fill=(*_mix(spec.palette[0], spec.palette[2], 0.28), 245))
        draw.line(poly[:8], fill=(*spec.palette[3], 115), width=max(1, w // 700))
        for j in range(rng.randint(3, 10)):
            lx = cx + rng.randint(-iw // 3, iw // 3)
            ly = cy + rng.randint(-max(1, ih // 20), max(2, ih // 9))
            _glow_ellipse(base, (lx - 4, ly - 4, lx + 4, ly + 4), spec.palette[5], 125, 5)


def _draw_city(base, draw, rng: random.Random, spec: NativeSceneSpec, phase: float) -> None:
    if not spec.has_city:
        return
    w, h = spec.width, spec.height
    horizon = int(spec.horizon * h)
    x = int(w * 0.10)
    end = int(w * 0.48)
    while x < end:
        bw = rng.randint(max(5, w // 90), max(10, w // 38))
        bh = rng.randint(max(18, h // 18), max(45, h // 4))
        y0 = horizon - bh
        draw.rectangle((x, y0, x + bw, horizon), fill=(*_mix(spec.palette[0], spec.palette[1], 0.42), 235))
        if rng.random() < 0.55:
            draw.polygon([(x, y0), (x + bw // 2, y0 - rng.randint(5, 30)), (x + bw, y0)], fill=(*spec.palette[1], 220))
        for wy in range(y0 + 8, horizon - 5, 9):
            if rng.random() < 0.70:
                wx = x + rng.randint(2, max(2, bw - 4))
                _glow_ellipse(base, (wx - 2, wy - 2, wx + 2, wy + 2), spec.palette[5], 105, 3)
        x += bw + rng.randint(2, 7)


def _branch_points(x: float, y: float, length: float, angle: float, depth: int, rng: random.Random):
    if depth <= 0 or length < 2:
        return []
    x2 = x + math.cos(angle) * length
    y2 = y + math.sin(angle) * length
    segments = [((x, y), (x2, y2), depth)]
    spread = 0.35 + rng.random() * 0.30
    shrink = 0.63 + rng.random() * 0.10
    segments += _branch_points(x2, y2, length * shrink, angle - spread, depth - 1, rng)
    segments += _branch_points(x2, y2, length * shrink, angle + spread, depth - 1, rng)
    if rng.random() < 0.24:
        segments += _branch_points(x2, y2, length * shrink * 0.82, angle + rng.uniform(-0.18, 0.18), depth - 1, rng)
    return segments


def _draw_world_tree(base, draw, rng: random.Random, spec: NativeSceneSpec, phase: float) -> None:
    if not spec.has_tree:
        return
    w, h = spec.width, spec.height
    horizon = int(spec.horizon * h)
    root_x = int(w * (0.68 + 0.07 * rng.random()))
    root_y = horizon + int(h * 0.03)
    trunk_h = int(h * (0.19 + 0.10 * spec.surrealism))
    bend = math.sin(phase * 0.08) * w * 0.004
    segments = _branch_points(root_x + bend, root_y, trunk_h * 0.42, -math.pi / 2, 7, rng)
    for (a, b, depth) in sorted(segments, key=lambda s: s[2]):
        width = max(1, int((depth / 7) ** 1.5 * w * 0.014))
        c = _mix(spec.palette[2], spec.palette[3], 1.0 - depth / 8.0)
        _glow_line(base, [a, b], c, width, int(120 + 80 * spec.glow), max(2, width * 0.8))
        draw.line([a, b], fill=(*_mix(c, (245, 250, 255), 0.20), 235), width=max(1, width // 3))
    canopy_y = root_y - trunk_h
    for i in range(65 + int(spec.complexity * 90)):
        ang = rng.random() * math.tau
        rad = (rng.random() ** 0.55) * trunk_h * 0.92
        x = root_x + math.cos(ang) * rad * 1.45
        y = canopy_y + math.sin(ang) * rad * 0.48
        rr = rng.randint(max(2, w // 650), max(4, w // 280))
        c = spec.palette[3] if i % 3 else spec.palette[5]
        _glow_ellipse(base, (x - rr * 2, y - rr * 2, x + rr * 2, y + rr * 2), c, 65, rr * 1.6)
        draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(*c, 170))


def _draw_water(base, draw, rng: random.Random, spec: NativeSceneSpec, phase: float) -> None:
    if not spec.has_water:
        return
    w, h = spec.width, spec.height
    horizon = int(spec.horizon * h)
    draw.rectangle((0, horizon, w, h), fill=(*_mix(spec.palette[0], spec.palette[1], 0.32), 250))
    bands = 70 + int(spec.complexity * 70)
    for i in range(bands):
        y = rng.randint(horizon, h - 1)
        depth = (y - horizon) / max(1, h - horizon)
        length = rng.randint(max(6, int(w * 0.008)), max(20, int(w * (0.02 + 0.09 * depth))))
        x = rng.randint(0, w - 1)
        wobble = int(math.sin(phase * 0.45 + y * 0.033 + i) * (1 + 3 * spec.motion))
        c = spec.palette[3 + (i % 2)]
        alpha = int(25 + 90 * depth * spec.glow)
        draw.line((x, y + wobble, min(w, x + length), y + wobble), fill=(*c, alpha), width=1 + int(depth * 2))
    # Perspective energy paths on the water.
    for lane in range(4 + int(spec.surrealism * 5)):
        x0 = rng.randint(0, w)
        x1 = int(w * (0.35 + 0.55 * rng.random()))
        pts = []
        for j in range(18):
            t = j / 17
            y = horizon + int((h - horizon) * (t ** 1.65))
            x = int(x0 * t + x1 * (1 - t) + math.sin(t * 12 + phase * 0.35 + lane) * 10 * t)
            pts.append((x, y))
        _glow_line(base, pts, spec.palette[3], max(1, w // 900), int(50 + 80 * spec.glow), 4)


def _draw_foreground(base, draw, rng: random.Random, spec: NativeSceneSpec, phase: float) -> None:
    w, h = spec.width, spec.height
    # Curved observation frame: gives the scene a cinematic built-environment anchor.
    if spec.has_city or _stable_int(spec.seed, "frame") % 2 == 0:
        thickness = max(5, w // 70)
        frame_color = _mix(spec.palette[1], (210, 180, 125), 0.45)
        draw.arc((-w * 0.20, -h * 0.18, w * 0.62, h * 1.17), 265, 95, fill=(*frame_color, 210), width=thickness)
        draw.arc((-w * 0.17, -h * 0.15, w * 0.59, h * 1.14), 265, 95, fill=(*spec.palette[5], 80), width=max(2, thickness // 4))
        floor_y = int(h * 0.91)
        draw.ellipse((-w * 0.15, floor_y - h * 0.10, w * 0.42, floor_y + h * 0.16), outline=(*frame_color, 190), width=max(3, thickness // 2))


def _draw_particles(base, rng: random.Random, spec: NativeSceneSpec, phase: float) -> None:
    w, h = spec.width, spec.height
    count = 80 + int(spec.complexity * 160)
    for i in range(count):
        x = (rng.random() * w + phase * (2 + 8 * spec.motion) * (0.35 + rng.random())) % w
        y = (rng.random() * h + math.sin(i * 0.71 + phase * 0.21) * 8) % h
        rr = 1 if rng.random() < 0.80 else 2
        c = spec.palette[3 if i % 4 else 5]
        _glow_ellipse(base, (x - rr, y - rr, x + rr, y + rr), c, rng.randint(35, 100), 2 + rr)


def render_native_image(
    prompt: str,
    context: str,
    seed: int,
    state: Sequence[float],
    width: int,
    height: int,
    *,
    phase: float = 0.0,
):
    """Render one deterministic COSMOS frame entirely inside this repository."""
    from PIL import ImageDraw, ImageEnhance, ImageFilter

    spec = build_scene_spec(prompt, context, seed, state, width, height)
    # Keep layout stable across frames; phase moves the scene without re-rolling it.
    rng = random.Random(spec.structure_seed)
    sky = _gradient((width, height), spec.palette[0], spec.palette[2]).convert("RGBA")
    base = sky
    _draw_nebula(base, rng, spec, phase)
    draw = ImageDraw.Draw(base, "RGBA")
    _draw_stars(draw, rng, spec, phase)
    _draw_moons(base, draw, rng, spec, phase)
    _draw_islands(base, draw, rng, spec, phase)
    _draw_city(base, draw, rng, spec, phase)
    _draw_water(base, draw, rng, spec, phase)
    _draw_world_tree(base, draw, rng, spec, phase)
    _draw_foreground(base, draw, rng, spec, phase)
    _draw_particles(base, rng, spec, phase)

    # Filmic finish from first-party operations only.
    rgb = base.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.12 + spec.complexity * 0.10)
    rgb = ImageEnhance.Color(rgb).enhance(1.08 + spec.glow * 0.10)
    sharp = rgb.filter(ImageFilter.UnsharpMask(radius=1.2, percent=75, threshold=3))
    return sharp
