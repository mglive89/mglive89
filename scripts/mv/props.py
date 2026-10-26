"""Props: smartphone UI (lock screen + chat), reaching hands, title type."""
import math

import cairo

from .core import (OUTLINE, clamp, ellipse, hexc, lerp, mix, radial_glow, rgba,
                   text_center)


def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def text_left(ctx, txt, x, y, size, col, a=1.0, font="Inter", weight=cairo.FONT_WEIGHT_NORMAL):
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)
    ctx.move_to(x, y)
    rgba(ctx, col, a)
    ctx.show_text(txt)
    return ctx.text_extents(txt).x_advance


def text_w(ctx, txt, size, font="Inter", weight=cairo.FONT_WEIGHT_NORMAL):
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)
    return ctx.text_extents(txt).x_advance


def mini_avatar(ctx, x, y, r):
    """Tiny portrait of the girl (orange hair, blue cap) for the chat header."""
    ctx.save()
    ctx.arc(x, y, r, 0, 6.3)
    ctx.clip()
    rgba(ctx, hexc("#ffb37a"))
    ctx.paint()
    rgba(ctx, hexc("#e0552b"))
    ellipse(ctx, x, y + r * 0.35, r * 0.75, r * 0.9)
    ctx.fill()
    rgba(ctx, hexc("#f6cfb0"))
    ellipse(ctx, x, y + r * 0.1, r * 0.45, r * 0.5)
    ctx.fill()
    rgba(ctx, hexc("#2c63c0"))
    ellipse(ctx, x, y - r * 0.32, r * 0.55, r * 0.3, math.pi, 2 * math.pi)
    ctx.fill()
    ctx.rectangle(x - r * 0.1, y - r * 0.36, r * 0.75, r * 0.1)
    ctx.fill()
    ctx.restore()


