"""Atmospheric effects (rain, bokeh, particles, light leaks) and the
per-frame post-processing chain (DOF blur, bloom, grade, vignette, grain,
chromatic aberration, flashes)."""
import math
import os

import cairo
import cv2
import numpy as np

from .core import clamp, ellipse, hexc, mix, radial_glow, rgba, rng


class Rain:
    def __init__(self, n=900, seed=1):
        r = rng(seed)
        self.x = r.uniform(-0.2, 1.2, n)
        self.y = r.uniform(0, 1, n)
        self.layer = r.choice([0, 1, 2], n, p=[0.55, 0.3, 0.15])
        self.sp = r.uniform(0.8, 1.2, n)

    def draw(self, ctx, sw, sh, rt, intensity=1.0, angle=0.18, speed=1.0, color=(0.75, 0.82, 1.0),
             frozen=False):
        """rt: rain clock (scenes may slow or freeze it). speed scales streak length."""
        n = int(len(self.x) * clamp(intensity, 0, 1))
        if n <= 0:
            return
        sc = sh / 1080
        for layer, (vel, ln, wd, a) in enumerate(((1.6, 38, 1.1, 0.32), (2.3, 60, 1.8, 0.42),
                                                    (3.2, 95, 2.8, 0.5))):
            m = self.layer[:n] == layer
            xs = self.x[:n][m]
            ys = self.y[:n][m]
            sp = self.sp[:n][m]
            yy = ((ys + rt * vel * sp) % 1.15 - 0.1) * sh
            xx = xs * sw + yy * angle
            L = ln * sc * (0.12 if frozen else max(0.15, min(1.6, speed)))
            rgba(ctx, color, a * min(1.0, intensity * 1.4))
            ctx.set_line_width(wd * sc)
            ctx.set_line_cap(1)
            dx = -angle * L
            for x_, y_ in zip(xx, yy):
                ctx.move_to(x_, y_)
                ctx.line_to(x_ + dx, y_ - L)
            ctx.stroke()

    @staticmethod
    def splashes(ctx, x0, x1, y0, y1, t, intensity=1.0, seed=4, n=60):
        r = rng(seed)
        xs = r.uniform(0, 1, n)
        ys = r.uniform(0, 1, n)
        ph = r.uniform(0, 1, n)
        rate = r.uniform(1.5, 3.0, n)
        for i in range(int(n * intensity)):
            k = (t * rate[i] + ph[i])
            f = k % 1.0
            cyc = int(k)
            jitter = ((cyc * 7919 + i * 104729) % 1000) / 1000
            x = x0 + ((xs[i] + jitter) % 1) * (x1 - x0)
            y = y0 + ys[i] * (y1 - y0)
            rgba(ctx, (0.8, 0.88, 1.0), 0.45 * (1 - f))
            ctx.set_line_width(1.6)
            ellipse(ctx, x, y, 4 + 22 * f, 1.5 + 5 * f)
            ctx.stroke()


class Bokeh:
    def __init__(self, n=60, seed=2, cols=("#ff5fd2", "#46d8ff", "#ffcf6a", "#a46bff", "#ff8a5a")):
        r = rng(seed)
        self.x = r.uniform(0, 1, n)
        self.y = r.uniform(0, 1, n)
        self.r = r.uniform(18, 75, n)
        self.c = [hexc(cols[i]) for i in r.integers(0, len(cols), n)]
        self.ph = r.uniform(0, 6.28, n)
        self.v = r.uniform(-1, 1, n)

    def draw(self, ctx, sw, sh, t, alpha=1.0, pan=0.0, drift=1.0, scale=1.0, cols=None):
        sc = sh / 1080 * scale
        for i in range(len(self.x)):
            x = ((self.x[i] * 1.4 + pan * (0.4 + self.r[i] / 120) + t * 0.006 * self.v[i] * drift) % 1.4 - 0.2) * sw
            y = (self.y[i] + math.sin(t * 0.3 + self.ph[i]) * 0.02 * drift) * sh
            rr = self.r[i] * sc
            a = alpha * (0.22 + 0.12 * math.sin(t * 1.3 + self.ph[i]))
            col = self.c[i] if cols is None else cols[i % len(cols)]
            g = cairo.RadialGradient(x, y, 0, x, y, rr)
            g.add_color_stop_rgba(0, *col, a * 0.7)
            g.add_color_stop_rgba(0.82, *col, a)
            g.add_color_stop_rgba(1, *col, 0)
            ctx.set_source(g)
            ctx.arc(x, y, rr, 0, 6.283)
            ctx.fill()


