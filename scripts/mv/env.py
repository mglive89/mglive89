"""Procedural environments: parallax city, street, 3D fly-through, bedroom,
park at dawn. Everything is drawn in world units (1920x1080 reference)."""
import math

import cairo

from .core import (catmull_path, clamp, ellipse, hexc, lerp, mix, noise1,
                   radial_glow, rgba, rng, text_center, vgrad)

PALETTES = {
    "night": dict(sky=[(0, "#05071a"), (0.55, "#1a1245"), (1, "#4b2a72")],
                  far="#14163a", mid="#1d1f45", near="#262a52",
                  win=["#ffcf7a", "#7ad7ff", "#ff7ad9", "#fff1c9"], win_on=0.30,
                  ground="#1a1c33", fog="#5a4a9a", moon=True),
    "rain": dict(sky=[(0, "#04060f"), (0.6, "#121a33"), (1, "#2c3560")],
                 far="#131a33", mid="#192241", near="#20294d",
                 win=["#ffd38a", "#8fd8ff", "#ff8ad0", "#e8f0ff"], win_on=0.26,
                 ground="#141a2c", fog="#4a5a8a", moon=False),
    "warm": dict(sky=[(0, "#3d2a6b"), (0.35, "#c45a6a"), (0.7, "#ff9a5c"), (1, "#ffd59a")],
                 far="#9c4f5e", mid="#7a3b52", near="#5c2c46",
                 win=["#ffe2a0", "#ffc27a", "#fff3d0", "#ffb070"], win_on=0.2,
                 ground="#5a3242", fog="#ffb37a", moon=False),
    "dusk": dict(sky=[(0, "#1d1a4f"), (0.5, "#6a3a7a"), (0.85, "#e0706a"), (1, "#ffb27a")],
                 far="#3b2f62", mid="#33285a", near="#2a234e",
                 win=["#ffd68a", "#ffb36a", "#ff8ad0", "#fff1c9"], win_on=0.5,
                 ground="#2a2240", fog="#c47aa0", moon=False),
    "dawn": dict(sky=[(0, "#22305e"), (0.45, "#7a6a9a"), (0.8, "#f4a08a"), (1, "#ffd8a6")],
                 far="#5a5a86", mid="#45466f", near="#36375d",
                 win=["#ffe0a0", "#fff0d0", "#ffd090", "#ffe8b8"], win_on=0.10,
                 ground="#3a3a5c", fog="#ffc6a6", moon=False),
}


def pal(name):
    return PALETTES[name]


def mix_pal(a, b, t):
    """Blend two palettes (used for night -> warm memory transitions)."""
    pa, pb = PALETTES[a], PALETTES[b]
    out = {}
    for k in ("far", "mid", "near", "ground", "fog"):
        out[k] = mix(hexc(pa[k]), hexc(pb[k]), t)
    out["win"] = [mix(hexc(x), hexc(y), t) for x, y in zip(pa["win"], pb["win"])]
    out["win_on"] = lerp(pa["win_on"], pb["win_on"], t)
    out["sky"] = (pa["sky"], pb["sky"], t)
    out["moon"] = pa["moon"] and t < 0.5
    return out


def _c(v):
    return hexc(v) if isinstance(v, str) else v


def draw_sky(ctx, p, x0, y0, w, h, t=0.0):
    sky = p["sky"]
    if isinstance(sky, tuple):
        sa, sb, k = sky
        # blend stop by stop (both lists resampled at 5 points)
        g = cairo.LinearGradient(0, y0, 0, y0 + h)
        for i in range(6):
            f = i / 5
            g.add_color_stop_rgb(f, *mix(_sample(sa, f), _sample(sb, f), k))
    else:
        g = cairo.LinearGradient(0, y0, 0, y0 + h)
        for pos, col in sky:
            g.add_color_stop_rgb(pos, *hexc(col))
    ctx.set_source(g)
    ctx.rectangle(x0, y0, w, h)
    ctx.fill()


def _sample(stops, f):
    for (p0, c0), (p1, c1) in zip(stops[:-1], stops[1:]):
        if p0 <= f <= p1:
            return mix(hexc(c0), hexc(c1), (f - p0) / max(p1 - p0, 1e-6))
    return hexc(stops[-1][1])