def phone_ui(ctx, cx, cy, h, t, mode="chat", status="online", n_msgs=3, typing=0.0,
             clock="02:30", glow=1.0, lock_text="Keine neuen Nachrichten", draft="",
             notif=0.0):
    w = h * 0.49
    x, y = cx - w / 2, cy - h / 2
    radial_glow(ctx, cx, cy, h * 0.9, hexc("#6a8cff"), 0.18 * glow)
    # body
    rgba(ctx, hexc("#0b0b10"))
    rrect(ctx, x, y, w, h, w * 0.14)
    ctx.fill()
    rgba(ctx, hexc("#3a3a48"))
    ctx.set_line_width(h * 0.006)
    rrect(ctx, x, y, w, h, w * 0.14)
    ctx.stroke()
    m = w * 0.035
    sx, sy, sw, sh = x + m, y + m, w - 2 * m, h - 2 * m
    ctx.save()
    rrect(ctx, sx, sy, sw, sh, w * 0.11)
    ctx.clip()
    u = sh / 100.0   # screen unit
    if mode == "lock":
        g = cairo.LinearGradient(sx, sy, sx + sw, sy + sh)
        g.add_color_stop_rgb(0, *hexc("#3a2a6b"))
        g.add_color_stop_rgb(0.6, *hexc("#c45a6a"))
        g.add_color_stop_rgb(1, *hexc("#ffb36a"))
        ctx.set_source(g)
        ctx.paint()
        # wallpaper: the two of them as silhouettes against a sunset
        radial_glow(ctx, sx + sw * 0.5, sy + sh * 0.62, sw * 0.6, hexc("#ffe2a8"), 0.7)
        for k, (ox, hh, col) in enumerate(((0.38, 1.0, "#2a1a3a"), (0.62, 0.95, "#2a1a3a"))):
            px = sx + sw * ox
            rgba(ctx, hexc(col), 0.85)
            ellipse(ctx, px, sy + sh * 0.66 - 22 * u * hh * 0.35, 3.2 * u, 3.6 * u)
            ctx.fill()
            rrect(ctx, px - 4 * u, sy + sh * 0.66 - 4 * u * hh, 8 * u, 40 * u, 3 * u)
            ctx.fill()
        rgba(ctx, (0, 0, 0), 0.25)
        ctx.paint()
        text_center(ctx, "Samstag, 24. Oktober", cx, sy + 15 * u, 2.6 * u, (1, 1, 1), 0.85,
                    font="Inter", weight=cairo.FONT_WEIGHT_NORMAL)
        text_center(ctx, clock, cx, sy + 24 * u, 11 * u, (1, 1, 1), 0.95, font="Inter Display")
        # notification pill
        py = sy + 40 * u
        rgba(ctx, (1, 1, 1), 0.18)
        rrect(ctx, sx + 5 * u, py, sw - 10 * u, 9 * u, 3 * u)
        ctx.fill()
        text_center(ctx, lock_text, cx, py + 4.5 * u, 2.6 * u, (1, 1, 1), 0.9,
                    font="Inter", weight=cairo.FONT_WEIGHT_NORMAL)
        if notif > 0:
            rgba(ctx, (1, 1, 1), 0.9 * notif)
            ctx.arc(cx, sy + 92 * u, 1.2 * u, 0, 6.3)
            ctx.fill()
    else:
        rgba(ctx, hexc("#0e1220"))
        ctx.paint()
        # subtle chat wallpaper pattern
        rgba(ctx, (1, 1, 1), 0.025)
        for i in range(40):
            ctx.arc(sx + (i * 37 % 100) / 100 * sw, sy + (i * 53 % 100) / 100 * sh, 1.4 * u, 0, 6.3)
            ctx.fill()
        # status bar
        text_left(ctx, clock, sx + 7 * u, sy + 4.6 * u, 2.4 * u, (1, 1, 1), 0.9, weight=cairo.FONT_WEIGHT_BOLD)
        rgba(ctx, (1, 1, 1), 0.85)
        rrect(ctx, sx + sw - 9 * u, sy + 2.5 * u, 5 * u, 2.2 * u, 0.6 * u)
        ctx.set_line_width(0.3 * u)
        ctx.stroke()
        ctx.rectangle(sx + sw - 8.6 * u, sy + 2.9 * u, 2.0 * u, 1.4 * u)
        ctx.fill()
        # header
        rgba(ctx, hexc("#161b2e"))
        ctx.rectangle(sx, sy + 6.5 * u, sw, 9 * u)
        ctx.fill()
        rgba(ctx, hexc("#7aa8ff"))
        ctx.set_line_width(0.5 * u)
        ctx.move_to(sx + 5 * u, sy + 9.5 * u)
        ctx.line_to(sx + 3.5 * u, sy + 11 * u)
        ctx.line_to(sx + 5 * u, sy + 12.5 * u)
        ctx.stroke()
        mini_avatar(ctx, sx + 11 * u, sy + 11 * u, 3.2 * u)
        text_left(ctx, "Du ♥", sx + 16 * u, sy + 10.6 * u, 2.9 * u, (1, 1, 1), 1,
                  font="DejaVu Sans", weight=cairo.FONT_WEIGHT_BOLD)
        scol = hexc("#5affb0") if status == "online" else (hexc("#7aa8ff") if "schreibt" in status else (0.7, 0.7, 0.75))
        text_left(ctx, status, sx + 16 * u, sy + 13.6 * u, 2.1 * u, scol, 0.95)
        # messages (his, right aligned, blue)
        msgs = [("Hey, bist du noch wach?", "02:14"),
                ("Ich muss die ganze Zeit an dich denken", "02:21"),
                ("Warum antwortest du nicht?", "02:30")]
        my = sy + 22 * u
        text_center(ctx, "HEUTE", cx, my, 1.8 * u, (0.7, 0.72, 0.8), 0.7, font="Inter",
                    weight=cairo.FONT_WEIGHT_NORMAL)
        my += 4 * u
        fs = 2.5 * u
        for i, (msg, ts) in enumerate(msgs):
            vis = clamp(n_msgs - i)
            if vis <= 0:
                break
            words = msg.split(" ")
            lines, cur = [], ""
            for wd in words:
                trial = (cur + " " + wd).strip()
                if text_w(ctx, trial, fs) > sw * 0.62:
                    lines.append(cur)
                    cur = wd
                else:
                    cur = trial
            lines.append(cur)
            bw = max(text_w(ctx, ln, fs) for ln in lines) + 5 * u
            bw = max(bw, 16 * u)
            bh = len(lines) * 3.6 * u + 5.2 * u
            bx = sx + sw - bw - 3 * u
            oy = (1 - vis) * 3 * u
            rgba(ctx, hexc("#2f6bff"), vis)
            rrect(ctx, bx, my + oy, bw, bh, 2.4 * u)
            ctx.fill()
            for k, ln in enumerate(lines):
                text_left(ctx, ln, bx + 2.5 * u, my + oy + 3.9 * u + k * 3.6 * u, fs, (1, 1, 1), vis)
            text_left(ctx, ts + "  ✓✓", bx + bw - 12.5 * u, my + oy + bh - 1.3 * u, 1.6 * u,
                      (0.82, 0.88, 1.0), 0.8 * vis, font="DejaVu Sans")
            my += bh + 2.5 * u
        if typing > 0:
            rgba(ctx, hexc("#232a40"), typing)
            rrect(ctx, sx + 3 * u, my + 1 * u, 13 * u, 6 * u, 3 * u)
            ctx.fill()
            for k in range(3):
                b = 0.5 + 0.5 * math.sin(t * 8 - k * 0.9)
                rgba(ctx, (0.85, 0.88, 1), typing * (0.4 + 0.6 * b))
                ctx.arc(sx + 6.5 * u + k * 3 * u, my + 4 * u - b * 0.6 * u, 0.9 * u, 0, 6.3)
                ctx.fill()
        # input bar
        rgba(ctx, hexc("#161b2e"))
        ctx.rectangle(sx, sy + sh - 9 * u, sw, 9 * u)
        ctx.fill()
        rgba(ctx, hexc("#232a40"))
        rrect(ctx, sx + 3 * u, sy + sh - 7.5 * u, sw - 14 * u, 5.4 * u, 2.7 * u)
        ctx.fill()
        if draft:
            text_left(ctx, draft, sx + 5.5 * u, sy + sh - 4 * u, 2.3 * u, (1, 1, 1), 0.95)
            if int(t * 2) % 2 == 0:
                dw = text_w(ctx, draft, 2.3 * u)
                rgba(ctx, hexc("#7aa8ff"))
                ctx.rectangle(sx + 5.8 * u + dw, sy + sh - 6.3 * u, 0.3 * u, 3 * u)
                ctx.fill()
        else:
            text_left(ctx, "Nachricht", sx + 5.5 * u, sy + sh - 4 * u, 2.3 * u, (0.6, 0.62, 0.7), 0.8)
        rgba(ctx, hexc("#2f6bff"))
        ctx.arc(sx + sw - 6 * u, sy + sh - 4.8 * u, 2.7 * u, 0, 6.3)
        ctx.fill()
    # glass glare
    g = cairo.LinearGradient(sx, sy, sx + sw, sy + sh)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.07)
    g.add_color_stop_rgba(0.45, 1, 1, 1, 0.0)
    ctx.set_source(g)
    ctx.paint()
    ctx.restore()
    # notch
    rgba(ctx, hexc("#0b0b10"))
    rrect(ctx, cx - w * 0.16, y + m + h * 0.008, w * 0.32, h * 0.03, h * 0.015)
    ctx.fill()


