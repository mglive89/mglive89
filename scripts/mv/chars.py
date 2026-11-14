"""2D cut-out rigs for the two leads: the boy (glasses, blue/turquoise jacket)
and the girl (long orange-red hair, blue cap, dark jacket, green skateboard).

Every body part is drawn separately (legs, torso, arms, hands, head, eyes,
glasses, mouth, hair, cap, board) from a joint-angle pose, so scenes can
animate walking, turning, sitting, phone use, skating, wind, breathing and
facial expressions. Units: the boy is ~100 units tall, origin at the feet,
character faces +x; facing left is a mirror.
"""
import math

from .core import (OUTLINE, catmull_path, clamp, ellipse, hexc, lerp, mix,
                   noise1, rgba)

D2R = math.pi / 180

BASE_POSE = dict(
    turn=0.35,          # -1 profile left .. 0 front .. 1 profile right
    hip_back=0, knee_back=4, hip_front=0, knee_front=4,
    sh_back=4, el_back=8, sh_front=4, el_front=8,
    hand_back="open", hand_front="open",
    bob=0.0, lean=0.0, head_tilt=0.0, nod=0.0,
    look_x=0.0, look_y=0.0, smile=0.15, blink=0.0, mouth_open=0.0,
    brow=0.0, blush=0.0, lid=0.0,
    wind=0.15, phone=0.0, board=False, board_tilt=0.0, sit=0.0,
    breath=0.0, shadow=1.0, alpha=1.0, phone_glow=0.0, tears=0.0,
)


def pose(**kw):
    p = dict(BASE_POSE)
    p.update(kw)
    return p


# ----------------------------------------------------------------- poses

def walk_pose(phase, speed=1.0, **kw):
    """Walk cycle; phase in radians (2*pi per stride pair)."""
    s = math.sin(phase)
    c = math.cos(phase)
    amp = 24 * speed
    p = pose(
        hip_front=amp * s, hip_back=-amp * s,
        knee_front=6 + 34 * speed * max(0.0, -c) ** 1.2 * (1 if s < 0.6 else 0.6),
        knee_back=6 + 34 * speed * max(0.0, c) ** 1.2 * (1 if s > -0.6 else 0.6),
        sh_front=-16 * speed * s, sh_back=16 * speed * s,
        el_front=14 + 10 * speed * max(0, -s), el_back=14 + 10 * speed * max(0, s),
        bob=-1.3 * speed * abs(c) + 0.6, lean=3 * speed,
    )
    p.update(kw)
    return p


def run_pose(phase, **kw):
    s = math.sin(phase)
    c = math.cos(phase)
    p = pose(
        hip_front=40 * s, hip_back=-40 * s,
        knee_front=15 + 75 * max(0.0, -c), knee_back=15 + 75 * max(0.0, c),
        sh_front=-45 * s, sh_back=45 * s, el_front=80, el_back=80,
        bob=-2.8 * abs(c) + 1.0, lean=12, wind=0.8,
    )
    p.update(kw)
    return p


def sit_pose(**kw):
    p = pose(hip_back=84, knee_back=88, hip_front=80, knee_front=84,
             sh_back=10, el_back=40, sh_front=12, el_front=45, sit=1.0, lean=4, shadow=0.0)
    p.update(kw)
    return p


def skate_pose(t, push=0.0, **kw):
    """Riding a skateboard; push in [0,1] blends a kick-push cycle."""
    ph = t * 2.2
    k = max(0.0, math.sin(ph)) * push
    p = pose(turn=0.85, hip_front=16, knee_front=30, hip_back=-14 - 20 * k,
             knee_back=18 + 30 * k, sh_front=-20, el_front=25, sh_back=28,
             el_back=20, bob=1.5 + 0.6 * math.sin(t * 3), lean=6,
             board=True, wind=0.9, smile=0.5)
    p.update(kw)
    return p


def blend(p1, p2, t):
    out = {}
    for k, v in p1.items():
        v2 = p2.get(k, v)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and isinstance(v2, (int, float)):
            out[k] = lerp(v, v2, t)
        else:
            out[k] = v2 if t > 0.5 else v
    return out


def blink_at(t, seed=0):
    """Natural blinking: a ~0.15 s blink every 3-5 s."""
    period = 3.7 + 1.1 * math.sin(seed * 3.1)
    ph = (t + seed * 1.37) % period
    return 1.0 if ph < 0.12 else 0.0


# ----------------------------------------------------------------- base rig