class Particles:
    """Floating dust/embers; `mode='up'` rises (memories), 'drift' floats."""

    def __init__(self, n=120, seed=3):
        r = rng(seed)
        self.x = r.uniform(0, 1, n)
        self.y = r.uniform(0, 1, n)
        self.s = r.uniform(1.0, 4.0, n)
        self.v = r.uniform(0.01, 0.05, n)
        self.ph = r.uniform(0, 6.28, n)

    def draw(self, ctx, sw, sh, t, col=hexc("#ffd28a"), alpha=1.0, mode="up"):
        sc = sh / 1080
        rgba(ctx, col, alpha)
        for i in range(len(self.x)):
            if mode == "up":
                y = ((self.y[i] - t * self.v[i]) % 1.0) * sh
            else:
                y = ((self.y[i] + math.sin(t * 0.4 + self.ph[i]) * 0.03) % 1.0) * sh
            x = ((self.x[i] + math.sin(t * 0.5 + self.ph[i]) * 0.02) % 1.0) * sw
            tw = 0.5 + 0.5 * math.sin(t * 2.0 + self.ph[i])
            rgba(ctx, col, alpha * (0.35 + 0.65 * tw))
            ctx.arc(x, y, self.s[i] * sc, 0, 6.283)
            ctx.fill()


def light_leak(ctx, sw, sh, t, a=1.0, col1=hexc("#ff8a3a"), col2=hexc("#ffcf6a")):
    x = sw * (0.15 + 0.7 * (0.5 + 0.5 * math.sin(t * 0.35)))
    radial_glow(ctx, x, sh * 0.15, sh * 0.9, col1, 0.32 * a)
    radial_glow(ctx, sw - x * 0.6, sh * 0.95, sh * 0.7, col2, 0.22 * a)


def dissolve_particles(ctx, cx, cy, w, h, prog, t, seed=9, n=260, col=hexc("#ffc27a")):
    """Sparks streaming away from a figure as it dissolves (prog 0..1)."""
    r = rng(seed)
    xs = r.normal(0, 0.3, n)
    ys = r.uniform(-1, 0, n)
    vx = r.normal(0.2, 0.5, n)
    vy = r.uniform(-1.4, -0.2, n)
    s = r.uniform(1.5, 5, n)
    delay = r.uniform(0, 0.6, n)
    for i in range(n):
        p = clamp((prog - delay[i]) / 0.4)
        if p <= 0 or p >= 1:
            continue
        x = cx + xs[i] * w + vx[i] * p * w * 1.5 + math.sin(t * 3 + i) * 4
        y = cy + ys[i] * h + vy[i] * p * h * 0.6
        rgba(ctx, mix(col, (1, 1, 1), 0.3), (1 - p) * 0.95)
        ctx.arc(x, y, s[i] * (1 - p * 0.5), 0, 6.283)
        ctx.fill()


# ---------------------------------------------------------------- post FX

GRAIN_K = float(os.environ.get("MV_GRAIN", "0.45"))