def stars(ctx, x0, w, horizon, t, alpha=1.0, seed=5, n=140):
    r = rng(seed)
    xs = r.uniform(0, 1, n)
    ys = r.uniform(0, 1, n)
    ss = r.uniform(0.6, 2.0, n)
    ph = r.uniform(0, 6.28, n)
    for x, y, s_, p_ in zip(xs, ys, ss, ph):
        a = alpha * (0.45 + 0.55 * math.sin(t * 1.7 + p_) ** 2)
        rgba(ctx, (1, 0.95, 1), a * 0.8)
        ctx.arc(x0 + x * w, y * horizon * 0.75, s_, 0, 6.283)
        ctx.fill()


def moon(ctx, x, y, r, alpha=1.0):
    radial_glow(ctx, x, y, r * 5, hexc("#9aa8ff"), 0.25 * alpha)
    rgba(ctx, hexc("#f4f1ff"), alpha)
    ctx.arc(x, y, r, 0, 6.283)
    ctx.fill()
    rgba(ctx, hexc("#d8d4f0"), alpha * 0.6)
    ctx.arc(x - r * 0.3, y - r * 0.2, r * 0.22, 0, 6.283)
    ctx.arc(x + r * 0.35, y + r * 0.3, r * 0.15, 0, 6.283)
    ctx.fill()


NEON_WORDS = ["BAR", "KIOSK", "HOTEL", "24/7", "KINO", "DÖNER", "CAFÉ", "CLUB", "PIZZA", "SPÄTI"]
NEON_COLS = ["#ff4fd8", "#46e6ff", "#b46bff", "#ff6a5a", "#5affb0", "#ffd84a"]


class CityLayer:
    """One parallax layer of procedurally generated buildings, tiling every `period`."""

    def __init__(self, seed, depth, base_y, hmin, hmax, wmin, wmax, period=5200,
                 neon=False, detail=1.0):
        r = rng(seed)
        self.depth = depth
        self.base_y = base_y
        self.period = period
        self.neon = neon
        self.b = []
        x = 0
        while x < period:
            w = r.uniform(wmin, wmax)
            h = r.uniform(hmin, hmax)
            if r.random() < 0.12:
                h *= 1.45
            gap = r.uniform(0, 30) if r.random() < 0.3 else 0
            cols = max(2, int(w / (26 if depth > 0.5 else 18)))
            rows = max(3, int(h / (34 if depth > 0.5 else 22)))
            lit = r.random((rows, cols))
            wcol = r.integers(0, 4, (rows, cols))
            roof = r.integers(0, 4)
            sign = None
            if neon and r.random() < 0.55:
                sign = dict(word=NEON_WORDS[r.integers(0, len(NEON_WORDS))],
                            col=NEON_COLS[r.integers(0, len(NEON_COLS))],
                            y=r.uniform(0.25, 0.6), vertical=r.random() < 0.35,
                            flick=r.uniform(0, 100), bad=r.random() < 0.18)
            self.b.append(dict(x=x, w=w, h=h, cols=cols, rows=rows, lit=lit, wcol=wcol,
                               roof=roof, sign=sign, tone=r.uniform(-0.06, 0.06),
                               detail=detail))
            x += w + gap

    def draw(self, ctx, cam_x, view_x0, view_x1, p, key, t, lit_scale=1.0, sign_alpha=1.0):
        """Draw buildings for world view [view_x0, view_x1] given camera x."""
        off = cam_x * (1 - self.depth)       # parallax: slower layers drift less
        base = _c(p[key])
        winc = [_c(c) for c in p["win"]]
        thr = 1 - p["win_on"] * lit_scale
        k0 = math.floor((view_x0 - off) / self.period) - 1
        k1 = math.floor((view_x1 - off) / self.period) + 1
        win_paths = [[] for _ in range(4)]
        signs = []
        for k in range(k0, k1 + 1):
            for b in self.b:
                bx = b["x"] + k * self.period + off
                if bx + b["w"] < view_x0 - 50 or bx > view_x1 + 50:
                    continue
                top = self.base_y - b["h"]
                col = tuple(clamp(c + b["tone"]) for c in base)
                rgba(ctx, col)
                ctx.rectangle(bx, top, b["w"], b["h"] + 400)
                ctx.fill()
                # roof details
                if b["roof"] == 1:
                    ctx.rectangle(bx + b["w"] * 0.6, top - 26, 4, 26)
                    ctx.fill()
                    rgba(ctx, hexc("#ff3b3b"), 0.6 + 0.4 * math.sin(t * 3 + bx))
                    ctx.arc(bx + b["w"] * 0.6 + 2, top - 28, 3, 0, 6.3)
                    ctx.fill()
                elif b["roof"] == 2:
                    rgba(ctx, col)
                    ctx.rectangle(bx + b["w"] * 0.15, top - 18, b["w"] * 0.3, 18)
                    ctx.fill()
                elif b["roof"] == 3:
                    rgba(ctx, col)
                    ctx.move_to(bx, top)
                    ctx.line_to(bx + b["w"] / 2, top - b["w"] * 0.18)
                    ctx.line_to(bx + b["w"], top)
                    ctx.fill()
                # edge highlight
                rgba(ctx, (1, 1, 1), 0.035)
                ctx.rectangle(bx + b["w"] - 3, top, 3, b["h"])
                ctx.fill()
                cw = b["w"] / b["cols"]
                rh = b["h"] / b["rows"]
                ww, wh = cw * 0.52, rh * 0.5
                for i in range(b["rows"]):
                    for j in range(b["cols"]):
                        if b["lit"][i, j] > thr:
                            win_paths[b["wcol"][i, j]].append(
                                (bx + j * cw + (cw - ww) / 2, top + i * rh + rh * 0.3, ww, wh))
                if b["sign"] is not None:
                    signs.append((bx, top, b))
        for idx, rects in enumerate(win_paths):
            if not rects:
                continue
            rgba(ctx, winc[idx], 0.45 + 0.45 * self.depth)
            for r_ in rects:
                ctx.rectangle(*r_)
            ctx.fill()
        if self.neon and sign_alpha > 0:
            for bx, top, b in signs:
                draw_neon_sign(ctx, bx, top, b, t, sign_alpha)