def holding_hand(ctx, cx, cy, h, skin, sleeve, light, part="front"):
    """Hand holding the phone from below: 'back' = arm + palm (drawn before
    the phone), 'front' = fingers on the left edge and thumb on the right."""
    w = h * 0.49
    sk = light(skin)

    def oval(x, y, rx, ry, col):
        rgba(ctx, OUTLINE)
        ellipse(ctx, x, y, rx + h * 0.006, ry + h * 0.006)
        ctx.fill()
        rgba(ctx, col)
        ellipse(ctx, x, y, rx, ry)
        ctx.fill()

    if part == "back":
        ctx.set_line_cap(1)
        for wd, col in ((h * 0.36 + h * 0.012, OUTLINE), (h * 0.36, light(sleeve))):
            rgba(ctx, col)
            ctx.set_line_width(wd)
            ctx.move_to(cx - w * 0.2, cy + h * 1.3)
            ctx.line_to(cx - w * 0.05, cy + h * 0.72)
            ctx.stroke()
        oval(cx - w * 0.02, cy + h * 0.42, w * 0.5, h * 0.17, sk)
        return
    # fingers curling round the left edge
    for k in range(4):
        oval(cx - w * 0.5 - w * 0.01, cy - h * 0.0 + k * h * 0.075, w * 0.055, h * 0.03, sk)
    # thumb on the right edge
    oval(cx + w * 0.5, cy + h * 0.22, w * 0.05, h * 0.07, sk)