class Character:
    skin = hexc("#f2c39e")
    jeans = hexc("#2b3452")
    shoe = hexc("#f1eee8")
    shoe_acc = hexc("#d8473b")
    sleeve_w = 6.4
    leg_w = 7.4
    hip_y = -44.0
    thigh = 21.0
    shin = 20.0
    upper = 13.5
    fore = 13.0
    torso_len = 25.0
    neck_len = 2.5
    head_r = 10.0
    head_scale = 1.32
    seed = 1

    def __init__(self):
        self.L = None

    def c(self, col, k=1.0):
        out = self.L(col)
        return tuple(clamp(v * k) for v in out)

    # ---- generic shape helpers
    def limb(self, ctx, pts, width, col, outline=1.25):
        ctx.set_line_cap(1)   # round
        ctx.set_line_join(1)
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        rgba(ctx, OUTLINE)
        ctx.set_line_width(width + outline * 2)
        ctx.stroke_preserve()
        rgba(ctx, col)
        ctx.set_line_width(width)
        ctx.stroke()

    def blob(self, ctx, build, col, outline=1.2):
        build(ctx)
        rgba(ctx, OUTLINE)
        ctx.set_line_width(outline * 2)
        ctx.set_line_join(1)
        ctx.stroke_preserve()
        rgba(ctx, col)
        ctx.fill()

    # ---- skeleton
    @staticmethod
    def vec(a_deg, length, fs):
        a = a_deg * D2R
        return (math.sin(a) * length * fs, math.cos(a) * length)

    def leg_points(self, hx, hy, a, k, fs):
        dx, dy = self.vec(a, self.thigh, fs)
        knee = (hx + dx, hy + dy)
        dx2, dy2 = self.vec(a - k, self.shin, fs)
        ankle = (knee[0] + dx2, knee[1] + dy2)
        return knee, ankle

    def arm_points(self, sx, sy, a, e, fs):
        dx, dy = self.vec(a, self.upper, fs)
        elbow = (sx + dx, sy + dy)
        dx2, dy2 = self.vec(a + e, self.fore, fs)
        wrist = (elbow[0] + dx2, elbow[1] + dy2)
        return elbow, wrist

    def draw_shoe(self, ctx, x, y, rot, v, k=1.0):
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(rot)
        ln = lerp(0.55, 1.0, v)
        base = self.c(self.shoe, k)

        def shape(c_):
            c_.move_to(-2.8 * ln, -2.4)
            c_.curve_to(-3.4 * ln, 1.6, -2.0 * ln, 2.6, 0, 2.6)
            c_.line_to(6.2 * ln, 2.6)
            c_.curve_to(8.0 * ln, 2.6, 8.0 * ln, 0.0, 5.8 * ln, -0.6)
            c_.curve_to(3.5 * ln, -1.2, 2.5 * ln, -3.0, 0.5 * ln, -3.2)
            c_.close_path()
        self.blob(ctx, shape, base, 0.9)
        rgba(ctx, self.c(self.shoe_acc, k))
        ctx.rectangle(-3.0 * ln, 1.5, 10.5 * ln, 1.0)
        ctx.fill()
        rgba(ctx, self.c(self.shoe_acc, k), 0.9)
        ctx.set_line_width(0.7)
        ctx.move_to(-0.5 * ln, -1.6)
        ctx.curve_to(1.5 * ln, -0.4, 3.0 * ln, -0.6, 4.5 * ln, 0.6)
        ctx.stroke()
        ctx.restore()

    def draw_leg(self, ctx, hx, hy, a, k, fs, v, shade):
        knee, ankle = self.leg_points(hx, hy, a, k, fs)
        self.limb(ctx, [(hx, hy), knee, ankle], self.leg_w, self.c(self.jeans, shade))
        foot_rot = -(a - k) * 0.45 * D2R if v > 0.3 else 0.0
        self.draw_shoe(ctx, ankle[0], ankle[1] + 0.6, foot_rot, v, shade)
        return ankle

    def draw_arm(self, ctx, sx, sy, a, e, fs, shade, hand, sleeve):
        elbow, wrist = self.arm_points(sx, sy, a, e, fs)
        if hand == "pocket":
            # forearm tucked into the jacket pocket
            wrist = (lerp(elbow[0], wrist[0], 0.55), lerp(elbow[1], wrist[1], 0.55))
            self.limb(ctx, [(sx, sy), elbow, wrist], self.sleeve_w, self.c(sleeve, shade))
            return wrist
        self.limb(ctx, [(sx, sy), elbow, wrist], self.sleeve_w, self.c(sleeve, shade))
        # cuff + hand
        ang = math.atan2(wrist[1] - elbow[1], wrist[0] - elbow[0])
        hx = wrist[0] + math.cos(ang) * 2.2
        hy = wrist[1] + math.sin(ang) * 2.2
        self.blob(ctx, lambda c_: ellipse(c_, hx, hy, 2.5, 2.8), self.c(self.skin, shade), 0.9)
        return (hx, hy)

    def draw_phone(self, ctx, hx, hy, glow, t):
        ctx.save()
        ctx.translate(hx + 0.5, hy - 3.0)
        ctx.rotate(-0.15)
        self.blob(ctx, lambda c_: c_.rectangle(-2.6, -4.6, 5.2, 9.2), (0.08, 0.08, 0.1), 0.6)
        g = 0.55 + 0.45 * glow
        rgba(ctx, (0.55 * g, 0.75 * g, 1.0 * g))
        ctx.rectangle(-2.1, -4.0, 4.2, 8.0)
        ctx.fill()
        ctx.restore()
        # finger over phone
        self.blob(ctx, lambda c_: ellipse(c_, hx - 1.0, hy - 1.2, 1.6, 1.2), self.c(self.skin), 0.7)

    # ---- main entry
    def draw(self, ctx, x, y, scale, p, light, t=0.0):
        self.L = light
        turn = clamp(p["turn"], -1, 1)
        flip = -1 if turn < 0 else 1
        v = abs(turn)
        fs = lerp(0.38, 1.0, v)
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(scale * flip, scale)

        if p["alpha"] < 0.999:
            ctx.push_group()

        if p["shadow"] > 0:
            rgba(ctx, (0, 0, 0), 0.32 * p["shadow"])
            ellipse(ctx, 0, 1.5 if not p["board"] else 6.0, 15 + 4 * v, 3.0)
            ctx.fill()

        if p["board"]:
            self.draw_board(ctx, t, p)

        breath = math.sin(t * 2 * math.pi / 4.0) * 0.45 + p["breath"]
        hip_y = self.hip_y + p["bob"] + (6 if p["sit"] > 0 else 0) * p["sit"] * 0
        if p["board"]:
            hip_y -= 4.2
        hw = lerp(4.6, 0.9, v)

        # head transform (needed for back hair which sits behind everything)
        lean = p["lean"]
        neck_base = (0, hip_y - self.torso_len - breath * 0.3)
        hs = self.head_scale
        head_c = (neck_base[0] + p["nod"] * 1.4, neck_base[1] - self.neck_len - self.head_r * 0.95 * hs + p["nod"] * 1.4)

        def upper_tf():
            ctx.translate(0, hip_y)
            ctx.rotate(lean * D2R)
            ctx.translate(0, -hip_y)

        def head_tf():
            upper_tf()
            ctx.translate(*head_c)
            ctx.rotate((p["head_tilt"] + p["nod"] * 9) * D2R)
            ctx.scale(hs, hs)

        ctx.save()
        head_tf()
        self.draw_back_hair(ctx, p, v, t)
        ctx.restore()

        sh_y = hip_y - self.torso_len + 2.0 - breath * 0.3
        shw = lerp(self.shoulder_w, 2.2, v)

        # back arm
        ctx.save()
        upper_tf()
        self.draw_arm(ctx, -shw, sh_y, p["sh_back"], p["el_back"], fs,
                      0.78 if v > 0.25 else 0.95, p["hand_back"], self.sleeve)
        ctx.restore()

        # legs + pelvis
        bk = 0.8 if v > 0.25 else 0.95
        self.draw_leg(ctx, -hw, hip_y, p["hip_back"], p["knee_back"], fs, v, bk)
        rgba(ctx, self.c(self.jeans))
        self.blob(ctx, lambda c_: c_.rectangle(-hw - 3.6, hip_y - 3, 2 * hw + 7.2, 6.2), self.c(self.jeans), 1.0)
        self.draw_leg(ctx, hw, hip_y, p["hip_front"], p["knee_front"], fs, v, 1.0)

        # torso
        ctx.save()
        upper_tf()
        self.draw_torso(ctx, hip_y, v, breath, p)
        ctx.restore()

        # head
        ctx.save()
        head_tf()
        self.draw_head(ctx, p, v, t)
        ctx.restore()

        # front arm (+ phone)
        ctx.save()
        upper_tf()
        hand = self.draw_arm(ctx, shw, sh_y, p["sh_front"], p["el_front"], fs, 1.0,
                             p["hand_front"], self.sleeve)
        if p["phone"] > 0.5 and hand is not None:
            self.draw_phone(ctx, hand[0], hand[1], p["phone_glow"], t)
        ctx.restore()

        if p["phone_glow"] > 0:
            # screen light on the face
            ctx.save()
            head_tf()
            import cairo
            ctx.set_operator(cairo.OPERATOR_ADD)
            g = cairo.RadialGradient(4, 6, 0, 4, 6, 16)
            g.add_color_stop_rgba(0, 0.35, 0.5, 0.75, 0.45 * p["phone_glow"])
            g.add_color_stop_rgba(1, 0.35, 0.5, 0.75, 0)
            ctx.set_source(g)
            ctx.arc(4, 6, 16, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        if p["alpha"] < 0.999:
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(clamp(p["alpha"]))
        ctx.restore()

    def draw_board(self, ctx, t, p):
        pass

    def draw_back_hair(self, ctx, p, v, t):
        pass

    # ---- face (shared)
    def draw_face(self, ctx, p, v, t, eye_rx, eye_ry, lashes=False, glasses=False):
        dx = v * 4.6
        nod = p["nod"]
        ey = 0.8 + nod * 1.2
        sep = 4.3 * (1 - 0.18 * v)
        eyes = [(dx - sep, ey, 1.0 - 0.0 * v), (dx + sep * (1 - 0.35 * v), ey, 1 - 0.45 * v)]
        blink = max(p["blink"], 0.0)
        lid = clamp(p["lid"] + nod * 0.55)
        # blush
        if p["blush"] > 0:
            for ex, _, sx in eyes:
                rgba(ctx, hexc("#ff7b8a"), 0.35 * p["blush"])
                ellipse(ctx, ex - 0.4 * (1 if ex < dx else -1), ey + 4.0, 2.6 * sx, 1.4)
                ctx.fill()
        for ex, ey_, sx in eyes:
            lx = ex + p["look_x"] * 1.1 * sx
            ly = ey_ + p["look_y"] * 0.9 + nod * 0.6
            if blink > 0.5:
                ctx.set_line_width(0.7)
                rgba(ctx, OUTLINE)
                ctx.move_to(ex - eye_rx * sx * 1.1, ey_ + 0.3)
                ctx.curve_to(ex - 0.5 * sx, ey_ + 1.3, ex + 0.5 * sx, ey_ + 1.3, ex + eye_rx * sx * 1.1, ey_ + 0.3)
                ctx.stroke()
                continue
            ctx.save()
            lid_y = ey_ - eye_ry + lid * eye_ry * 1.25
            ctx.rectangle(ex - 6, lid_y, 12, 12)
            ctx.clip()
            rgba(ctx, hexc("#2a1712"))
            ellipse(ctx, lx, ly, eye_rx * sx, eye_ry)
            ctx.fill()
            rgba(ctx, (1, 1, 1), 0.95)
            ellipse(ctx, lx + 0.45 * sx, ly - eye_ry * 0.42, eye_rx * 0.38 * sx, eye_rx * 0.38)
            ctx.fill()
            rgba(ctx, (1, 1, 1), 0.7)
            ellipse(ctx, lx - 0.5 * sx, ly + eye_ry * 0.4, eye_rx * 0.18 * sx, eye_rx * 0.18)
            ctx.fill()
            ctx.restore()
            if lid > 0.05:
                rgba(ctx, OUTLINE)
                ctx.set_line_width(0.6)
                ctx.move_to(ex - eye_rx * sx * 1.2, lid_y)
                ctx.line_to(ex + eye_rx * sx * 1.2, lid_y)
                ctx.stroke()
            if lashes:
                rgba(ctx, OUTLINE)
                ctx.set_line_width(0.75)
                top = max(lid_y, ey_ - eye_ry) - 0.2
                ctx.move_to(ex - eye_rx * sx * 1.25, top + 0.9)
                ctx.curve_to(ex - 0.6 * sx, top - 0.7, ex + 0.6 * sx, top - 0.7, ex + eye_rx * sx * 1.35, top + 0.4)
                ctx.stroke()
                ctx.move_to(ex + eye_rx * sx * 1.2, top + 0.5)
                ctx.line_to(ex + eye_rx * sx * 1.9, top - 0.6)
                ctx.stroke()
            if p["tears"] > 0:
                rgba(ctx, hexc("#bfe6ff"), 0.85 * p["tears"])
                ellipse(ctx, ex + 0.6, ey_ + eye_ry + 1.0 + p["tears"] * 3.5, 0.55, 0.85)
                ctx.fill()
        if glasses:
            ctx.set_line_width(1.05)
            for i, (ex, ey_, sx) in enumerate(eyes):
                rgba(ctx, (1, 1, 1), 0.10)
                ellipse(ctx, ex, ey_, 4.3 * sx, 3.9)
                ctx.fill_preserve()
                rgba(ctx, hexc("#2a1d1b"))
                ctx.stroke()
                # lens glare
                ctx.save()
                ellipse(ctx, ex, ey_, 4.3 * sx, 3.9)
                ctx.clip()
                if p.get("reflect", 0) > 0:
                    rf = p["reflect"]
                    import cairo as _c
                    g = _c.RadialGradient(ex + 1.2 * sx, ey_ + 1.0, 0, ex + 1.2 * sx, ey_ + 1.0, 4.0)
                    g.add_color_stop_rgba(0, 1.0, 0.7, 0.35, 0.55 * rf)
                    g.add_color_stop_rgba(1, 1.0, 0.5, 0.3, 0.0)
                    ctx.set_source(g)
                    ctx.paint()
                rgba(ctx, (1, 1, 1), 0.28)
                ctx.set_line_width(1.1)
                ctx.move_to(ex - 3.5 * sx, ey_ + 1.0)
                ctx.line_to(ex + 0.5 * sx, ey_ - 3.6)
                ctx.stroke()
                ctx.set_line_width(0.5)
                ctx.move_to(ex - 1.8 * sx, ey_ + 2.6)
                ctx.line_to(ex + 2.2 * sx, ey_ - 1.8)
                ctx.stroke()
                ctx.restore()
            rgba(ctx, hexc("#2a1d1b"))
            (l, r) = eyes
            ctx.move_to(l[0] + 4.3 * l[2], l[1] - 0.6)
            ctx.curve_to(l[0] + 4.3 * l[2] + 1, l[1] - 1.8, r[0] - 4.3 * r[2] - 1, r[1] - 1.8, r[0] - 4.3 * r[2], r[1] - 0.6)
            ctx.stroke()
            ctx.move_to(l[0] - 4.3 * l[2], l[1] - 0.8)
            ctx.line_to(-8.6 + v * 2.5, l[1] - 1.2)
            ctx.stroke()
        # brows
        bro = p["brow"]
        rgba(ctx, self.brow_col)
        ctx.set_line_width(1.0 if glasses else 0.8)
        ctx.set_line_cap(1)
        for i, (ex, ey_, sx) in enumerate(eyes):
            inner = 1 if i == 0 else -1
            by = ey_ - (5.6 if glasses else 4.0) - max(0, bro) * 0.5
            ix = ex + inner * 2.2 * sx
            ox = ex - inner * 2.4 * sx
            ctx.move_to(ox, by + 0.3 + bro * 0.2)
            ctx.line_to(ix, by + 0.2 - max(0, -bro) * 1.7 - max(0, bro) * 0.3)
            ctx.stroke()
        # nose
        rgba(ctx, self.c(self.skin, 0.72))
        ctx.set_line_width(0.75)
        nx = dx * 1.12 + 0.8
        ctx.move_to(nx - 0.3, 3.4 + nod)
        ctx.curve_to(nx + 1.3, 4.6 + nod, nx + 0.8, 5.4 + nod, nx - 0.5, 5.3 + nod)
        ctx.stroke()
        # mouth
        mx = dx * 0.95 + 0.4
        my = 7.6 + nod * 0.8
        sm = p["smile"]
        mw = 2.4 + 0.6 * max(0, sm)
        if p["mouth_open"] > 0.05:
            o = p["mouth_open"]
            rgba(ctx, hexc("#5a1f24"))
            ctx.move_to(mx - mw, my - 0.2)
            ctx.curve_to(mx - mw * 0.5, my + sm * 1.0 + o * 2.4, mx + mw * 0.5, my + sm * 1.0 + o * 2.4, mx + mw, my - 0.2)
            ctx.curve_to(mx + mw * 0.4, my + 0.4, mx - mw * 0.4, my + 0.4, mx - mw, my - 0.2)
            ctx.fill()
            rgba(ctx, (1, 1, 1), 0.9)
            ctx.rectangle(mx - mw * 0.55, my - 0.05, mw * 1.1, 0.5)
            ctx.fill()
        rgba(ctx, self.mouth_col)
        ctx.set_line_width(0.8)
        ctx.move_to(mx - mw, my - sm * 0.6)
        ctx.curve_to(mx - mw * 0.4, my + sm * 1.3, mx + mw * 0.4, my + sm * 1.3, mx + mw, my - sm * 0.6)
        ctx.stroke()


# ----------------------------------------------------------------- the boy

class Boy(Character):
    skin = hexc("#f1c19b")
    jacket = hexc("#17a2b4")
    jacket_dark = hexc("#0f6f86")
    hoodie = hexc("#2e5aa8")
    sleeve = hexc("#17a2b4")
    jeans = hexc("#27304d")
    hair = hexc("#8e4526")
    hair_hi = hexc("#b9643a")
    brow_col = hexc("#5a2a18")
    mouth_col = hexc("#6b2a22")
    shoe_acc = hexc("#d8473b")
    shoulder_w = 11.5
    seed = 3
    glasses = True

    def draw_torso(self, ctx, hip_y, v, breath, p):
        top = hip_y - self.torso_len
        tw = lerp(12.6, 8.2, v) + breath * 0.15
        off = v * 1.2
        # hood bunched behind the neck
        self.blob(ctx, lambda c_: ellipse(c_, -v * 4.5, top - 0.5, 7.2, 4.0), self.c(self.hoodie, 0.85), 1.0)
        # neck
        self.blob(ctx, lambda c_: c_.rectangle(-2.6 + v * 1.2, top - 5.5, 5.2, 7), self.c(self.skin, 0.88), 0.9)

        def body(c_):
            c_.move_to(-tw + off, top + 3.5)
            c_.curve_to(-tw + off, top - 0.5, -tw + 3 + off, top - 1.6, -3.5 + off, top - 1.6)
            c_.line_to(3.5 + off, top - 1.6)
            c_.curve_to(tw - 3 + off, top - 1.6, tw + off, top - 0.5, tw + off, top + 3.5)
            c_.line_to(tw - 0.6 + off * 0.5, hip_y + 4.5)
            c_.curve_to(4, hip_y + 5.6, -4, hip_y + 5.6, -tw + 0.6 + off * 0.5, hip_y + 4.5)
            c_.close_path()
        self.blob(ctx, body, self.c(self.jacket), 1.25)
        # cel shade on the back side
        ctx.save()
        body(ctx)
        ctx.clip()
        rgba(ctx, self.c(self.jacket_dark), 0.55)
        ctx.rectangle(-tw - 2 + off, top - 3, tw * 0.55, self.torso_len + 12)
        ctx.fill()
        # hoodie visible in the open jacket
        cx = off + v * 4.0
        hwid = lerp(4.4, 2.6, v)
        rgba(ctx, self.c(self.hoodie))
        ctx.move_to(cx - hwid, top - 1.6)
        ctx.line_to(cx + hwid, top - 1.6)
        ctx.line_to(cx + hwid * 0.8, hip_y + 6)
        ctx.line_to(cx - hwid * 0.8, hip_y + 6)
        ctx.fill()
        rgba(ctx, OUTLINE, 0.8)
        ctx.set_line_width(0.7)
        for sgn in (-1, 1):
            ctx.move_to(cx + sgn * hwid, top - 1.6)
            ctx.line_to(cx + sgn * hwid * 0.8, hip_y + 6)
        ctx.stroke()
        # drawstrings
        rgba(ctx, self.c(hexc("#e9eef5")))
        ctx.set_line_width(0.6)
        for sgn in (-1, 1):
            ctx.move_to(cx + sgn * 1.4, top - 1.0)
            ctx.line_to(cx + sgn * 1.6, top + 6.5 + sgn * 0.4)
        ctx.stroke()
        # hoodie pocket hint
        rgba(ctx, self.c(self.hoodie, 0.78))
        ctx.rectangle(cx - hwid * 0.8, hip_y - 6, hwid * 1.6, 4)
        ctx.fill()
        # jacket pocket line + hem band
        rgba(ctx, self.c(self.jacket_dark), 0.9)
        ctx.set_line_width(0.7)
        ctx.move_to(tw * 0.35 + off + v * 2, hip_y - 6)
        ctx.line_to(tw * 0.75 + off, hip_y - 1)
        ctx.stroke()
        ctx.rectangle(-tw - 2, hip_y + 2.6, 2 * tw + 6, 3)
        ctx.fill()
        ctx.restore()

    def draw_head(self, ctx, p, v, t):
        wind = p["wind"]
        dx = v * 4.6
        # back hair volume
        self.blob(ctx, lambda c_: ellipse(c_, -v * 1.8, -2.4, 10.2, 10.0), self.c(self.hair, 0.8), 1.1)
        # ears + head
        ear_x = -8.6 + v * 2.6

        def head(c_):
            ellipse(c_, -v * 0.6, -1.0, 9.4, 9.6)
            c_.new_sub_path()
            c_.move_to(8.8 + v * 0.8, 0.5)
            c_.curve_to(8.5 + v * 1.4, 7.0, 4.5 + dx * 0.6, 11.4, 0.5 + dx * 0.55, 11.4)
            c_.curve_to(-3.0 + dx * 0.5, 11.4, -8.0, 7.5, -8.6 - v * 0.2, 0.5)
            c_.close_path()
            c_.new_sub_path()
            ellipse(c_, ear_x, 1.8, 2.1, 3.0)
            if v < 0.45:
                c_.new_sub_path()
                ellipse(c_, 8.7, 1.8, 2.0, 3.0)
        self.blob(ctx, head, self.c(self.skin), 1.15)
        rgba(ctx, self.c(self.skin, 0.78))
        ellipse(ctx, ear_x + 0.3, 1.9, 0.9, 1.6)
        ctx.fill()
        self.draw_face(ctx, p, v, t, 1.25, 1.65, lashes=False, glasses=self.glasses)
        # messy hair: spiky crown + fringe
        pts = []
        n = 13
        for i in range(n + 1):
            th = (168 + (372 - 168) * i / n) * D2R
            spike = i % 2 == 1
            r = (12.6 + 1.6 * math.sin(i * 2.7 + 1)) if spike else 10.1
            sway = (noise1(t * 1.6 + i, self.seed) * 0.6 - wind * 1.4) * (1 if spike else 0.3)
            x = math.cos(th) * r - v * 1.0 + sway
            y = math.sin(th) * r - 1.8
            pts.append((x, y))
        # fringe going back from right temple to left temple
        fr = [(8.7 + v * 0.3, -1.0), (6.4 + dx * 0.4, -3.2), (5.6 + dx * 0.6, -1.8),
              (3.4 + dx * 0.55, -5.0), (1.6 + dx * 0.5, -2.2), (-0.6 + dx * 0.4, -5.4),
              (-2.6 + dx * 0.3, -2.8), (-4.4 + dx * 0.2, -5.6), (-6.8, -3.2), (-9.0 - v * 0.4, -0.6)]
        fr = [(x - wind * 0.4 * noise1(t * 2 + x, 2), y) for x, y in fr]
        allp = pts + fr

        def hair(c_):
            c_.move_to(*allp[0])
            for q in allp[1:]:
                c_.line_to(*q)
            c_.close_path()
        ctx.set_line_join(1)
        self.blob(ctx, hair, self.c(self.hair), 1.15)
        # highlight strands
        rgba(ctx, self.c(self.hair_hi), 0.9)
        ctx.set_line_width(0.9)
        for a0, a1, r in ((205, 240, 8.5), (250, 285, 9.0), (295, 330, 8.4)):
            ctx.arc(-v * 1.0, -1.8, r, a0 * D2R, a1 * D2R)
            ctx.new_sub_path()
        ctx.stroke()


# ----------------------------------------------------------------- the girl

class Girl(Character):
    skin = hexc("#f6cfb0")
    jacket = hexc("#2a2b38")
    jacket_dark = hexc("#18181f")
    sleeve = hexc("#2a2b38")
    top = hexc("#ece3d3")
    jeans = hexc("#384a72")
    hair = hexc("#e0552b")
    hair_dark = hexc("#b23c1f")
    hair_hi = hexc("#f79a5a")
    cap = hexc("#2c63c0")
    cap_dark = hexc("#1d4590")
    deck = hexc("#38b24a")
    deck_dark = hexc("#237a31")
    brow_col = hexc("#9a3d1d")
    mouth_col = hexc("#b5404a")
    shoe_acc = hexc("#38b24a")
    shoulder_w = 10.0
    leg_w = 6.6
    sleeve_w = 5.8
    thigh = 21.5
    shin = 20.5
    hip_y = -45.0
    torso_len = 23.0
    seed = 7

    def draw_board(self, ctx, t, p):
        ctx.save()
        ctx.translate(0, 2.2)
        ctx.rotate(p["board_tilt"] * D2R)

        def deck(c_):
            c_.move_to(-14, -0.4)
            c_.curve_to(-16.5, -0.6, -17, -2.6, -16, -3.0)
            c_.line_to(-14, -1.6)
            c_.line_to(14, -1.6)
            c_.line_to(16, -3.0)
            c_.curve_to(17, -2.6, 16.5, -0.6, 14, -0.4)
            c_.close_path()
        self.blob(ctx, deck, self.c(self.deck), 1.0)
        rgba(ctx, self.c(self.deck_dark))
        ctx.rectangle(-14, -1.0, 28, 0.6)
        ctx.fill()
        for wx in (-9.5, 9.5):
            rgba(ctx, self.c(hexc("#9aa0a8")))
            ctx.rectangle(wx - 1.6, -0.4, 3.2, 1.2)
            ctx.fill()
            self.blob(ctx, lambda c_: ellipse(c_, wx, 2.0, 1.9, 1.9), self.c(hexc("#f2d23c")), 0.8)
            rgba(ctx, OUTLINE, 0.6)
            ctx.set_line_width(0.4)
            a = t * 18
            ctx.move_to(wx + math.cos(a) * 1.3, 2.0 + math.sin(a) * 1.3)
            ctx.line_to(wx - math.cos(a) * 1.3, 2.0 - math.sin(a) * 1.3)
            ctx.stroke()
        ctx.restore()

    def hair_points(self, p, v, t):
        wind = p["wind"]
        back = -v * 3.2
        pts = []
        # left (back) contour, top to bottom, then bottom, then right side up
        base = [(-9.6, -6), (-10.8, 2), (-11.6, 10), (-12.4, 19), (-12.0, 27),
                (-9.0, 33), (-4.0, 35.5), (1.0, 34.0), (6.0, 30.0), (9.6, 22),
                (10.8, 12), (10.8, 2), (9.8, -6), (0, -11)]
        for i, (x, y) in enumerate(base):
            d = clamp((y + 4) / 38)
            sway = noise1(t * 1.9 + i * 0.6, self.seed) * (0.6 + 2.2 * wind) * d
            x2 = x + back * (0.5 + d) - wind * 9 * d * d + sway
            y2 = y - wind * 3.5 * d * d + noise1(t * 2.3 + i, 4) * 0.8 * wind * d
            pts.append((x2, y2))
        return pts

    def draw_back_hair(self, ctx, p, v, t):
        pts = self.hair_points(p, v, t)
        self.blob(ctx, lambda c_: catmull_path(c_, pts), self.c(self.hair_dark), 1.2)
        # strand lines
        rgba(ctx, self.c(self.hair), 0.9)
        ctx.set_line_width(1.1)
        for k in range(5):
            f = (k + 1) / 6
            x0 = lerp(pts[1][0], pts[10][0], f)
            ctx.move_to(x0, 0)
            ctx.curve_to(x0 - 1, 12, lerp(pts[4][0], pts[8][0], f), 20,
                         lerp(pts[5][0], pts[7][0], f), 30)
        ctx.stroke()

    def draw_torso(self, ctx, hip_y, v, breath, p):
        top = hip_y - self.torso_len
        tw = lerp(10.4, 7.0, v) + breath * 0.12
        off = v * 1.0
        self.blob(ctx, lambda c_: c_.rectangle(-2.2 + v * 1.2, top - 5.5, 4.4, 7), self.c(self.skin, 0.88), 0.9)

        def body(c_):
            c_.move_to(-tw + off, top + 3.0)
            c_.curve_to(-tw + off, top - 0.6, -tw + 3 + off, top - 1.4, -3 + off, top - 1.4)
            c_.line_to(3 + off, top - 1.4)
            c_.curve_to(tw - 3 + off, top - 1.4, tw + off, top - 0.6, tw + off, top + 3.0)
            c_.curve_to(tw - 1.6 + off, top + 12, tw - 1.0, hip_y - 2, tw + 0.2, hip_y + 3.0)
            c_.curve_to(4, hip_y + 4.2, -4, hip_y + 4.2, -tw - 0.2, hip_y + 3.0)
            c_.curve_to(-tw + 1.0, hip_y - 2, -tw + 1.6 + off, top + 12, -tw + off, top + 3.0)
            c_.close_path()
        self.blob(ctx, body, self.c(self.jacket), 1.2)
        ctx.save()
        body(ctx)
        ctx.clip()
        rgba(ctx, self.c(self.jacket_dark), 0.7)
        ctx.rectangle(-tw - 2 + off, top - 3, tw * 0.5, self.torso_len + 10)
        ctx.fill()
        cx = off + v * 3.2
        wd = lerp(3.4, 2.0, v)
        rgba(ctx, self.c(self.top))
        ctx.move_to(cx - wd, top - 1.4)
        ctx.line_to(cx + wd, top - 1.4)
        ctx.line_to(cx + wd * 0.7, hip_y + 5)
        ctx.line_to(cx - wd * 0.7, hip_y + 5)
        ctx.fill()
        rgba(ctx, OUTLINE, 0.9)
        ctx.set_line_width(0.6)
        for sgn in (-1, 1):
            ctx.move_to(cx + sgn * wd, top - 1.4)
            ctx.line_to(cx + sgn * wd * 0.7, hip_y + 5)
        ctx.stroke()
        # collar
        rgba(ctx, self.c(self.jacket, 1.25))
        for sgn in (-1, 1):
            ctx.move_to(cx + sgn * wd, top - 1.4)
            ctx.line_to(cx + sgn * (wd + 3.2), top + 1.2)
            ctx.line_to(cx + sgn * (wd + 0.4), top + 6.5)
            ctx.close_path()
            ctx.fill()
        ctx.restore()

    def draw_head(self, ctx, p, v, t):
        dx = v * 4.4
        ear_x = -8.2 + v * 2.6

        def head(c_):
            ellipse(c_, -v * 0.5, -1.2, 9.0, 9.4)
            c_.new_sub_path()
            c_.move_to(8.4 + v * 0.8, 0.4)
            c_.curve_to(8.2 + v * 1.4, 6.6, 4.2 + dx * 0.6, 10.6, 0.5 + dx * 0.55, 10.6)
            c_.curve_to(-2.8 + dx * 0.5, 10.6, -7.6, 7.0, -8.3, 0.4)
            c_.close_path()
            c_.new_sub_path()
            ellipse(c_, ear_x, 2.0, 1.8, 2.6)
        self.blob(ctx, head, self.c(self.skin), 1.1)
        # freckles
        rgba(ctx, hexc("#d9875d"), 0.55)
        for fx, fy in ((-1.2, 4.3), (-0.2, 4.9), (-2.1, 4.9), (1.0 + dx * 0.9, 4.4), (2.0 + dx * 0.9, 4.9)):
            ctx.arc(fx + dx * 0.5, fy, 0.28, 0, 6.3)
            ctx.fill()
        self.draw_face(ctx, p, v, t, 1.5, 2.15, lashes=True, glasses=False)
        # front locks + fringe under the cap
        wind = p["wind"]
        sw = noise1(t * 2.1, 9) * 0.5 * (0.5 + wind)
        for side in (-1, 1):
            if side == 1 and v > 0.7:
                continue
            bx = side * (8.6 - (v * 1.5 if side == 1 else -v * 0.8))
            lock = [(bx - side * 0.5, -6.5), (bx + side * 1.4, 2), (bx + side * 1.2 - wind * 2 + sw, 10),
                    (bx + side * 0.2 - wind * 3.5 + sw, 17), (bx - side * 1.6 - wind * 3 + sw, 15),
                    (bx - side * 1.6, 6), (bx - side * 2.6, -2)]
            self.blob(ctx, lambda c_: catmull_path(c_, lock), self.c(self.hair), 0.9)
        fringe = [(-8.6, -4.5), (-6.0 + dx * 0.3, -1.5), (-3.0 + dx * 0.5, -4.4),
                  (0.5 + dx * 0.6, -2.0 + 0.2 * sw), (3.6 + dx * 0.6, -4.3), (7.0 + dx * 0.4, -1.8),
                  (9.0 + v * 0.4, -4.6), (0, -8.5)]
        self.blob(ctx, lambda c_: catmull_path(c_, fringe, tension=0.35), self.c(self.hair), 1.0)
        rgba(ctx, self.c(self.hair_hi), 0.8)
        ctx.set_line_width(0.6)
        ctx.move_to(-5 + dx * 0.3, -5.5)
        ctx.curve_to(-4 + dx * 0.3, -4, -3.5 + dx * 0.4, -3.5, -3 + dx * 0.5, -3.2)
        ctx.stroke()
        # cap: crown, band, brim, button
        cx = -v * 0.6

        def crown(c_):
            c_.move_to(cx - 9.8, -4.4)
            c_.curve_to(cx - 10.4, -15.5, cx + 10.4, -15.5, cx + 9.8, -4.4)
            c_.curve_to(cx + 4, -5.4, cx - 4, -5.4, cx - 9.8, -4.4)
            c_.close_path()
        self.blob(ctx, crown, self.c(self.cap), 1.15)
        ctx.save()
        crown(ctx)
        ctx.clip()
        rgba(ctx, self.c(self.cap_dark), 0.6)
        ctx.rectangle(cx - 12, -16, 7.0 - v * 3, 14)
        ctx.fill()
        rgba(ctx, self.c(self.cap_dark))
        ctx.set_line_width(0.5)
        ctx.move_to(cx + dx * 0.3, -13.6)
        ctx.curve_to(cx + dx * 0.4 - 1, -10, cx + dx * 0.5, -7, cx + dx * 0.5, -5.2)
        ctx.stroke()
        ctx.restore()
        self.blob(ctx, lambda c_: ellipse(c_, cx, -13.7, 1.0, 0.6), self.c(self.cap_dark), 0.6)
        bx = lerp(0.6, 8.2, v) + dx * 0.15
        brx = lerp(9.6, 6.4, v)
        bry = lerp(2.5, 1.3, v)
        self.blob(ctx, lambda c_: ellipse(c_, bx, -4.2, brx, bry, math.pi * 0.0, math.pi * 1.0), self.c(self.cap_dark), 1.0)
        self.blob(ctx, lambda c_: ellipse(c_, bx, -4.5, brx, bry * 0.8), self.c(self.cap), 1.0)


class Friend(Boy):
    """Background friends: same rig, different outfits, no glasses."""
    glasses = False

    def __init__(self, jacket, hoodie, hair, jeans="#2a2a36", seed=5):
        super().__init__()
        self.jacket = hexc(jacket)
        self.sleeve = hexc(jacket)
        self.jacket_dark = mix(hexc(jacket), (0, 0, 0), 0.35)
        self.hoodie = hexc(hoodie)
        self.hair = hexc(hair)
        self.hair_hi = mix(hexc(hair), (1, 1, 1), 0.25)
        self.jeans = hexc(jeans)
        self.seed = seed