def draw_neon_sign(ctx, bx, top, b, t, alpha):
    s = b["sign"]
    col = hexc(s["col"])
    on = 1.0
    if s["bad"]:
        ph = (t * 7 + s["flick"]) % 9
        on = 0.15 if (ph < 0.25 or 1.1 < ph < 1.3) else 1.0
    a = alpha * on
    word = s["word"]
    ctx.select_font_face("Inter Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    if s["vertical"]:
        fs = min(36, b["w"] * 0.35)
        x = bx + b["w"] * 0.5
        y0 = top + b["h"] * 0.15
        hgt = len(word) * fs * 1.05 + 20
        rgba(ctx, (0.04, 0.03, 0.06), 0.85)
        ctx.rectangle(x - fs * 0.62, y0 - 10, fs * 1.24, hgt)
        ctx.fill()
        radial_glow(ctx, x, y0 + hgt / 2, hgt * 0.8, col, 0.22 * a)
        for i, ch in enumerate(word):
            text_center(ctx, ch, x, y0 + fs * 0.55 + i * fs * 1.05, fs, mix(col, (1, 1, 1), 0.45), a)
    else:
        fs = min(44, b["w"] * 0.22)
        x = bx + b["w"] * 0.5
        y = top + b["h"] * s["y"] * 0.5 + 30
        ctx.set_font_size(fs)
        tw = ctx.text_extents(word).x_advance
        radial_glow(ctx, x, y, tw * 0.9, col, 0.25 * a)
        rgba(ctx, col, 0.9 * a)
        ctx.set_line_width(3)
        ctx.rectangle(x - tw / 2 - 14, y - fs * 0.75, tw + 28, fs * 1.5)
        ctx.stroke()
        text_center(ctx, word, x, y, fs, mix(col, (1, 1, 1), 0.5), a)


class City:
    """Three-layer skyline + street-level facades, shared by many scenes."""

    def __init__(self, base_y=820, seed=11):
        self.base_y = base_y
        self.far = CityLayer(seed, 0.15, base_y - 40, 260, 560, 60, 150, period=4200)
        self.mid = CityLayer(seed + 1, 0.4, base_y - 10, 200, 460, 90, 200, period=4600)
        self.near = CityLayer(seed + 2, 1.0, base_y, 300, 640, 180, 340, period=5600, neon=True)

    def draw(self, ctx, cam_x, x0, x1, p, t, horizon_glow=True, reflections=True, lit=1.0,
             near=True):
        draw_sky(ctx, p, x0 - 10, -600, x1 - x0 + 20, self.base_y + 600, t)
        if p.get("moon"):
            stars(ctx, x0, x1 - x0, self.base_y, t, 0.8)
            moon(ctx, x0 + (x1 - x0) * 0.78, 150, 38)
        if horizon_glow:
            g = cairo.LinearGradient(0, self.base_y - 380, 0, self.base_y)
            fc = _c(p["fog"])
            g.add_color_stop_rgba(0, *fc, 0)
            g.add_color_stop_rgba(1, *fc, 0.45)
            ctx.set_source(g)
            ctx.rectangle(x0 - 10, self.base_y - 380, x1 - x0 + 20, 380)
            ctx.fill()
        self.far.draw(ctx, cam_x, x0, x1, p, "far", t, lit)
        fog_band(ctx, x0, x1, self.base_y - 160, 200, _c(p["fog"]), 0.18, t)
        self.mid.draw(ctx, cam_x, x0, x1, p, "mid", t, lit)
        fog_band(ctx, x0, x1, self.base_y - 90, 140, _c(p["fog"]), 0.16, t + 3)
        if near:
            self.near.draw(ctx, cam_x, x0, x1, p, "near", t, lit)


def fog_band(ctx, x0, x1, y, h, col, a, t):
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgba(0, *col, 0)
    g.add_color_stop_rgba(0.5, *col, a)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.set_source(g)
    ctx.rectangle(x0 - 10, y, x1 - x0 + 20, h)
    ctx.fill()
    # drifting wisps
    for i in range(4):
        wx = x0 + ((i * 523 + t * 25) % (x1 - x0 + 600)) - 300
        radial_glow(ctx, wx, y + h * 0.5, 260, col, a * 0.6)


def street(ctx, x0, x1, ground_y, p, t, cam_x=0.0, wet=1.0, lamps=True, lamp_period=620,
           lamp_lit=1.0, curb=True):
    """Sidewalk + road strip below `ground_y` with wet reflections and lamps."""
    gcol = _c(p["ground"])
    vgrad(ctx, x0 - 10, ground_y, x1 - x0 + 20, 1200,
          [(0, mix(gcol, (1, 1, 1), 0.06)), (0.25, gcol), (1, mix(gcol, (0, 0, 0), 0.5))])
    # paving joints
    rgba(ctx, (0, 0, 0), 0.25)
    ctx.set_line_width(2)
    step = 160
    k0 = int((x0 - cam_x * 0) // step) - 1
    for k in range(k0, k0 + int((x1 - x0) / step) + 3):
        x = k * step
        ctx.move_to(x, ground_y + 4)
        ctx.line_to(x - 60, ground_y + 260)
    ctx.stroke()
    if curb:
        rgba(ctx, mix(gcol, (1, 1, 1), 0.15))
        ctx.rectangle(x0 - 10, ground_y + 175, x1 - x0 + 20, 10)
        ctx.fill()
    # puddles reflecting the sky glow
    r = rng(77)
    for i in range(14):
        px = (r.uniform(0, 3000) // 1)
        pk = math.floor((x0 - px) / 3000) + 1
        for kk in (pk - 1, pk, pk + 1):
            xx = px + kk * 3000
            if x0 - 300 < xx < x1 + 300:
                rgba(ctx, _c(p["fog"]), 0.14 * wet)
                ellipse(ctx, xx, ground_y + 40 + r.uniform(0, 120), r.uniform(80, 220), r.uniform(8, 18))
                ctx.fill()
    if lamps:
        k0 = math.floor(x0 / lamp_period) - 1
        k1 = math.floor(x1 / lamp_period) + 1
        for k in range(k0, k1 + 1):
            lx = k * lamp_period + 120
            street_lamp(ctx, lx, ground_y + 10, t, wet, lamp_lit, seed=k)


def street_lamp(ctx, x, y, t, wet=1.0, lit=1.0, seed=0, height=430):
    warm = hexc("#ffd28a")
    top = y - height
    # reflection streak on the wet ground
    if wet > 0 and lit > 0:
        g = cairo.LinearGradient(0, y, 0, y + 260)
        g.add_color_stop_rgba(0, *warm, 0.35 * wet * lit)
        g.add_color_stop_rgba(1, *warm, 0)
        ctx.set_source(g)
        ctx.rectangle(x + 30, y, 30, 260)
        ctx.fill()
    rgba(ctx, hexc("#0e0f1c"))
    ctx.rectangle(x - 5, top, 10, height)
    ctx.fill()
    ctx.rectangle(x - 9, y - 20, 18, 20)
    ctx.fill()
    ctx.set_line_width(8)
    ctx.move_to(x, top + 6)
    ctx.curve_to(x, top - 30, x + 60, top - 30, x + 60, top + 4)
    ctx.stroke()
    ctx.rectangle(x + 42, top + 2, 36, 10)
    ctx.fill()
    if lit > 0:
        fl = 1.0 - 0.05 * max(0, noise1(t * 9, seed))
        # light cone
        g = cairo.LinearGradient(0, top + 10, 0, y)
        g.add_color_stop_rgba(0, *warm, 0.28 * lit * fl)
        g.add_color_stop_rgba(1, *warm, 0.02 * lit)
        ctx.set_source(g)
        ctx.move_to(x + 46, top + 12)
        ctx.line_to(x + 74, top + 12)
        ctx.line_to(x + 230, y)
        ctx.line_to(x - 110, y)
        ctx.close_path()
        ctx.fill()
        radial_glow(ctx, x + 60, top + 14, 120, warm, 0.55 * lit * fl)
        rgba(ctx, hexc("#fff4d8"), lit)
        ellipse(ctx, x + 60, top + 13, 16, 4)
        ctx.fill()
        # pool of light on the ground
        rgba(ctx, warm, 0.10 * lit)
        ellipse(ctx, x + 60, y + 30, 210, 34)
        ctx.fill()


# ------------------------------------------------------------ 3D fly-through

class FlyCity:
    """Pseudo-3D street corridor: camera moves forward between facades."""

    def __init__(self, seed=21):
        r = rng(seed)
        self.b = []
        for side in (-1, 1):
            z = 0.0
            while z < 900:
                d = r.uniform(10, 26)
                self.b.append(dict(side=side, z0=z, z1=z + d, h=r.uniform(14, 60),
                                   x=side * r.uniform(11, 13), tone=r.uniform(-0.05, 0.05),
                                   lit=r.random((40, 12)), wc=r.integers(0, 4, (40, 12)),
                                   sign=(NEON_WORDS[r.integers(0, len(NEON_WORDS))],
                                         NEON_COLS[r.integers(0, len(NEON_COLS))])
                                   if r.random() < 0.5 else None,
                                   sh=r.uniform(4, 9)))
                z += d + r.uniform(0, 3)
        self.cars = [dict(z=r.uniform(0, 300), lane=r.choice([-1, 1]), v=r.uniform(8, 16)) for _ in range(10)]

    def draw(self, ctx, cz, t, p, sw=1920, sh=1080, cam_h=3.2, sway=0.0):
        f = sh * 0.9
        cx, cy = sw / 2 + sway * 40, sh * 0.56

        def proj(x, y, z):
            dz = z - cz
            if dz < 0.3:
                dz = 0.3
            return cx + f * (x - sway) / dz, cy - f * (y - cam_h) / dz

        draw_sky(ctx, p, 0, 0, sw, sh, t)
        stars(ctx, 0, sw, cy, t, 0.6)
        radial_glow(ctx, cx, cy, sh * 0.7, _c(p["fog"]), 0.45)
        # road
        rgba(ctx, _c(p["ground"]))
        ctx.rectangle(0, cy, sw, sh - cy)
        ctx.fill()
        # lane dashes
        rgba(ctx, (0.9, 0.9, 1), 0.55)
        z0 = math.floor(cz / 6) * 6
        for k in range(1, 60):
            z = z0 + k * 6
            a = proj(-0.15, 0, z)
            b = proj(0.15, 0, z)
            c = proj(0.15, 0, z + 2.5)
            d = proj(-0.15, 0, z + 2.5)
            if a[1] < cy + 1:
                continue
            ctx.move_to(*a)
            ctx.line_to(*b)
            ctx.line_to(*c)
            ctx.line_to(*d)
            ctx.fill()
        # sidewalks
        for side in (-1, 1):
            rgba(ctx, mix(_c(p["ground"]), (1, 1, 1), 0.08))
            a = proj(side * 7, 0, cz + 0.5)
            b = proj(side * 11, 0, cz + 0.5)
            c = proj(side * 11, 0, cz + 600)
            d = proj(side * 7, 0, cz + 600)
            ctx.move_to(*a)
            ctx.line_to(*b)
            ctx.line_to(*c)
            ctx.line_to(*d)
            ctx.fill()
        winc = [_c(c) for c in p["win"]]
        # buildings far -> near
        vis = [b for b in self.b if b["z1"] > cz + 0.5 and b["z0"] < cz + 420]
        vis.sort(key=lambda b: -b["z0"])
        for b in vis:
            z0 = max(b["z0"], cz + 0.5)
            x = b["x"]
            base = mix(_c(p["near"]), (0, 0, 0), 0.0)
            col = tuple(clamp(c + b["tone"]) for c in base)
            fog = clamp((b["z0"] - cz) / 420)
            col = mix(col, _c(p["fog"]), fog * 0.55)
            pts = [proj(x, 0, z0), proj(x, b["h"], z0), proj(x, b["h"], b["z1"]), proj(x, 0, b["z1"])]
            rgba(ctx, col)
            ctx.move_to(*pts[0])
            for q in pts[1:]:
                ctx.line_to(*q)
            ctx.fill()
            # front face (towards camera)
            pts2 = [proj(x, 0, b["z0"]), proj(x, b["h"], b["z0"]),
                    proj(x + b["side"] * 8, b["h"], b["z0"]), proj(x + b["side"] * 8, 0, b["z0"])]
            if b["z0"] > cz + 0.5:
                rgba(ctx, mix(col, (0, 0, 0), 0.3))
                ctx.move_to(*pts2[0])
                for q in pts2[1:]:
                    ctx.line_to(*q)
                ctx.fill()
            # windows
            nz = max(1, int((b["z1"] - b["z0"]) / 2.2))
            ny = max(1, int(b["h"] / 3.2))
            for wc_i in range(4):
                rgba(ctx, mix(winc[wc_i], _c(p["fog"]), fog * 0.6), 0.9)
                for iy in range(min(ny, 40)):
                    for iz in range(min(nz, 12)):
                        if b["lit"][iy, iz] < 1 - p["win_on"] or b["wc"][iy, iz] != wc_i:
                            continue
                        wz = b["z0"] + (iz + 0.3) * (b["z1"] - b["z0"]) / nz
                        if wz < cz + 0.6:
                            continue
                        wy = 1.5 + iy * 3.2
                        q1 = proj(x, wy, wz)
                        q2 = proj(x, wy + 1.6, wz + 1.0)
                        ctx.rectangle(min(q1[0], q2[0]), q2[1], abs(q2[0] - q1[0]), q1[1] - q2[1])
                ctx.fill()
            if b["sign"] and b["z0"] > cz + 2:
                word, scol = b["sign"]
                sz = b["z0"] + 1
                q = proj(x - b["side"] * 1.2, b["sh"], sz)
                dz = sz - cz
                fsz = f * 1.6 / dz
                if fsz > 4:
                    sc = hexc(scol)
                    radial_glow(ctx, q[0], q[1], fsz * 3.2, sc, 0.35 * (1 - fog))
                    text_center(ctx, word, q[0], q[1], fsz, mix(sc, (1, 1, 1), 0.5), 1 - fog * 0.7)
        # car light streaks
        for c_ in self.cars:
            z = (c_["z"] + t * c_["v"] * (1 if c_["lane"] > 0 else -1)) % 300 + cz + 4
            xx = c_["lane"] * 3.2
            q = proj(xx, 0.8, z)
            dz = z - cz
            rr = f * 0.35 / dz
            col = hexc("#ff3a3a") if c_["lane"] > 0 else hexc("#fff2c8")
            radial_glow(ctx, q[0] - rr * 1.2, q[1], rr * 4, col, 0.6)
            radial_glow(ctx, q[0] + rr * 1.2, q[1], rr * 4, col, 0.6)
            # reflection
            rgba(ctx, col, 0.18)
            ctx.rectangle(q[0] - rr * 1.6, q[1] + rr, rr * 3.2, rr * 10)
            ctx.fill()


# ------------------------------------------------------------ bedroom

def bedroom(ctx, t, rain=1.0, phone_light=0.0, window_city=None, cam_x=960, clock="02:30",
            lamp=0.0):
    wall = hexc("#1b2042")
    vgrad(ctx, -400, -200, 2800, 1100, [(0, mix(wall, (0, 0, 0), 0.4)), (1, wall)])
    # floor
    vgrad(ctx, -400, 860, 2800, 400, [(0, hexc("#2a2238")), (1, hexc("#120f1c"))])
    rgba(ctx, (0, 0, 0), 0.3)
    ctx.rectangle(-400, 856, 2800, 8)
    ctx.fill()
    # window with the rainy city outside
    wx, wy, ww, wh = 200, 150, 620, 560
    ctx.save()
    ctx.rectangle(wx, wy, ww, wh)
    ctx.clip()
    if window_city is not None:
        ctx.save()
        ctx.translate(wx - 300, wy - 260)
        ctx.scale(0.75, 0.75)
        window_city.draw(ctx, cam_x * 0.05 + t * 4, -100, 2200, pal("rain"), t)
        ctx.restore()
    rain_on_glass(ctx, wx, wy, ww, wh, t, rain)
    ctx.restore()
    # window light spilling into the room
    g = cairo.LinearGradient(wx, wy, wx + 500, 1080)
    g.add_color_stop_rgba(0, 0.45, 0.55, 0.95, 0.18)
    g.add_color_stop_rgba(1, 0.45, 0.55, 0.95, 0.0)
    ctx.set_source(g)
    ctx.move_to(wx, wy + wh)
    ctx.line_to(wx + ww, wy + wh)
    ctx.line_to(wx + ww + 520, 1100)
    ctx.line_to(wx + 180, 1100)
    ctx.close_path()
    ctx.fill()
    # frame
    rgba(ctx, hexc("#0c0e1f"))
    ctx.set_line_width(22)
    ctx.rectangle(wx, wy, ww, wh)
    ctx.stroke()
    ctx.set_line_width(12)
    ctx.move_to(wx + ww / 2, wy)
    ctx.line_to(wx + ww / 2, wy + wh)
    ctx.move_to(wx, wy + wh * 0.45)
    ctx.line_to(wx + ww, wy + wh * 0.45)
    ctx.stroke()
    rgba(ctx, hexc("#2b2f55"))
    ctx.rectangle(wx - 40, wy + wh + 8, ww + 80, 22)
    ctx.fill()
    # poster + photo strip on the wall (warm memory)
    rgba(ctx, hexc("#0f1228"))
    ctx.rectangle(1040, 210, 230, 300)
    ctx.fill()
    vgrad(ctx, 1052, 222, 206, 276, [(0, hexc("#ff9a5c")), (1, hexc("#7a3b6a"))], 0.55)
    text_center(ctx, "TOUR", 1155, 440, 40, hexc("#ffe2b0"), 0.5)
    for i, ang in enumerate((-0.08, 0.06, -0.03)):
        ctx.save()
        ctx.translate(1380 + i * 130, 300 + i * 18)
        ctx.rotate(ang)
        rgba(ctx, hexc("#e8e2d8"), 0.85)
        ctx.rectangle(-50, -60, 100, 120)
        ctx.fill()
        vgrad(ctx, -42, -52, 84, 84, [(0, hexc("#ffb36a")), (1, hexc("#c4566a"))], 0.75)
        rgba(ctx, hexc("#e0552b"), 0.8)
        ellipse(ctx, -8, -8, 12, 18)
        ctx.fill()
        ctx.restore()
    # bed
    rgba(ctx, hexc("#141633"))
    ctx.rectangle(980, 690, 900, 220)
    ctx.fill()
    vgrad(ctx, 980, 640, 900, 90, [(0, hexc("#3b4a8a")), (1, hexc("#26305e"))])
    rgba(ctx, hexc("#4a5aa0"))
    ellipse(ctx, 1730, 640, 120, 40)
    ctx.fill()
    rgba(ctx, hexc("#0c0d1f"))
    ctx.rectangle(1860, 520, 40, 400)
    ctx.fill()
    # nightstand + digital clock
    rgba(ctx, hexc("#10122a"))
    ctx.rectangle(1700 - 900, 720, 150, 160)
    ctx.fill()
    rgba(ctx, hexc("#06070f"))
    ctx.rectangle(820, 670, 110, 50)
    ctx.fill()
    radial_glow(ctx, 875, 695, 110, hexc("#ff3b5c"), 0.25)
    text_center(ctx, clock, 875, 695, 34, hexc("#ff4a6a"), 1.0, font="DejaVu Sans Mono")
    if lamp > 0:
        radial_glow(ctx, 860, 600, 300, hexc("#ffcf8a"), 0.3 * lamp)
    # phone light glow in the room
    if phone_light > 0:
        radial_glow(ctx, 1260, 560, 520, hexc("#7aa8ff"), 0.22 * phone_light)


def rain_on_glass(ctx, x, y, w, h, t, amount=1.0, seed=3, n=90):
    """Droplets sliding down a window pane."""
    rgba(ctx, hexc("#1a2140"), 0.35 * amount)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    r = rng(seed)
    xs = r.uniform(0, 1, n)
    sp = r.uniform(20, 160, n)
    sz = r.uniform(2, 7, n)
    off = r.uniform(0, 1, n)
    for i in range(int(n * amount)):
        yy = y + ((off[i] * h + t * sp[i]) % (h + 40)) - 20
        xx = x + xs[i] * w + math.sin(t * 0.7 + i) * 3
        rgba(ctx, (0.8, 0.88, 1.0), 0.22)
        ctx.set_line_width(sz[i] * 0.45)
        ctx.move_to(xx, yy - sp[i] * 0.5)
        ctx.line_to(xx, yy)
        ctx.stroke()
        rgba(ctx, (0.9, 0.95, 1.0), 0.55)
        ellipse(ctx, xx, yy, sz[i] * 0.55, sz[i] * 0.7)
        ctx.fill()
        rgba(ctx, (1, 1, 1), 0.8)
        ctx.arc(xx - sz[i] * 0.15, yy - sz[i] * 0.2, sz[i] * 0.16, 0, 6.3)
        ctx.fill()
    # static beads
    r2 = rng(seed + 9)
    for _ in range(int(160 * amount)):
        xx, yy, s_ = x + r2.uniform(0, w), y + r2.uniform(0, h), r2.uniform(1, 3.2)
        rgba(ctx, (0.85, 0.92, 1), 0.35)
        ctx.arc(xx, yy, s_, 0, 6.3)
        ctx.fill()


# ------------------------------------------------------------ park bench

def bench(ctx, x, y, s=1.0, col=hexc("#3a2a2a")):
    rgba(ctx, mix(col, (0, 0, 0), 0.3))
    for dx in (-150, 150):
        ctx.rectangle(x + dx * s - 6 * s, y - 70 * s, 12 * s, 70 * s)
    ctx.fill()
    rgba(ctx, col)
    for i in range(3):
        ctx.rectangle(x - 190 * s, y - 80 * s - i * 14 * s, 380 * s, 10 * s)
    for i in range(3):
        ctx.rectangle(x - 190 * s, y - 150 * s - i * 22 * s, 380 * s, 14 * s)
    ctx.fill()
    rgba(ctx, mix(col, (0, 0, 0), 0.4))
    for dx in (-160, 160):
        ctx.rectangle(x + dx * s - 5 * s, y - 210 * s, 10 * s, 130 * s)
    ctx.fill()


def tree(ctx, x, y, h, col, t, seed=0):
    rgba(ctx, mix(col, (0, 0, 0), 0.25))
    ctx.move_to(x - 12, y)
    ctx.line_to(x - 6, y - h * 0.55)
    ctx.line_to(x + 6, y - h * 0.55)
    ctx.line_to(x + 12, y)
    ctx.fill()
    r = rng(seed)
    rgba(ctx, col)
    for i in range(7):
        ang = i / 7 * 6.28
        rr = h * 0.22
        sway = math.sin(t * 0.8 + i) * 3
        ctx.arc(x + math.cos(ang) * rr * 0.9 + sway, y - h * 0.72 + math.sin(ang) * rr * 0.6,
                rr * r.uniform(0.6, 0.9), 0, 6.3)
        ctx.fill()


def sun(ctx, x, y, r, a=1.0):
    radial_glow(ctx, x, y, r * 9, hexc("#ffb36a"), 0.45 * a)
    radial_glow(ctx, x, y, r * 3, hexc("#ffe2a8"), 0.7 * a)
    rgba(ctx, hexc("#fff4dc"), a)
    ctx.arc(x, y, r, 0, 6.3)
    ctx.fill()