class Post:
    def __init__(self, sw, sh):
        self.sw, self.sh = sw, sh
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        d = np.sqrt(((xx - sw / 2) / (sw / 2)) ** 2 + ((yy - sh / 2) / (sh / 2)) ** 2) / math.sqrt(2)
        self.vig_d = d
        self._vig_cache = {}
        r = rng(42)
        self.grain = [r.normal(128, 30, (sh, sw, 1)).clip(0, 255).astype(np.uint8).repeat(3, 2)
                      for _ in range(4)]

    def vignette(self, strength):
        key = round(strength, 2)
        if key not in self._vig_cache:
            m = 1 - strength * np.clip((self.vig_d - 0.35) / 0.65, 0, 1) ** 1.6
            self._vig_cache[key] = (m * 255).astype(np.uint8)[..., None].repeat(3, 2)
            if len(self._vig_cache) > 30:
                self._vig_cache.pop(next(iter(self._vig_cache)))
        return self._vig_cache[key]

    @staticmethod
    def lut(tint=(1, 1, 1), lift=(0, 0, 0), gamma=1.0, contrast=1.0, exposure=1.0):
        x = np.arange(256, dtype=np.float32) / 255
        out = []
        # BGR order for cv2
        for ch in (2, 1, 0):
            y = x * exposure
            y = (y - 0.5) * contrast + 0.5
            y = np.clip(y, 0, 1) ** gamma
            y = y * tint[ch] + lift[ch] * (1 - y)
            out.append(np.clip(y * 255, 0, 255))
        return np.stack(out, 1).astype(np.uint8).reshape(1, 256, 3)

    def process(self, img, g, frame_idx):
        """img: HxWx3 uint8 BGR (contiguous). g: grade dict."""
        sw, sh = self.sw, self.sh
        if g.get("blur", 0) > 0.3:
            img = cv2.GaussianBlur(img, (0, 0), g["blur"])
        bloom = g.get("bloom", 0.6)
        if bloom > 0:
            small = cv2.resize(img, (sw // 4, sh // 4), interpolation=cv2.INTER_AREA)
            bright = cv2.subtract(small, np.full_like(small, int(g.get("bloom_thr", 150))))
            b1 = cv2.GaussianBlur(bright, (0, 0), 4 * sh / 1080)
            b2 = cv2.GaussianBlur(bright, (0, 0), 14 * sh / 1080)
            bl = cv2.addWeighted(b1, 0.6, b2, 0.9, 0)
            up = cv2.resize(bl, (sw, sh), interpolation=cv2.INTER_LINEAR)
            img = cv2.addWeighted(img, 1.0, up, bloom * 1.6, 0)
        sat = g.get("sat", 1.0)
        if abs(sat - 1.0) > 0.01:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            img = cv2.addWeighted(img, sat, gray3, 1 - sat, 0)
        lut = g.get("_lut")
        if lut is not None:
            img = cv2.LUT(img, lut)
        ca = g.get("ca", 0)
        if ca >= 1:
            k = int(ca * sh / 1080)
            if k > 0:
                b, gg, r = cv2.split(img)
                r = np.roll(r, k, axis=1)
                b = np.roll(b, -k, axis=1)
                img = cv2.merge([b, gg, r])
        v = g.get("vignette", 0.45)
        if v > 0:
            img = cv2.multiply(img, self.vignette(v), scale=1 / 255)
        gr = g.get("grain", 0.06) * GRAIN_K
        if gr > 0:
            img = cv2.addWeighted(img, 1.0, self.grain[frame_idx % 4], gr, -128 * gr)
        fl = g.get("flash", 0)
        if fl > 0.004:
            col = g.get("flash_col", (255, 255, 255))
            img = cv2.addWeighted(img, 1.0, np.full_like(img, col), fl, 0)
        fade = g.get("fade", 1.0)
        if fade < 0.999:
            img = cv2.convertScaleAbs(img, alpha=max(0.0, fade))
        lb = g.get("letterbox", 0)
        if lb > 0:
            h = int(lb * sh)
            img[:h] = 0
            img[sh - h:] = 0
        return img


def blur_surface(surf, sigma, downscale=4):
    """In-place blur of a cairo RGB24 surface (used for depth-of-field)."""
    surf.flush()
    w, h = surf.get_width(), surf.get_height()
    arr = np.ndarray((h, surf.get_stride() // 4, 4), np.uint8, surf.get_data())
    view = arr[:, :w, :3]
    small = cv2.resize(view, (w // downscale, h // downscale), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), max(0.5, sigma / downscale))
    view[:] = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    surf.mark_dirty()
