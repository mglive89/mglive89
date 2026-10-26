"""Shared math, colour and drawing helpers for the Warum Du renderer."""
import math

import cairo
import numpy as np

W, H = 1920, 1080          # world/canvas reference size (16:9)
FPS = 30
OUTLINE = (0.11, 0.09, 0.13)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_io(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t)
    return t * t * t


def seg(t, a, b):
    """Normalised progress of t through [a, b]."""
    if b == a:
        return 1.0 if t >= b else 0.0
    return clamp((t - a) / (b - a))


def pulse(t, a, b):
    """0 -> 1 -> 0 bump across [a, b]."""
    s = seg(t, a, b)
    return math.sin(s * math.pi)


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


def mix(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def noise1(x, seed=0):
    """Cheap smooth pseudo-noise in [-1, 1] built from incommensurate sines."""
    s = seed * 12.9898
    return (math.sin(x * 1.0 + s) * 0.5 + math.sin(x * 2.31 + s * 1.7) * 0.3
            + math.sin(x * 4.73 + s * 2.3) * 0.2)


def rng(seed):
    return np.random.default_rng(seed)


def rgba(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], a)


def catmull_path(ctx, pts, closed=True, tension=0.5):
    """Smooth path through points using Catmull-Rom -> cubic Bezier."""
    n = len(pts)
    if n < 2:
        return
    ctx.move_to(*pts[0])
    rng_ = range(n) if closed else range(n - 1)
    for i in rng_:
        p0 = pts[(i - 1) % n] if closed or i > 0 else pts[i]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed or i + 2 < n else pts[(i + 1) % n]
        k = tension / 3 * 2
        c1 = (p1[0] + (p2[0] - p0[0]) * k / 2, p1[1] + (p2[1] - p0[1]) * k / 2)
        c2 = (p2[0] - (p3[0] - p1[0]) * k / 2, p2[1] - (p3[1] - p1[1]) * k / 2)
        ctx.curve_to(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if closed:
        ctx.close_path()


def ellipse(ctx, x, y, rx, ry, a0=0, a1=2 * math.pi):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(rx, 1e-4), max(ry, 1e-4))
    ctx.arc(0, 0, 1, a0, a1)
    ctx.restore()


def radial_glow(ctx, x, y, r, c, a=1.0, falloff=(0.0, 0.35, 1.0)):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(falloff[0], c[0], c[1], c[2], a)
    g.add_color_stop_rgba(falloff[1], c[0], c[1], c[2], a * 0.35)
    g.add_color_stop_rgba(falloff[2], c[0], c[1], c[2], 0)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()


def vgrad(ctx, x, y, w, h, stops, alpha=1.0):
    g = cairo.LinearGradient(x, y, x, y + h)
    for pos, c, *a in stops:
        g.add_color_stop_rgba(pos, c[0], c[1], c[2], (a[0] if a else 1.0) * alpha)
    ctx.set_source(g)
    ctx.rectangle(x, y, w, h)
    ctx.fill()


def text_center(ctx, txt, x, y, size, color, alpha=1.0, font="Inter Display",
                weight=cairo.FONT_WEIGHT_BOLD, spacing=0.0):
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)
    if spacing:
        widths = [ctx.text_extents(ch).x_advance for ch in txt]
        total = sum(widths) + spacing * (len(txt) - 1)
        cx = x - total / 2
        ext = ctx.text_extents(txt)
        for ch, w_ in zip(txt, widths):
            ctx.move_to(cx, y - (ext.y_bearing + ext.height / 2))
            rgba(ctx, color, alpha)
            ctx.show_text(ch)
            cx += w_ + spacing
        return total
    ext = ctx.text_extents(txt)
    ctx.move_to(x - ext.x_advance / 2, y - (ext.y_bearing + ext.height / 2))
    rgba(ctx, color, alpha)
    ctx.show_text(txt)
    return ext.x_advance


class Lighting:
    """Ambient tint applied to every character colour so they sit in the scene."""

    def __init__(self, mult=(1, 1, 1), add=(0, 0, 0), add_k=0.0):
        self.mult = mult
        self.add = add
        self.add_k = add_k

    def __call__(self, c):
        m = tuple(clamp(a * b) for a, b in zip(c, self.mult))
        return mix(m, self.add, self.add_k)


NIGHT = Lighting((0.76, 0.86, 1.0), hexc("#3b3f8f"), 0.10)
RAIN = Lighting((0.68, 0.80, 0.95), hexc("#2a3a6a"), 0.14)
WARM = Lighting((1.02, 0.96, 0.9), hexc("#ff9a4a"), 0.05)
DAWN = Lighting((1.0, 0.88, 0.86), hexc("#ff9f8a"), 0.06)
ROOM = Lighting((0.55, 0.62, 0.88), hexc("#1d2450"), 0.18)
NEUTRAL = Lighting()