def reaching_arm(ctx, x0, y0, x1, y1, scale, skin, sleeve, cuff, flip=1, curl=0.0):
    """Arm from (x0,y0) to a hand at (x1,y1) with an extended index finger."""
    ctx.set_line_cap(1)
    ctx.set_line_join(1)
    for wdt, col in ((44 * scale + 8, OUTLINE), (44 * scale, sleeve)):
        rgba(ctx, col)
        ctx.set_line_width(wdt)
        ctx.move_to(x0, y0)
        ctx.curve_to(lerp(x0, x1, 0.4), y0, lerp(x0, x1, 0.6), y1, x1 - flip * 60 * scale, y1)
        ctx.stroke()
    rgba(ctx, cuff)
    ctx.set_line_width(46 * scale)
    ctx.move_to(x1 - flip * 75 * scale, y1)
    ctx.line_to(x1 - flip * 62 * scale, y1)
    ctx.stroke()
    ctx.save()
    ctx.translate(x1, y1)
    ctx.scale(flip * scale, scale)

    def shape(stroke):
        # palm
        ellipse(ctx, -18, 4, 30, 24)
        ctx.new_sub_path()
        # extended index finger
        ctx.save()
        ctx.rotate(-0.08 + curl * 0.3)
        ctx.rectangle(0, -14, 52, 13)
        ctx.restore()
        ctx.new_sub_path()
        for k in range(3):
            ellipse(ctx, 10 - k * 2, 2 + k * 9, 14 - curl * 4, 6)
            ctx.new_sub_path()
        ellipse(ctx, -16, -16, 16, 8)
    shape(True)
    rgba(ctx, OUTLINE)
    ctx.set_line_width(7)
    ctx.stroke()
    shape(False)
    rgba(ctx, skin)
    ctx.fill()
    ctx.save()
    ctx.rotate(-0.08 + curl * 0.3)
    rgba(ctx, skin)
    ctx.arc(52, -7.5, 6.5, -math.pi / 2, math.pi / 2)
    ctx.fill()
    rgba(ctx, mix(skin, (1, 1, 1), 0.5), 0.8)
    ellipse(ctx, 50, -9, 3.5, 2.2)
    ctx.fill()
    ctx.restore()
    ctx.restore()


def title(ctx, sw, sh, text, t, a=1.0, scale=1.0, glow_col=hexc("#ff4fd8"), col2=hexc("#46e6ff"),
          y=None, split=0.0, sub=None, flicker=True):
    """Neon title type with layered glow and an optional RGB split."""
    if a <= 0:
        return
    base = min(sw, sh * 1.78)
    size = base * 0.115 * scale
    y = sh * 0.5 if y is None else y
    fl = 1.0
    if flicker:
        ph = (t * 5.3) % 7.0
        fl = 0.55 if 0.0 < ph < 0.07 or 0.3 < ph < 0.36 else 1.0
    ctx.select_font_face("Inter Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    spacing = size * 0.06
    radial_glow(ctx, sw / 2, y, size * 4.2, glow_col, 0.22 * a * fl)
    if split > 0:
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_ADD)
        text_center(ctx, text, sw / 2 - split, y, size, (1, 0.1, 0.4), 0.55 * a, spacing=spacing)
        text_center(ctx, text, sw / 2 + split, y, size, (0.1, 0.7, 1), 0.55 * a, spacing=spacing)
        ctx.restore()
    # glow layers via outlined text paths
    ctx.set_font_size(size)
    for wdt, al in ((size * 0.22, 0.10), (size * 0.12, 0.18), (size * 0.05, 0.4)):
        _text_path(ctx, text, sw / 2, y, size, spacing)
        rgba(ctx, glow_col, al * a * fl)
        ctx.set_line_width(wdt)
        ctx.set_line_join(1)
        ctx.stroke()
    text_center(ctx, text, sw / 2, y, size, mix(glow_col, (1, 1, 1), 0.75), a * fl, spacing=spacing)
    if sub:
        text_center(ctx, sub, sw / 2, y + size * 0.85, size * 0.22, (1, 1, 1), a * 0.85,
                    font="Inter", weight=cairo.FONT_WEIGHT_NORMAL, spacing=size * 0.06)


def _text_path(ctx, txt, x, y, size, spacing):
    ctx.set_font_size(size)
    widths = [ctx.text_extents(ch).x_advance for ch in txt]
    total = sum(widths) + spacing * (len(txt) - 1)
    ext = ctx.text_extents(txt)
    cx = x - total / 2
    for ch, w_ in zip(txt, widths):
        ctx.move_to(cx, y - (ext.y_bearing + ext.height / 2))
        ctx.text_path(ch)
        cx += w_ + spacing
