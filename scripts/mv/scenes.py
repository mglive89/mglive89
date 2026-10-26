"""Scene library + music-synced timeline for WARUM DU?

Every scene is a function scene(F, lt, d) drawing frame content for local
time lt in a scene of duration d. F is the Frame context (camera, canvas,
audio features, grade). Timings come from build/analysis.json (see
timeline()), snapped to detected beats.
"""
import bisect
import math

import cairo

from . import env
from .chars import (Boy, Friend, Girl, blend, blink_at, pose, run_pose, sit_pose,
                    skate_pose, walk_pose)
from .core import (DAWN, NIGHT, RAIN, ROOM, WARM, Lighting, clamp, ease_in,
                   ease_io, ease_out, ellipse, hexc, lerp, mix, noise1, pulse,
                   radial_glow, rgba, seg, smooth, text_center, vgrad)
from .fx import (Bokeh, Particles, Rain, blur_surface, dissolve_particles,
                 light_leak)
from .props import holding_hand, phone_ui, reaching_arm, title

BOY = Boy()
GIRL = Girl()
FRIENDS = [Friend("#c0392b", "#e6e6e6", "#2b1a12", seed=11),
           Friend("#3a7d44", "#222222", "#d9b36a", seed=12),
           Friend("#6b4fa0", "#1f2a44", "#1a1a1a", seed=13)]
CITY = env.City(base_y=820)
FLY = env.FlyCity()
RAIN_FX = Rain(1100)
BOKEH = Bokeh(70)
BOKEH_WARM = Bokeh(55, seed=8, cols=("#ffcf6a", "#ff9a5c", "#fff0c0", "#ff7a5a"))
DUST = Particles(140)
EMBERS = Particles(90, seed=17)

HAND_L = Lighting((0.92, 0.86, 0.9), hexc("#6a7aff"), 0.04)
GROUND = 985          # feet line on the sidewalk
BS = 5.4              # boy scale in medium shots
GS = 5.3              # girl scale


def head_y(scale, ground=None):
    return (GROUND if ground is None else ground) - 84 * scale

G_NIGHT = dict(tint=(0.95, 0.97, 1.08), lift=(0.02, 0.02, 0.06), sat=1.12, bloom=0.55,
               vignette=0.5, grain=0.05)
G_RAIN = dict(tint=(0.88, 0.95, 1.08), lift=(0.02, 0.03, 0.06), sat=0.92, bloom=0.5,
              vignette=0.55, grain=0.06)
G_WARM = dict(tint=(1.08, 1.0, 0.86), lift=(0.06, 0.03, 0.0), sat=1.05, bloom=0.75,
              bloom_thr=140, vignette=0.42, grain=0.07)
G_DUSK = dict(tint=(1.04, 0.96, 0.98), lift=(0.04, 0.02, 0.05), sat=1.1, bloom=0.7,
              vignette=0.45, grain=0.06)
G_DAWN = dict(tint=(1.05, 0.99, 0.96), lift=(0.04, 0.03, 0.05), sat=1.0, bloom=0.6,
              vignette=0.4, grain=0.05)
G_ROOM = dict(tint=(0.85, 0.92, 1.15), lift=(0.01, 0.02, 0.06), sat=0.9, bloom=0.6,
              vignette=0.62, grain=0.07)


# ====================================================================== Frame

class Frame:
    def __init__(self, sw, sh, A):
        self.sw, self.sh = sw, sh
        self.vertical = sh > sw
        self.base = sh / 1080
        self.ts = min(sw / 1920, sh / 1080)   # screen-space text scale
        self.surf = cairo.ImageSurface(cairo.FORMAT_RGB24, sw, sh)
        self.ctx = cairo.Context(self.surf)
        self.A = A
        self.beats = A["beats"]
        self.t = 0.0
        self.g = dict(G_NIGHT)
        self.shake = (0.0, 0.0)
        self.x0, self.x1 = 0, 1920

    def begin(self, t, idx):
        self.t = t
        self.idx = idx
        self.ctx.identity_matrix()
        self.ctx.reset_clip()
        self.ctx.set_operator(cairo.OPERATOR_SOURCE)
        self.ctx.set_source_rgb(0, 0, 0)
        self.ctx.paint()
        self.ctx.set_operator(cairo.OPERATOR_OVER)
        self.g = dict(G_NIGHT)
        self.shake = (0.0, 0.0)

    # audio features
    def beat(self, t=None, decay=7.0):
        t = self.t if t is None else t
        i = bisect.bisect_right(self.beats, t) - 1
        if i < 0:
            return 0.0
        return math.exp(-(t - self.beats[i]) * decay)

    def energy(self, t=None):
        t = self.t if t is None else t
        e = self.A["energy_smooth"]
        return e[min(len(e) - 1, max(0, int(t * 30)))]

    def cam(self, x=960, y=540, zoom=1.0, rot=0.0, focus=None, vzoom=1.0, vy=None):
        ctx = self.ctx
        ctx.identity_matrix()
        cx = x
        if self.vertical:
            cx = focus if focus is not None else x
            zoom = zoom * vzoom
            y = vy if vy is not None else y
        sc = self.base * zoom
        ctx.translate(self.sw / 2 + self.shake[0] * self.base, self.sh / 2 + self.shake[1] * self.base)
        ctx.rotate(rot)
        ctx.scale(sc, sc)
        ctx.translate(-cx, -y)
        hw = self.sw / (2 * sc) * (1.0 + abs(rot) * 2)
        self.x0, self.x1 = cx - hw - 60, cx + hw + 60
        self.y0 = y - self.sh / (2 * sc) - 60
        self.y1 = y + self.sh / (2 * sc) + 60
        self.zoom = zoom

    def screen(self):
        self.ctx.identity_matrix()

    def blur(self, sigma):
        blur_surface(self.surf, sigma * self.base)

    def grade(self, base, **kw):
        g = dict(base)
        g.update(kw)
        self.g = g

    def do_shake(self, amount, freq=11.0):
        t = self.t
        self.shake = (noise1(t * freq, 1) * amount, noise1(t * freq, 2) * amount)


# ====================================================================== helpers

def city_street(F, cam_x, p, t, wet=1.0, lamps=True, lamp_lit=1.0, reflect=True, lit=1.0,
                lamp_period=620, lamp_offset=0):
    ctx = F.ctx
    gy = CITY.base_y
    CITY.draw(ctx, cam_x, F.x0, F.x1, p, t, lit=lit)
    env.street(ctx, F.x0, F.x1, gy, p, t, wet=wet, lamps=False)
    if reflect and wet > 0:
        ctx.save()
        ctx.rectangle(F.x0, gy, F.x1 - F.x0, 900)
        ctx.clip()
        ctx.push_group()
        ctx.translate(0, 2 * gy)
        ctx.scale(1, -0.75)
        ctx.translate(0, gy * 0.333)
        CITY.near.draw(ctx, cam_x, F.x0, F.x1, p, "near", t, lit)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(0.2 * wet)
        ctx.restore()
    if lamps:
        k0 = math.floor((F.x0 - lamp_offset) / lamp_period) - 1
        k1 = math.floor((F.x1 - lamp_offset) / lamp_period) + 1
        for k in range(k0, k1 + 1):
            env.street_lamp(ctx, k * lamp_period + lamp_offset, gy + 14, t, wet, lamp_lit, seed=k)


def rain(F, t, intensity, speed=1.0, frozen=False, rt=None, color=(0.75, 0.82, 1.0)):
    F.screen()
    RAIN_FX.draw(F.ctx, F.sw, F.sh, t if rt is None else rt, intensity, speed=speed, frozen=frozen,
                 color=color)


def walking(phase, **kw):
    return walk_pose(phase, **kw)


def sad_face(t, seed=0, **kw):
    p = dict(smile=-0.35, brow=-0.8, lid=0.35, nod=0.25, blink=blink_at(t, seed))
    p.update(kw)
    return p


def happy_face(t, seed=0, **kw):
    p = dict(smile=0.75, brow=0.6, blush=0.4, blink=blink_at(t, seed))
    p.update(kw)
    return p


def warm_sky_sun(F, x, y, a=1.0):
    env.sun(F.ctx, x, y, 70, a)


def string_lights(ctx, x0, x1, y, sag, t, n=24, a=1.0):
    ctx.set_line_width(2)
    rgba(ctx, (0.05, 0.04, 0.06), 0.9)
    ctx.move_to(x0, y)
    ctx.curve_to(lerp(x0, x1, 0.33), y + sag * 1.33, lerp(x0, x1, 0.66), y + sag * 1.33, x1, y)
    ctx.stroke()
    for i in range(n + 1):
        f = i / n
        bx = lerp(x0, x1, f)
        by = y + sag * 4 * f * (1 - f)
        tw = 0.75 + 0.25 * math.sin(t * 2.3 + i * 1.7)
        col = (hexc("#ffcf7a"), hexc("#ff9a6a"), hexc("#fff0c0"))[i % 3]
        radial_glow(ctx, bx, by + 8, 46, col, 0.45 * tw * a)
        rgba(ctx, col, a)
        ellipse(ctx, bx, by + 8, 5, 7)
        ctx.fill()


# ====================================================================== scenes

def s_fly(F, lt, d):
    """INTRO - camera glides through the sleepless city."""
    t = F.t
    F.screen()
    sway = math.sin(lt * 0.5) * 0.6
    env.FlyCity.draw(FLY, F.ctx, 4 + lt * 10.5 + ease_in(seg(lt, d - 2.0, d)) * 8, t,
                     env.pal("night"), F.sw, F.sh, cam_h=3.4 - lt * 0.12, sway=sway)
    rain(F, t, 0.35)
    a = pulse(lt, 1.0, d - 0.6) ** 0.5
    ctx = F.ctx
    text_center(ctx, "M A R C O   G A L L O", F.sw / 2, F.sh * 0.43, 52 * F.ts * (1.4 if F.vertical else 1), (1, 1, 1), 0.85 * a,
                font="Inter", weight=cairo.FONT_WEIGHT_NORMAL)
    text_center(ctx, "präsentiert", F.sw / 2, F.sh * 0.43 + 70 * F.ts * (1.4 if F.vertical else 1), 30 * F.ts * (1.4 if F.vertical else 1), (0.85, 0.88, 1),
                0.6 * a, font="Inter", weight=cairo.FONT_WEIGHT_NORMAL)
    F.grade(G_NIGHT, fade=smooth(seg(lt, 0, 1.6)), bloom=0.7)


def s_walk_alone(F, lt, d):
    """The boy walks alone, hands in pockets."""
    t = F.t
    bx = 300 + lt * 125
    F.cam(bx + 180, 560, 1.0 + lt * 0.006, focus=bx + 20, vzoom=0.95)
    city_street(F, bx + 180, env.pal("night"), t, wet=0.8)
    ph = bx / (BS * 30) * math.pi
    p = walking(ph, turn=0.92, hand_front="pocket", hand_back="pocket", sh_front=6, el_front=40,
                sh_back=4, el_back=40, **sad_face(t, 1, nod=0.35, look_y=0.5))
    BOY.draw(F.ctx, bx, GROUND, BS, p, NIGHT, t)
    rain(F, t, 0.4)
    F.grade(G_NIGHT)


def s_phone_check(F, lt, d):
    """He stops and checks his phone: no new messages."""
    t = F.t
    bx = 1280
    split = 1.7
    if lt < split:
        z = 1.7 + lt * 0.05
        F.cam(bx + 40, 640, z, focus=bx + 10)
        city_street(F, bx, env.pal("night"), t, wet=0.8)
        F.blur(5)
        k = smooth(seg(lt, 0.0, 1.1))
        p0 = pose(turn=0.5, hand_front="pocket", sh_front=6, el_front=40, hand_back="pocket", sh_back=4,
                  el_back=40)
        p1 = pose(turn=0.4, sh_front=12, el_front=118, phone=1, phone_glow=1, hand_back="pocket",
                  sh_back=4, el_back=40)
        p = blend(p0, p1, k)
        p.update(sad_face(t, 2, nod=0.5 * k + 0.2, look_y=0.8))
        BOY.draw(F.ctx, bx, GROUND, BS, p, NIGHT, t)
        rain(F, t, 0.35)
        F.grade(G_NIGHT)
    else:
        lt2 = lt - split
        F.cam(960, 560, 1.15, focus=960)
        city_street(F, 900 + lt2 * 10, env.pal("night"), t, wet=0.8)
        F.blur(22)
        F.screen()
        BOKEH.draw(F.ctx, F.sw, F.sh, t, 0.7)
        ph_h = F.sh * (0.82 if not F.vertical else 0.55) * (1 + lt2 * 0.02)
        cx, cy = F.sw / 2, F.sh * 0.53
        holding_hand(F.ctx, cx, cy, ph_h, BOY.skin, BOY.sleeve, HAND_L, "back")
        phone_ui(F.ctx, cx, cy, ph_h, t, mode="lock", clock="23:47",
                 lock_text="Keine neuen Nachrichten")
        holding_hand(F.ctx, cx, cy, ph_h, BOY.skin, BOY.sleeve, HAND_L, "front")
        rain(F, t, 0.25)
        F.grade(G_NIGHT, bloom=0.5)


def s_memory_arrive(F, lt, d):
    """MEMORY - first meeting: she arrives on her skateboard."""
    t = F.t
    p_w = env.pal("warm")
    F.cam(960 + lt * 12, 560, 1.0 + lt * 0.015, focus=lerp(1500, 1000, smooth(seg(lt, 0, 3.6))), vzoom=0.9)
    CITY.draw(F.ctx, 960 + lt * 12, F.x0, F.x1, p_w, t)
    F.ctx.save()
    warm_sky_sun(F, 1450, 470)
    F.ctx.restore()
    CITY.near.draw(F.ctx, 960 + lt * 12, F.x0, F.x1, p_w, "near", t, 0.6)
    env.street(F.ctx, F.x0, F.x1, CITY.base_y, p_w, t, wet=0.3, lamps=False)
    arrive = ease_out(seg(lt, 0.0, 3.4))
    gx = lerp(2500, 1180, arrive)
    on_board = lt < 3.6
    if on_board:
        gp = skate_pose(t, push=0.6 * (1 - arrive), turn=-0.85, wind=0.9 * (1 - arrive) + 0.2,
                        **happy_face(t, 4, smile=0.5, blush=0.0))
    else:
        k = smooth(seg(lt, 3.6, 4.4))
        gp = blend(skate_pose(t, turn=-0.85), pose(turn=-0.5, sh_front=10, el_front=30), k)
        gp.update(happy_face(t, 4, smile=0.7, look_x=-0.3, blush=0.3 * k))
        gp["board"] = False
    if not on_board:
        # board resting next to her
        F.ctx.save()
        F.ctx.translate(gx + 110, GROUND - 6)
        F.ctx.scale(5.2, 5.2)
        GIRL.L = WARM
        GIRL.draw_board(F.ctx, 0, dict(board_tilt=0))
        F.ctx.restore()
    GIRL.draw(F.ctx, gx, GROUND, GS, gp, WARM, t)
    turn_k = smooth(seg(lt, 1.6, 3.0))
    bp = pose(turn=lerp(-0.2, 0.6, turn_k), hand_back="pocket", sh_back=4, el_back=40,
              **happy_face(t, 5, smile=lerp(0.1, 0.55, smooth(seg(lt, 3.4, 4.6))), look_x=turn_k * 0.6,
                           blush=0.3 * smooth(seg(lt, 4, 5.5))))
    BOY.draw(F.ctx, 760, GROUND, BS, bp, WARM, t)
    F.screen()
    EMBERS.draw(F.ctx, F.sw, F.sh, t, hexc("#ffe0a0"), 0.7)
    light_leak(F.ctx, F.sw, F.sh, t, 0.9)
    F.grade(G_WARM)


def s_memory_eyes(F, lt, d):
    """MEMORY - they look into each other's eyes and smile."""
    t = F.t
    p_w = env.pal("warm")
    F.cam(960, 560, 1.0)
    CITY.draw(F.ctx, 1200, F.x0, F.x1, p_w, t)
    warm_sky_sun(F, 980, 520)
    F.blur(26)
    F.screen()
    BOKEH_WARM.draw(F.ctx, F.sw, F.sh, t, 1.0, pan=lt * 0.02)
    z = 2.1 + lt * 0.07
    F.cam(960, head_y(BS) + 40, z, focus=960, vzoom=0.62)
    k = smooth(seg(lt, 0.0, 0.8))
    BOY.draw(F.ctx, 830, GROUND, BS, pose(turn=0.55, **happy_face(t, 1, smile=lerp(0.2, 0.7, k),
                                                                     blush=0.6 * k, look_x=0.8)), WARM, t)
    GIRL.draw(F.ctx, 1090, GROUND, GS, pose(turn=-0.55, wind=0.35,
                                             **happy_face(t, 3, smile=0.8, blush=0.7 * k, look_x=0.8,
                                                          mouth_open=0.3 * k)), WARM, t)
    F.screen()
    EMBERS.draw(F.ctx, F.sw, F.sh, t, hexc("#fff0c0"), 0.6)
    light_leak(F.ctx, F.sw, F.sh, t, 0.8)
    F.grade(G_WARM, bloom=0.85)


def s_memory_walk(F, lt, d):
    """MEMORY - walking together through the golden city; she rides beside him."""
    t = F.t
    p_w = env.pal("warm")
    bx = 500 + lt * 120
    F.cam(bx + 160, 560, 1.0, focus=bx + 110, vzoom=0.85)
    CITY.draw(F.ctx, bx, F.x0, F.x1, p_w, t)
    F.ctx.save()
    sx = bx + 700
    warm_sky_sun(F, sx, 520)
    F.ctx.restore()
    CITY.near.draw(F.ctx, bx + 160, F.x0, F.x1, p_w, "near", t, 0.5)
    env.street(F.ctx, F.x0, F.x1, CITY.base_y, p_w, t, wet=0.2, lamps=False)
    gx = bx + 230 + math.sin(lt * 0.9) * 25
    GIRL.draw(F.ctx, gx, GROUND - 12, GS,
              skate_pose(t, push=0.5, turn=0.8, wind=0.7,
                         **happy_face(t, 6, smile=0.85, mouth_open=0.35 + 0.25 * math.sin(t * 5) ** 2,
                                      look_x=-0.9, head_tilt=-6)), WARM, t)
    ph = bx / (BS * 30) * math.pi
    BOY.draw(F.ctx, bx, GROUND + 8, BS,
             walking(ph, turn=0.85, **happy_face(t, 7, smile=0.7, look_x=0.6, mouth_open=0.2)), WARM, t)
    F.screen()
    EMBERS.draw(F.ctx, F.sw, F.sh, t, hexc("#ffe0a0"), 0.8)
    light_leak(F.ctx, F.sw, F.sh, t * 1.3, 1.0)
    F.grade(G_WARM)


def s_present_alone(F, lt, d):
    """PRESENT - the same street, cold and blue; her ghost fades away."""
    t = F.t
    bx = 640 + lt * 85
    F.cam(bx + 160, 560, 1.0, focus=bx + 110, vzoom=0.85)
    city_street(F, bx + 160, env.pal("rain"), t, wet=1.0)
    ga = 0.45 * (1 - smooth(seg(lt, 0.2, 2.2)))
    if ga > 0.01:
        gx = bx + 230
        GIRL.draw(F.ctx, gx, GROUND - 12, GS, skate_pose(t, push=0.5, turn=0.8, alpha=ga, shadow=0,
                                                          **happy_face(t, 6, smile=0.8)), WARM, t)
        F.screen()
        F.cam(bx + 160, 560, 1.0, focus=bx + 110, vzoom=0.85)
        dissolve_particles(F.ctx, gx, GROUND - 200, 140, 300, seg(lt, 0.3, 2.5), t, seed=4)
    ph = bx / (BS * 30) * math.pi
    BOY.draw(F.ctx, bx, GROUND + 8, BS,
             walking(ph, speed=0.75, turn=0.9, hand_front="pocket", hand_back="pocket", sh_front=6,
                     el_front=40, sh_back=4, el_back=40,
                     **sad_face(t, 8, nod=0.4, look_x=-0.3 if lt < 2 else 0.2)), RAIN, t)
    rain(F, t, 0.6)
    F.grade(G_RAIN)


def s_memory_evening(F, lt, d):
    """MEMORY - a happy evening under the city lights."""
    t = F.t
    p_d = env.pal("dusk")
    F.cam(960 + lt * 10, 560, 1.06 + lt * 0.012, focus=960 + lt * 10, vzoom=0.8, vy=640)
    CITY.draw(F.ctx, 900 + lt * 10, F.x0, F.x1, p_d, t)
    env.street(F.ctx, F.x0, F.x1, CITY.base_y, p_d, t, wet=0.2, lamps=False)
    ctx = F.ctx
    string_lights(ctx, F.x0 - 100, 1000, 120, 160, t)
    string_lights(ctx, 1000, F.x1 + 100, 120, 130, t + 2)
    # low wall they sit on
    rgba(ctx, hexc("#2a2244"))
    ctx.rectangle(F.x0 - 50, 860, F.x1 - F.x0 + 100, 220)
    ctx.fill()
    rgba(ctx, hexc("#3a3060"))
    ctx.rectangle(F.x0 - 50, 850, F.x1 - F.x0 + 100, 18)
    ctx.fill()
    laugh = 0.5 + 0.5 * math.sin(lt * 4.2)
    # board leaning on the wall
    ctx.save()
    ctx.translate(1370, 935)
    ctx.rotate(-1.3)
    ctx.scale(4.4, 4.4)
    GIRL.L = Lighting((1.0, 0.9, 0.9), hexc("#ff9a6a"), 0.06)
    GIRL.draw_board(ctx, 0, dict(board_tilt=0))
    ctx.restore()
    L = Lighting((1.0, 0.9, 0.92), hexc("#ff9a6a"), 0.08)
    BOY.draw(ctx, 860, 1015, GS, sit_pose(turn=0.5, **happy_face(t, 9, smile=0.85, mouth_open=0.35 * laugh,
                                                                   look_x=0.6, head_tilt=4 * laugh)), L, t)
    GIRL.draw(ctx, 1130, 1060, 4.5, sit_pose(turn=-0.45, wind=0.2, head_tilt=-8 - 4 * laugh,
                                              **happy_face(t, 10, smile=0.9, mouth_open=0.45 * laugh,
                                                           look_x=0.7, blush=0.5)), L, t)
    F.screen()
    DUST.draw(ctx, F.sw, F.sh, t, hexc("#ffe7a0"), 0.6, mode="drift")
    light_leak(ctx, F.sw, F.sh, t, 0.6, col1=hexc("#ff7a8a"))
    F.grade(G_DUSK)


def _rain_clock(lt, stop_at, resume_at=None, base=0.0):
    """Integrated rain time that slows to a freeze (time stops) and resumes."""
    def speed(x):
        s = 1 - smooth(seg(x, stop_at - 0.8, stop_at))
        if resume_at is not None:
            s = max(s, smooth(seg(x, resume_at, resume_at + 1.0)))
        return s
    # numeric integral (cheap, piecewise)
    n = max(1, int(lt * 20))
    acc = 0.0
    for i in range(n):
        acc += speed((i + 0.5) / n * lt) * lt / n
    return base + acc, speed(lt)


def s_appear(F, lt, d):
    """PRE-HOOK - she appears in front of him; time stops."""
    t = F.t
    rt, spd = _rain_clock(lt, 2.6, base=F.t - lt)
    F.cam(960, 560, 1.12 + lt * 0.02, focus=1000, vzoom=0.8)
    city_street(F, 960, env.pal("rain"), t, wet=1.0)
    F.blur(lerp(2, 16, smooth(seg(lt, 1.0, 3.0))))
    F.screen()
    BOKEH.draw(F.ctx, F.sw, F.sh, t, smooth(seg(lt, 1.0, 3.0)), drift=spd)
    F.cam(960, 560, 1.12 + lt * 0.02, focus=1000, vzoom=0.8)
    ap = smooth(seg(lt, 1.0, 2.8))
    if ap > 0:
        radial_glow(F.ctx, 1180, 700, 520, hexc("#ffb36a"), 0.35 * ap)
        GIRL.draw(F.ctx, 1180, GROUND, GS, pose(turn=-0.4, wind=0.4 * spd + 0.15, alpha=ap,
                                                 **happy_face(t, 11, smile=0.5, look_x=0.5)), WARM, t)
        dissolve_particles(F.ctx, 1180, GROUND - 220, 150, 360, 1.2 - ap * 1.1, t, seed=12)
    look_up = smooth(seg(lt, 1.6, 3.2))
    bp = pose(turn=0.45, hand_front="pocket", hand_back="pocket", sh_front=6, el_front=40, sh_back=4,
              el_back=40, **sad_face(t, 12, nod=lerp(0.45, 0.0, look_up), lid=lerp(0.4, 0.0, look_up),
                                     brow=lerp(-0.8, 0.3, look_up), smile=lerp(-0.3, 0.1, look_up),
                                     look_x=look_up * 0.7))
    BOY.draw(F.ctx, 760, GROUND, BS, bp, RAIN, t)
    rain(F, t, 0.7, speed=spd, frozen=spd < 0.05, rt=rt)
    F.grade(G_RAIN, sat=lerp(0.92, 1.05, ap))


def s_orbit(F, lt, d):
    """PRE-HOOK - the camera circles slowly around the two of them."""
    t = F.t
    th = math.pi / 2 - 0.75 + 1.5 * ease_io(seg(lt, 0, d))
    F.cam(960, 560, 1.0)
    city_street(F, 960 + th * 900, env.pal("rain"), t, wet=1.0)
    F.blur(18)
    F.screen()
    BOKEH.draw(F.ctx, F.sw, F.sh, t, 1.0, pan=th * 0.45, drift=0)
    BOKEH_WARM.draw(F.ctx, F.sw, F.sh, t, 0.5, pan=th * 0.2, drift=0, scale=0.7)
    # frozen rain drops (parallax with the orbit)
    RAIN_FX.draw(F.ctx, F.sw, F.sh, 3.3 + th * 0.05, 0.5, frozen=True, angle=0.18 + (th - 1.57) * 0.1)
    F.cam(960, 640, 1.2, focus=960, vzoom=0.52, vy=700)
    R = 330
    figs = []
    for who, off in ((BOY, 0.0), (GIRL, math.pi)):
        a = th + off
        x = 960 + R * math.sin(a)
        depth = math.cos(a)
        figs.append((depth, who, x, a))
    figs.sort(key=lambda f: f[0])
    bxs = {id(f[1]): f[2] for f in figs}
    for depth, who, x, a in figs:
        other = bxs[id(GIRL) if who is BOY else id(BOY)]
        tr = clamp((other - x) / (2 * R) * 1.6, -0.9, 0.9)
        if abs(tr) < 0.08:
            tr = 0.08 if other >= x else -0.08
        sc = GS * (1 + 0.1 * depth)
        y = GROUND - 20 + depth * 28
        if who is BOY:
            p = pose(turn=tr, **happy_face(t, 13, smile=0.35, brow=0.4, look_x=0.6, blush=0.3))
            L = Lighting((0.85, 0.85, 1.0), hexc("#ffb36a"), 0.06)
        else:
            p = pose(turn=tr, wind=0.2, **happy_face(t, 14, smile=0.6, look_x=0.6, blush=0.3))
            L = WARM
        radial_glow(F.ctx, x, y - 280, 380, hexc("#ffb36a"), 0.12)
        who.draw(F.ctx, x, y, sc, p, L, t)
    F.grade(G_RAIN, sat=1.05, bloom=0.7)


def s_vanish(F, lt, d):
    """PRE-HOOK - he reaches for her and she vanishes like a memory."""
    t = F.t
    rt, spd = _rain_clock(lt, -10, resume_at=1.4, base=3.3)
    F.cam(980, 600, 1.35, focus=lerp(900, 1080, smooth(seg(lt, 0, 2))), vzoom=0.8)
    city_street(F, 980, env.pal("rain"), t, wet=1.0)
    F.blur(lerp(16, 4, smooth(seg(lt, 1.4, 3.0))))
    F.cam(980, 600, 1.35, focus=lerp(900, 1080, smooth(seg(lt, 0, 2))), vzoom=0.8)
    dis = smooth(seg(lt, 1.0, 2.6))
    if dis < 1:
        radial_glow(F.ctx, 1180, 700, 420, hexc("#ffb36a"), 0.35 * (1 - dis))
        GIRL.draw(F.ctx, 1180, GROUND, GS, pose(turn=-0.45, wind=0.3 + dis, alpha=1 - dis,
                                                 **happy_face(t, 15, smile=0.5 - 0.4 * dis, look_x=0.6)), WARM, t)
    dissolve_particles(F.ctx, 1180, GROUND - 230, 160, 380, seg(lt, 0.9, 3.4), t, seed=15, n=420)
    reach = smooth(seg(lt, 0.0, 1.4))
    bp = pose(turn=0.6, sh_front=lerp(4, 78, reach), el_front=lerp(8, 4, reach), lean=6 * reach,
              hip_front=10 * reach, knee_front=6,
              **sad_face(t, 16, nod=0.0, lid=0.1 + 0.3 * dis, brow=lerp(0.3, -0.9, dis),
                         smile=lerp(0.1, -0.4, dis), look_x=0.7, mouth_open=0.3 * reach * (1 - dis)))
    BOY.draw(F.ctx, 820, GROUND, BS, bp, RAIN, t)
    rain(F, t, 0.75, speed=max(spd, 0.05), frozen=spd < 0.05, rt=rt)
    F.grade(G_RAIN, sat=lerp(1.05, 0.85, dis), flash=0.5 * smooth(seg(lt, d - 0.35, d)))


def s_title(F, lt, d, variant=0):
    """CHORUS - WARUM DU? over a wide rainy street."""
    t = F.t
    hit = F.beat(decay=5.0)
    F.do_shake(6 * hit + (14 if variant == 2 else 4) * math.exp(-lt * 3))
    z = 0.85 + lt * 0.02 + 0.015 * hit
    F.cam(960, 520, z, focus=960, vzoom=0.9)
    city_street(F, 960 + lt * 20, env.pal("rain"), t, wet=1.0)
    bp = pose(turn=0.05, hand_front="pocket", hand_back="pocket", sh_front=6, el_front=40, sh_back=4,
              el_back=40, **sad_face(t, 17, nod=-0.2, lid=0.1, look_y=-0.6))
    env.street_lamp(F.ctx, 1010, CITY.base_y + 14, t, 1.0)
    BOY.draw(F.ctx, 960, GROUND, 3.2, bp, RAIN, t)
    rain(F, t, 1.0, speed=1.2)
    F.screen()
    k = ease_out(seg(lt, 0, 0.6))
    a = smooth(seg(lt, 0.0, 0.25)) * (1 - smooth(seg(lt, d - 0.5, d)))
    title(F.ctx, F.sw, F.sh, "WARUM DU?", t, a, scale=lerp(1.35, 1.0, k) * (1 + 0.02 * hit),
          y=F.sh * (0.32 if not F.vertical else 0.3), split=(12 * (1 - k) + 6 * hit) * F.base)
    F.grade(G_RAIN, flash=0.85 * math.exp(-lt * 4.5), ca=4 * hit + 4 * math.exp(-lt * 3), sat=1.0,
            bloom=0.7)


def s_eyes(F, lt, d):
    """CHORUS - extreme close-up of his eyes behind the glasses."""
    t = F.t
    s = 30 + lt * 1.6
    F.cam(960, 540, 1.0)
    CITY.draw(F.ctx, 960, F.x0, F.x1, env.pal("rain"), t)
    F.blur(30)
    F.screen()
    BOKEH.draw(F.ctx, F.sw, F.sh, t, 1.0, pan=lt * 0.01)
    F.cam(960, 540, 1.0)
    turn = 0.15
    hy = -84.5 + 1.0
    bx = 960 - turn * 4.6 * 1.32 * s * 0.0
    BOY.draw(F.ctx, bx, 540 - hy * s + 30, s,
             pose(turn=turn, reflect=1.0, **sad_face(t, 18, nod=0.0, lid=0.25 + 0.15 * seg(lt, 2.5, 3.5),
                                                       look_x=0.2 * math.sin(lt), brow=-0.9,
                                                       tears=smooth(seg(lt, 1.8, d)))), RAIN, t)
    rain(F, t, 0.8, speed=0.8)
    F.grade(G_RAIN, ca=2 * F.beat(), bloom=0.6)


def s_her_smile(F, lt, d):
    """CHORUS - she smiles in his memories (slow, warm)."""
    t = F.t
    tt = t * 0.6  # slow motion feel for hair/particles
    F.cam(960, 540, 1.0)
    CITY.draw(F.ctx, 1500, F.x0, F.x1, env.pal("warm"), t)
    warm_sky_sun(F, 760, 600)
    F.blur(24)
    F.screen()
    BOKEH_WARM.draw(F.ctx, F.sw, F.sh, tt, 1.0, pan=lt * 0.015)
    z = 3.0 + lt * 0.06
    F.cam(985, head_y(GS) + 70, z, focus=980, vzoom=0.75)
    laugh = smooth(seg(lt, 1.0, 1.8)) * (1 - smooth(seg(lt, 3.0, 3.8)))
    GIRL.draw(F.ctx, 960, GROUND, GS,
              pose(turn=-0.2, wind=0.55, head_tilt=-5 + 3 * math.sin(tt), **happy_face(
                  t, 19, smile=0.8, mouth_open=0.45 * laugh, look_x=0.3, blush=0.6,
                  blink=1.0 if 2.2 < lt < 2.33 else 0.0)), WARM, tt)
    F.screen()
    EMBERS.draw(F.ctx, F.sw, F.sh, tt, hexc("#fff0c0"), 0.8)
    light_leak(F.ctx, F.sw, F.sh, tt, 1.0)
    F.grade(G_WARM, bloom=0.6, bloom_thr=165)


def s_room(F, lt, d, clock="02:14", checking=False):
    """He sits alone in his room at night, phone in his hands."""
    t = F.t
    z = 1.3 + lt * 0.015
    F.cam(1060, 580, z, focus=1180, vzoom=0.75)
    env.bedroom(F.ctx, t, rain=1.0, phone_light=1.0, window_city=CITY, clock=clock)
    if checking:
        cyc = (lt % 2.4) / 2.4
        up = smooth(seg(cyc, 0.0, 0.18)) * (1 - smooth(seg(cyc, 0.62, 0.82)))
    else:
        up = 1.0
    p = sit_pose(turn=0.25, sh_front=lerp(10, 20, up), el_front=lerp(50, 105, up), phone=1 if up > 0.3 else 0,
                 phone_glow=up, **sad_face(t, 20, nod=lerp(0.6, 0.45, up), look_y=0.8, lid=0.4))
    BOY.draw(F.ctx, 1180, 920, 4.6, p, ROOM, t)
    F.grade(G_ROOM)


def s_phone_chat(F, lt, d, mode="noreply"):
    """Close-up of the chat: delivered, read... and no answer."""
    t = F.t
    F.cam(1000, 540, 1.6, focus=1150)
    env.bedroom(F.ctx, t, rain=1.0, phone_light=1.0, window_city=CITY)
    F.blur(26)
    F.screen()
    ph_h = F.sh * (0.86 if not F.vertical else 0.6) * (1 + lt * 0.012)
    cx, cy = F.sw / 2, F.sh * 0.53
    if mode == "noreply":
        n = min(3.0, 2.0 + lt * 1.4)
        status = "zuletzt online um 01:58"
        typing = 0.0
        draft = ""
        if lt > 1.8:
            draft = "Bitte"[:int((lt - 1.8) * 5)]
        if lt > 3.2:
            draft = ""
        clock = "02:30"
    else:  # "online": she is online, starts typing, then stops
        n = 3
        if lt < 1.0:
            status, typing = "online", 0.0
        elif lt < 3.0:
            status, typing = "schreibt …", smooth(seg(lt, 1.0, 1.3))
        elif lt < 4.0:
            status, typing = "online", 1 - smooth(seg(lt, 3.0, 3.25))
        else:
            status, typing = "zuletzt online um 02:31", 0.0
        draft = "Ich vermiss dich"[:max(0, int((lt - 0.2) * 7))] if lt < 2.6 else ""
        clock = "02:31"
    holding_hand(F.ctx, cx, cy, ph_h, BOY.skin, BOY.sleeve, HAND_L, "back")
    phone_ui(F.ctx, cx, cy, ph_h, t, mode="chat", status=status, n_msgs=n, typing=typing,
             clock=clock, draft=draft)
    holding_hand(F.ctx, cx, cy, ph_h, BOY.skin, BOY.sleeve, HAND_L, "front")
    F.grade(G_ROOM, bloom=0.45, vignette=0.5)


def s_window_rain(F, lt, d):
    """Slow-motion rain on the window; his faint reflection in the glass."""
    t = F.t
    tt = t * 0.35
    F.cam(960, 540, 1.0)
    CITY.draw(F.ctx, 960 + lt * 6, F.x0, F.x1, env.pal("rain"), t)
    F.blur(28)
    F.screen()
    BOKEH.draw(F.ctx, F.sw, F.sh, tt, 1.0, scale=1.3)
    env.rain_on_glass(F.ctx, 0, 0, F.sw, F.sh, tt * 0.8, 1.0, n=150)
    F.cam(960, 540, 1.0, focus=960)
    BOY.draw(F.ctx, 1250, 560 + 84 * 18, 18,
             pose(turn=-0.35, alpha=0.13, shadow=0, **sad_face(t, 21, nod=0.2, lid=0.45)), RAIN, t)
    F.grade(G_RAIN, bloom=0.6, sat=0.95)


def s_separated(F, lt, d):
    """CHORUS - the two of them separated by a lit street; cars streak past."""
    t = F.t
    p = env.pal("rain")
    F.cam(960 + lt * 8, 560, 1.0, focus=lerp(560, 1450, smooth(seg(lt, d * 0.4, d * 0.62))), vzoom=0.85)
    ctx = F.ctx
    env.draw_sky(ctx, p, F.x0, -600, F.x1 - F.x0, 1300, t)
    CITY.far.draw(ctx, 960, F.x0, F.x1, p, "far", t)
    ctx.save()
    ctx.translate(0, -150)
    CITY.mid.draw(ctx, 960, F.x0, F.x1, p, "mid", t)
    ctx.restore()
    env.fog_band(ctx, F.x0, F.x1, 520, 200, hexc(p["fog"]) if isinstance(p["fog"], str) else p["fog"], 0.25, t)
    # far sidewalk
    rgba(ctx, hexc("#232a48"))
    ctx.rectangle(F.x0, 640, F.x1 - F.x0, 40)
    ctx.fill()
    # her in a warm halo on the other side
    radial_glow(ctx, 1450, 520, 300, hexc("#ffb36a"), 0.35)
    env.street_lamp(ctx, 1380, 662, t, 0.6, 1.0, height=300)
    GIRL.draw(ctx, 1450, 668, 2.5, pose(turn=-0.4, wind=0.25, **happy_face(t, 22, smile=0.1, brow=-0.4,
                                                                               look_x=0.6)), WARM, t)
    # road
    vgrad(ctx, F.x0, 680, F.x1 - F.x0, 200, [(0, hexc("#141a2e")), (1, hexc("#0e1222"))])
    rgba(ctx, (0.9, 0.9, 0.8), 0.5)
    for k in range(int(F.x0 // 160) - 1, int(F.x1 // 160) + 2):
        ctx.rectangle(k * 160, 776, 80, 6)
    ctx.fill()
    # slow-motion cars with light streaks
    for i, (lane, speed, ph) in enumerate(((0, 1, 0.0), (1, -1, 0.45), (0, 1, 0.7))):
        y = 735 if lane == 0 else 830
        x = F.x0 + ((ph * 3000 + lt * 300 * speed) % 3000) - 300 if speed > 0 else \
            F.x1 - ((ph * 3000 + lt * 300) % 3000) + 300
        head = hexc("#fff2c8")
        tail = hexc("#ff3a3a")
        front = 1 if speed > 0 else -1
        # streaks
        g = cairo.LinearGradient(x - front * 600, 0, x, 0)
        g.add_color_stop_rgba(0, *tail, 0)
        g.add_color_stop_rgba(1, *tail, 0.5)
        ctx.set_source(g)
        ctx.rectangle(min(x, x - front * 600), y - 4, 600, 8)
        ctx.fill()
        rgba(ctx, hexc("#0a0c16"))
        ctx.rectangle(x - 150, y - 50, 300, 52)
        ctx.fill()
        ctx.rectangle(x - 90, y - 85, 170, 40)
        ctx.fill()
        rgba(ctx, hexc("#7aa8ff"), 0.25)
        ctx.rectangle(x - 80, y - 80, 150, 28)
        ctx.fill()
        radial_glow(ctx, x + front * 150, y - 20, 160, head, 0.6)
        radial_glow(ctx, x - front * 150, y - 20, 60, tail, 0.7)
        rgba(ctx, head, 0.15)
        ctx.rectangle(x + front * 150 - 30, y, 60, 90)
        ctx.fill()
    # near sidewalk + boy
    vgrad(ctx, F.x0, 880, F.x1 - F.x0, 400, [(0, hexc("#1d2340")), (1, hexc("#0e1122"))])
    rgba(ctx, hexc("#2c3358"))
    ctx.rectangle(F.x0, 876, F.x1 - F.x0, 10)
    ctx.fill()
    BOY.draw(ctx, 560, 1040, 4.6, pose(turn=0.55, hand_front="pocket", hand_back="pocket", sh_front=6,
                                       el_front=40, sh_back=4, el_back=40,
                                       **sad_face(t, 23, nod=0.0, lid=0.25, look_x=0.8, look_y=-0.3)), RAIN, t)
    rain(F, t, 0.9, speed=0.45)
    F.grade(G_RAIN, ca=2 * F.beat(), sat=1.0)


def s_room_wide(F, lt, d):
    """VERSE 2 - 02:30. He checks the phone again and again."""
    t = F.t
    if lt < 1.5:
        # insert: the clock
        F.cam(875, 695, 4.0 - lt * 0.3, focus=875)
        env.bedroom(F.ctx, t, rain=1.0, phone_light=0.6, window_city=CITY, clock="02:30")
        F.grade(G_ROOM, bloom=0.8)
        return
    s_room(F, lt, d, clock="02:30", checking=True)


def s_leave(F, lt, d):
    """VERSE 2 - he leaves the house into the heavy rain."""
    t = F.t
    door_x = 760
    bx = door_x + max(0, lt - 0.8) * 120
    F.cam(lerp(960, bx + 160, smooth(seg(lt, 0.5, 2.5))), 560, 1.0, focus=bx + 60, vzoom=0.9)
    city_street(F, 960, env.pal("rain"), t, wet=1.0)
    ctx = F.ctx
    # doorway in the facade
    op = smooth(seg(lt, 0.0, 0.8)) * (1 - smooth(seg(lt, 3.0, 4.0)))
    rgba(ctx, hexc("#0b0d18"))
    ctx.rectangle(door_x - 90, CITY.base_y - 330, 180, 340)
    ctx.fill()
    vgrad(ctx, door_x - 75, CITY.base_y - 315, 150, 325, [(0, hexc("#ffcf8a")), (1, hexc("#ff9a5c"))], op)
    rgba(ctx, hexc("#ffcf8a"), 0.22 * op)
    ctx.move_to(door_x - 75, CITY.base_y + 10)
    ctx.line_to(door_x + 75, CITY.base_y + 10)
    ctx.line_to(door_x + 260, 1080)
    ctx.line_to(door_x - 200, 1080)
    ctx.close_path()
    ctx.fill()
    radial_glow(ctx, door_x, CITY.base_y - 360, 50, hexc("#ffe2a8"), 0.8)
    ph = bx / (BS * 30) * math.pi
    walk = lt > 0.8
    p = walking(ph, speed=0.85 if walk else 0.0, turn=0.85, hand_front="pocket", hand_back="pocket",
                sh_front=6, el_front=40, sh_back=4, el_back=40, **sad_face(t, 24, nod=0.45))
    BOY.draw(ctx, bx, GROUND, BS, p, RAIN, t)
    rain(F, t, 1.0, speed=1.3)
    F.screen()
    Rain.splashes(F.ctx, 0, F.sw, F.sh * 0.82, F.sh, t, 1.0)
    F.grade(G_RAIN)


def s_rain_walk(F, lt, d):
    """VERSE 2 - walking through the downpour; friends in the distance."""
    t = F.t
    bx = 400 + lt * 115
    camx = bx + 200
    F.cam(camx, 560, 1.0, focus=bx + 40, vzoom=0.9)
    city_street(F, camx, env.pal("rain"), t, wet=1.0, lamp_offset=60)
    ctx = F.ctx
    # friends under a lamp, further back (smaller, darker) - they wave
    fx = 1350
    for i, fr in enumerate(FRIENDS):
        wave = math.sin(t * 6 + i) * 0.5 + 0.5 if i == 1 and lt > 2.5 else 0
        fp = pose(turn=-0.3 + i * 0.25, sh_front=lerp(4, 150, wave * 0.8) if i == 1 else 6,
                  el_front=30 if i == 1 else 10, smile=0.4, blink=blink_at(t, 30 + i))
        fr.draw(ctx, fx + i * 85, CITY.base_y + 90, 2.6, fp, Lighting((0.5, 0.55, 0.75), hexc("#20284a"), 0.35), t)
    ph = bx / (BS * 30) * math.pi
    look = smooth(seg(lt, 3.0, 4.0)) * (1 - smooth(seg(lt, 5.0, 6.0)))
    BOY.draw(ctx, bx, GROUND + 10, 4.5,
             walking(ph, speed=0.9, turn=0.9, hand_front="pocket", hand_back="pocket", sh_front=6,
                     el_front=40, sh_back=4, el_back=40, **sad_face(t, 25, nod=0.5 - 0.3 * look,
                                                                    look_x=0.6 * look, look_y=-0.3 * look)),
             RAIN, t)
    rain(F, t, 1.0, speed=1.3)
    F.screen()
    Rain.splashes(F.ctx, 0, F.sw, F.sh * 0.8, F.sh, t, 1.0, n=80)
    F.grade(G_RAIN)


def s_cross_city(F, lt, d):
    """VERSE 2 - the camera follows him across the city (wide crane shot)."""
    t = F.t
    z = lerp(0.62, 0.72, smooth(seg(lt, 0, d)))
    bx = 300 + lt * 140
    F.cam(960 + lt * 30, lerp(420, 520, smooth(seg(lt, 0, d))), z, focus=bx + 100, vzoom=1.4)
    p = env.pal("rain")
    city_street(F, 960, p, t, wet=1.0, lamp_period=700)
    ctx = F.ctx
    # crosswalk + traffic light
    rgba(ctx, (0.9, 0.92, 1.0), 0.55)
    for i in range(7):
        ctx.rectangle(820 + i * 70, 880, 40, 220)
    ctx.fill()
    tl_red = lt < 3.5
    rgba(ctx, hexc("#0b0c18"))
    ctx.rectangle(1260, 520, 14, 330)
    ctx.rectangle(1240, 470, 54, 120)
    ctx.fill()
    radial_glow(ctx, 1267, 495, 80, hexc("#ff3b3b") if tl_red else hexc("#3bff8a"), 0.7)
    rgba(ctx, hexc("#ff3b3b") if tl_red else (0.2, 0.2, 0.2))
    ctx.arc(1267, 495, 12, 0, 6.3)
    ctx.fill()
    rgba(ctx, hexc("#3bff8a") if not tl_red else (0.2, 0.2, 0.2))
    ctx.arc(1267, 560, 12, 0, 6.3)
    ctx.fill()
    ph = bx / (BS * 30) * math.pi
    BOY.draw(ctx, bx, 990, 4.0, walking(ph, speed=0.9, turn=0.9, hand_front="pocket", hand_back="pocket",
                                        sh_front=6, el_front=40, sh_back=4, el_back=40,
                                        **sad_face(t, 26, nod=0.4)), RAIN, t)
    # a car passing in the foreground (bokeh streak)
    cx = 2600 - ((lt * 900) % 4200)
    radial_glow(ctx, cx, 1120, 260, hexc("#fff2c8"), 0.5)
    rgba(ctx, hexc("#07080f"))
    ctx.rectangle(cx - 30, 1060, 560, 140)
    ctx.fill()
    rain(F, t, 1.0, speed=1.2)
    F.grade(G_RAIN)


def s_stop(F, lt, d):
    """BREAK - he stops. The rain slows. A warm light appears far away."""
    t = F.t
    rt, spd = _rain_clock(lt, 2.4, base=F.t - lt)
    F.cam(980, 560, 1.15 + lt * 0.03, focus=860, vzoom=0.85)
    city_street(F, 980, env.pal("rain"), t, wet=1.0)
    glow = smooth(seg(lt, 0.8, d))
    radial_glow(F.ctx, 1700, 720, 600, hexc("#ffb36a"), 0.4 * glow)
    BOY.draw(F.ctx, 820, GROUND, BS,
             pose(turn=0.55, hand_front="pocket", hand_back="pocket", sh_front=6, el_front=40, sh_back=4,
                  el_back=40, **sad_face(t, 27, nod=lerp(0.4, -0.15, smooth(seg(lt, 0.5, 2.0))),
                                         lid=0.1, brow=lerp(-0.8, 0.2, glow), look_x=0.9 * glow)), RAIN, t)
    rain(F, t, 0.8, speed=spd, rt=rt, frozen=spd < 0.05)
    F.grade(G_RAIN, sat=lerp(0.9, 1.0, glow))


def s_run(F, lt, d):
    """PRE-HOOK 2 - he runs toward her; night slowly turns into warm light."""
    t = F.t
    k = smooth(seg(lt, 0.5, d - 0.5))
    run_k = smooth(seg(lt, 0.0, 0.8))
    bx = 400 + lt * 330 * run_k
    gx = bx + lerp(1100, 360, ease_io(seg(lt, 0, d)))
    camx = lerp(bx + 300, (bx + gx) / 2, k)
    F.cam(camx, 560, 1.0, focus=lerp(bx + 80, (bx + gx) / 2, k), vzoom=lerp(0.85, 0.5, k), vy=lerp(560, 640, k))
    pal = env.mix_pal("rain", "warm", k)
    CITY.draw(F.ctx, camx, F.x0, F.x1, pal, t, lit=1.0)
    if k > 0.05:
        warm_sky_sun(F, camx + 500, 520, k)
    env.street(F.ctx, F.x0, F.x1, CITY.base_y, pal, t, wet=1 - k * 0.8, lamps=False)
    L = Lighting(tuple(lerp(a, b, k) for a, b in zip(RAIN.mult, WARM.mult)), mix(RAIN.add, WARM.add, k),
                 lerp(RAIN.add_k, WARM.add_k, k))
    radial_glow(F.ctx, gx, GROUND - 260, 500, hexc("#ffb36a"), 0.25 + 0.3 * k)
    GIRL.draw(F.ctx, gx, GROUND, GS, pose(turn=-0.6, sh_front=lerp(5, 60, k), el_front=10, wind=0.4,
                                          **happy_face(t, 28, smile=0.7, look_x=0.6)), WARM, t)
    ph = bx / (BS * 22) * math.pi
    bp = blend(pose(turn=0.85), run_pose(ph, turn=0.9), run_k)
    bp.update(happy_face(t, 29, smile=lerp(-0.2, 0.5, k), brow=lerp(-0.6, 0.5, k), look_x=0.7,
                         mouth_open=0.3, blush=0.3 * k))
    BOY.draw(F.ctx, bx, GROUND, BS, bp, L, t)
    rain(F, t, 0.9 * (1 - k), speed=1.0)
    F.screen()
    if k > 0.2:
        EMBERS.draw(F.ctx, F.sw, F.sh, t, hexc("#ffe0a0"), 0.8 * k)
        light_leak(F.ctx, F.sw, F.sh, t, k)
    F.grade(G_RAIN if k < 0.5 else G_WARM, tint=tuple(lerp(a, b, k) for a, b in zip(G_RAIN["tint"], G_WARM["tint"])),
            lift=tuple(lerp(a, b, k) for a, b in zip(G_RAIN["lift"], G_WARM["lift"])),
            bloom=lerp(0.5, 0.8, k))


def s_hands(F, lt, d):
    """PRE-HOOK 2 - their hands almost touch in golden light."""
    t = F.t
    F.cam(960, 540, 1.0)
    CITY.draw(F.ctx, 1300, F.x0, F.x1, env.pal("warm"), t)
    warm_sky_sun(F, 960, 520)
    F.blur(30)
    F.screen()
    BOKEH_WARM.draw(F.ctx, F.sw, F.sh, t * 0.5, 1.0)
    F.cam(960, 540, 1.0 + lt * 0.02, focus=960, vzoom=0.62)
    gap = lerp(420, 30, ease_out(seg(lt, 0, d * 0.75))) + math.sin(t * 5) * 3
    cx, cy = 960, 560
    radial_glow(F.ctx, cx, cy, 120 + 300 * seg(lt, 2, d), hexc("#fff0c0"), 0.5 + 0.4 * seg(lt, 2, d))
    reaching_arm(F.ctx, -300, 760, cx - gap / 2 - 52 * 2.5, cy + 10, 2.5, WARM(BOY.skin), WARM(BOY.sleeve),
                 WARM(BOY.jacket_dark), flip=1, curl=0.1)
    reaching_arm(F.ctx, 2220, 380, cx + gap / 2 + 52 * 2.3, cy - 10, 2.3, WARM(GIRL.skin), WARM(GIRL.sleeve),
                 WARM(GIRL.jacket_dark), flip=-1, curl=0.0)
    F.screen()
    EMBERS.draw(F.ctx, F.sw, F.sh, t * 0.6, hexc("#fff0c0"), 1.0)
    light_leak(F.ctx, F.sw, F.sh, t, 1.0)
    F.grade(G_WARM, bloom=0.95, bloom_thr=130)


def s_shatter(F, lt, d):
    """The memory breaks: white flash, she is gone, the rain returns."""
    t = F.t
    k = smooth(seg(lt, 0.0, 1.2))
    F.cam(960, 560, 1.2, focus=900, vzoom=0.8)
    pal = env.mix_pal("warm", "rain", k)
    CITY.draw(F.ctx, 960, F.x0, F.x1, pal, t)
    env.street(F.ctx, F.x0, F.x1, CITY.base_y, pal, t, wet=k, lamps=False)
    dissolve_particles(F.ctx, 1180, GROUND - 230, 160, 380, seg(lt, 0.0, 1.8), t, seed=31, n=420)
    L = Lighting(tuple(lerp(a, b, k) for a, b in zip(WARM.mult, RAIN.mult)), mix(WARM.add, RAIN.add, k),
                 lerp(WARM.add_k, RAIN.add_k, k))
    drop = smooth(seg(lt, 0.4, 2.0))
    BOY.draw(F.ctx, 900, GROUND, BS,
             pose(turn=0.6, sh_front=lerp(75, 6, drop), el_front=lerp(4, 20, drop), lean=6 * (1 - drop),
                  **sad_face(t, 32, nod=lerp(0.0, 0.6, drop), brow=-1, smile=-0.5, tears=drop)), L, t)
    rain(F, t, 0.9 * k, speed=1.0)
    F.grade(G_RAIN, flash=0.95 * math.exp(-lt * 3.2), sat=lerp(1.0, 0.85, k), ca=6 * math.exp(-lt * 2))


def s_montage(F, lt, d, shots):
    """Beat-cut montage: shots = list of (start_offset, scene_fn, local_offset)."""
    idx = 0
    for i, (st, _, _) in enumerate(shots):
        if lt >= st:
            idx = i
    st, fn, off = shots[idx]
    nxt = shots[idx + 1][0] if idx + 1 < len(shots) else d
    fn(F, lt - st + off, nxt - st + off)
    g = dict(F.g)
    g["flash"] = max(g.get("flash", 0), 0.55 * math.exp(-(lt - st) * 9))
    F.g = g


def s_skate_away(F, lt, d):
    """FINAL CHORUS - she skates away; he stays and watches."""
    t = F.t
    p = env.pal("dusk")
    F.cam(960, 560, 1.0, focus=lerp(700, 1300, smooth(seg(lt, 0, d))), vzoom=0.8)
    ctx = F.ctx
    env.draw_sky(ctx, p, F.x0, -600, F.x1 - F.x0, 1300, t)
    warm_sky_sun(F, 1500, 560, 0.8)
    CITY.far.draw(ctx, 960, F.x0, F.x1, p, "far", t)
    CITY.mid.draw(ctx, 960, F.x0, F.x1, p, "mid", t)
    # road receding to the horizon
    vgrad(ctx, F.x0, 800, F.x1 - F.x0, 400, [(0, hexc("#2a2240")), (1, hexc("#120f1e"))])
    rgba(ctx, hexc("#3a3058"))
    ctx.move_to(1300, 800)
    ctx.line_to(1340, 800)
    ctx.line_to(2400, 1080)
    ctx.line_to(400, 1080)
    ctx.close_path()
    ctx.fill()
    rgba(ctx, (1, 0.9, 0.7), 0.5)
    for i in range(10):
        f0 = ((i / 10 + lt * 0.05) % 1.0)
        f1 = f0 + 0.04
        yy0, yy1 = 800 + 280 * f0 ** 2, 800 + 280 * f1 ** 2
        ctx.move_to(lerp(1320, 1400, f0 ** 2) - 2 * f0, yy0)
        ctx.line_to(lerp(1320, 1400, f1 ** 2) + 2 * f1, yy1)
    ctx.set_line_width(4)
    ctx.stroke()
    # she goes into the distance
    away = ease_io(seg(lt, 0.3, d))
    gs = lerp(3.6, 0.6, away)
    gx = lerp(1250, 1325, away)
    gy = lerp(1060, 805, away)
    GIRL.draw(ctx, gx, gy, gs, skate_pose(t, push=0.6, turn=0.75, wind=0.8,
                                         alpha=1 - smooth(seg(lt, d - 1.2, d)),
                                         **happy_face(t, 33, smile=0.3)), WARM, t)
    BOY.draw(ctx, 620, 1120, 5.6, pose(turn=0.7, hand_front="pocket", hand_back="pocket", sh_front=6,
                                       el_front=40, sh_back=4, el_back=40,
                                       **sad_face(t, 34, nod=0.05, lid=0.2, look_x=0.9, look_y=-0.2,
                                                  tears=smooth(seg(lt, 3, d)))),
             Lighting((0.85, 0.8, 0.95), hexc("#6a3a7a"), 0.12), t)
    rain(F, t, 0.45, speed=0.7)
    F.screen()
    DUST.draw(ctx, F.sw, F.sh, t, hexc("#ffcfa0"), 0.4, mode="drift")
    F.grade(G_DUSK, sat=1.0)


def s_watch(F, lt, d):
    """FINAL CHORUS - close on him, watching her go. Tears."""
    t = F.t
    F.cam(960, 540, 1.0)
    CITY.draw(F.ctx, 700, F.x0, F.x1, env.pal("rain"), t)
    F.blur(26)
    F.screen()
    BOKEH.draw(F.ctx, F.sw, F.sh, t, 0.9)
    z = 2.2 + lt * 0.06
    F.cam(930, head_y(BS) + 50, z, focus=950, vzoom=0.75)
    BOY.draw(F.ctx, 960, GROUND, BS, pose(turn=0.6, **sad_face(t, 35, nod=lerp(0.0, 0.5, smooth(seg(lt, 2.5, d))),
                                                                 lid=0.35, brow=-1, look_x=0.9,
                                                                 tears=1.0, smile=-0.4)), RAIN, t)
    rain(F, t, 0.9, speed=0.8)
    F.grade(G_RAIN, fade=1 - 0.6 * smooth(seg(lt, d - 0.6, d)))


def s_dawn_bench(F, lt, d):
    """OUTRO - the rain stops, dawn breaks; one last look at the phone."""
    t = F.t
    k = smooth(seg(lt, 0, d * 0.8))
    pal = env.mix_pal("rain", "dawn", k)
    F.cam(960, 600, 1.15 - lt * 0.01, focus=960, vzoom=0.75)
    ctx = F.ctx
    CITY.draw(ctx, 960, F.x0, F.x1, pal, t, lit=1 - k * 0.6, near=False)
    env.sun(ctx, 1400, lerp(900, 640, k), 60, k)
    # park: grass, river railing, trees
    vgrad(ctx, F.x0, 800, F.x1 - F.x0, 400, [(0, mix(hexc("#1c2a3a"), hexc("#4a5a5a"), k)),
                                             (1, mix(hexc("#0c121c"), hexc("#2a3238"), k))])
    for i, tx in enumerate((260, 1700, 2050, -150)):
        env.tree(ctx, tx, 830, 520, mix(hexc("#101826"), hexc("#3a4258"), k), t, seed=i)
    env.bench(ctx, 960, 975, 1.0, mix(hexc("#2a2230"), hexc("#5a4044"), k))
    look = smooth(seg(lt, 2.5, 3.4)) * (1 - smooth(seg(lt, 6.5, 7.5)))
    L = Lighting(tuple(lerp(a, b, k) for a, b in zip(RAIN.mult, DAWN.mult)), mix(RAIN.add, DAWN.add, k),
                 lerp(RAIN.add_k, DAWN.add_k, k))
    BOY.draw(ctx, 940, 1050, 4.2, sit_pose(turn=0.2, sh_front=lerp(10, 20, look), el_front=lerp(45, 110, look),
                                          phone=1, phone_glow=look,
                                          **sad_face(t, 36, nod=0.5, look_y=0.8, lid=0.4)), L, t)
    rain(F, t, 0.6 * (1 - smooth(seg(lt, 0, 3.5))), speed=0.9)
    F.screen()
    DUST.draw(ctx, F.sw, F.sh, t, hexc("#ffe0c0"), 0.4 * k, mode="drift")
    F.grade(G_RAIN if k < 0.5 else G_DAWN,
            tint=tuple(lerp(a, b, k) for a, b in zip(G_RAIN["tint"], G_DAWN["tint"])),
            lift=tuple(lerp(a, b, k) for a, b in zip(G_RAIN["lift"], G_DAWN["lift"])))
    if 3.2 < lt < 6.6:
        # inset: the phone - still no answer
        a = smooth(seg(lt, 3.2, 3.7)) * (1 - smooth(seg(lt, 6.1, 6.6)))
        F.ctx.push_group()
        ph_h = F.sh * (0.5 if not F.vertical else 0.36)
        phone_ui(F.ctx, F.sw * (0.78 if not F.vertical else 0.5), F.sh * (0.42 if not F.vertical else 0.3),
                 ph_h, t, mode="lock", clock="06:12", lock_text="Keine neuen Nachrichten")
        F.ctx.pop_group_to_source()
        F.ctx.paint_with_alpha(a)


def s_pullback(F, lt, d):
    """OUTRO - the camera slowly pulls away over the city at sunrise."""
    t = F.t + 20
    z = lerp(1.0, 0.5, ease_io(seg(lt, 0, d)))
    pal = env.pal("dawn")
    F.cam(960, lerp(640, 520, seg(lt, 0, d)), z, focus=960, vzoom=1.2)
    ctx = F.ctx
    CITY.draw(ctx, 960, F.x0, F.x1, pal, t, lit=0.3, near=False)
    env.sun(ctx, 1400, lerp(640, 560, seg(lt, 0, d)), 60, 1.0)
    vgrad(ctx, F.x0, 800, F.x1 - F.x0, 900, [(0, hexc("#4a5a5a")), (1, hexc("#1a2028"))])
    for i, tx in enumerate((260, 1700, 2050, -150)):
        env.tree(ctx, tx, 830, 520, hexc("#3a4258"), t, seed=i)
    env.bench(ctx, 960, 975, 1.0, hexc("#5a4044"))
    BOY.draw(ctx, 940, 1050, 4.2, sit_pose(turn=0.2, sh_front=10, el_front=45, phone=1, phone_glow=0.0,
                                          **sad_face(t, 37, nod=0.2, look_x=0.6, look_y=-0.3, lid=0.3)), DAWN, t)
    F.screen()
    DUST.draw(ctx, F.sw, F.sh, t, hexc("#ffe0c0"), 0.4, mode="drift")
    F.grade(G_DAWN, fade=1 - smooth(seg(lt, d - 1.0, d)))


def s_end(F, lt, d):
    """Black screen. One line: WARUM DU?"""
    t = F.t
    F.screen()
    a = smooth(seg(lt, 0.25, 1.1))
    title(F.ctx, F.sw, F.sh, "WARUM DU?", t, a, scale=0.95 if F.vertical else 0.62, glow_col=hexc("#e8e8ff"),
          flicker=False)
    F.grade(dict(bloom=0.4, vignette=0.0, grain=0.04, sat=1.0), fade=1.0)


# ====================================================================== timeline

def timeline(A):
    """Build the scene list from the analysed song structure.

    Section boundaries come from the structural segmentation in
    build/analysis.json (agglomerative clustering on chroma+MFCC, beat
    synchronous) and the self-similarity repeat analysis (chorus 1 at
    ~59.7 s repeats at ~152.0 s). Inner cuts are snapped to detected beats.
    """
    beats = A["beats"]
    dur = A["duration"]
    segs = [s["start"] for s in A["segments"]]

    def near_seg(x):
        return min(segs, key=lambda s: abs(s - x))

    def snap(x):
        i = bisect.bisect_left(beats, x)
        cands = [beats[j] for j in (i - 1, i) if 0 <= j < len(beats)]
        return min(cands, key=lambda b: abs(b - x)) if cands else x

    # structural anchors (labels assigned from the analysis printout)
    INTRO_END = near_seg(7.9)
    V1_SPIKE = near_seg(25.9)
    V1_B = near_seg(27.9)
    PRE1 = near_seg(44.4)
    CH1 = near_seg(59.7)
    V2 = near_seg(97.0)
    V2_B = near_seg(100.3)
    BRK = near_seg(128.5)
    PRE2 = near_seg(131.4)
    BRK2 = near_seg(149.1)
    CH2 = near_seg(152.0)
    OUTRO = near_seg(180.0)

    bar = 4 * 60.0 / A["tempo"]
    S = []

    def add(a, b, fn, tr="cut", xd=0.0, **kw):
        S.append(dict(start=a, end=b, fn=fn, tr=tr, xd=xd, kw=kw))

    # INTRO
    add(0.0, INTRO_END, s_fly)
    # VERSE 1 - the present, then memories
    a = INTRO_END
    b = snap(INTRO_END + 4 * bar)
    add(a, b, s_walk_alone, "fade", 0.5)
    c = snap(b + 2 * bar)
    add(b, c, s_phone_check, "cut")
    add(c, V1_SPIKE, s_memory_arrive, "memory", 0.8)
    add(V1_SPIKE, V1_B, s_memory_eyes, "fade", 0.3)
    d1 = snap(V1_B + 3 * bar)
    add(V1_B, d1, s_memory_walk, "fade", 0.4)
    d2 = snap(d1 + 2.5 * bar)
    add(d1, d2, s_present_alone, "whip", 0.35)
    add(d2, PRE1, s_memory_evening, "memory", 0.7)
    # PRE-HOOK 1
    p1 = snap(PRE1 + 3 * bar)
    p2 = snap(p1 + 3 * bar)
    add(PRE1, p1, s_appear, "black", 0.6)
    add(p1, p2, s_orbit, "fade", 0.6)
    add(p2, CH1, s_vanish, "fade", 0.5)
    # CHORUS 1
    c1 = snap(CH1 + 2 * bar)
    c2 = snap(c1 + 2 * bar)
    c3 = snap(c2 + 2 * bar)
    c4 = snap(c3 + 2 * bar)
    c5 = snap(c4 + 2 * bar)
    c6 = snap(c5 + 2 * bar)
    c7 = snap(c6 + 3.5 * bar)
    add(CH1, c1, s_title, "white", 0.15)
    add(c1, c2, s_eyes, "cut")
    add(c2, c3, s_her_smile, "memory", 0.4)
    add(c3, c4, s_room, "whip", 0.3)
    add(c4, c5, s_phone_chat, "cut", mode="noreply")
    add(c5, c6, s_window_rain, "fade", 0.5)
    add(c6, c7, s_separated, "fade", 0.4)
    beat = 60.0 / A["tempo"]
    m_len = V2 - c7
    shots = []
    seq = [(s_memory_eyes, 0.5), (s_present_alone, 2.0), (s_her_smile, 1.0), (s_room, 0.5),
           (s_memory_walk, 2.0), (s_eyes, 2.5), (s_title, 0.6), (s_title, 1.5)]
    x = 0.0
    k = 0
    while x < m_len - 0.2 and k < len(seq):
        fn, off = seq[k]
        shots.append((x, fn, off))
        step = 2 * beat if k < 5 else (3 * beat if k < 6 else 4 * beat)
        x = snap(c7 + x + step) - c7
        k += 1
    add(c7, V2, s_montage, "cut", shots=shots)
    # VERSE 2 - loneliness
    v1 = snap(V2 + 3.5 * bar)
    v2 = snap(v1 + 2.5 * bar)
    v3 = snap(v2 + 2.5 * bar)
    v4 = snap(v3 + 3.5 * bar)
    add(V2, v1, s_room_wide, "black", 0.5)
    add(v1, v2, s_phone_chat, "cut", mode="online")
    add(v2, v3, s_leave, "fade", 0.4)
    add(v3, v4, s_rain_walk, "fade", 0.4)
    add(v4, BRK, s_cross_city, "whip", 0.35)
    # BREAK + PRE-HOOK 2 (hope)
    add(BRK, PRE2, s_stop, "fade", 0.4)
    h1 = snap(PRE2 + 5.5 * bar)
    add(PRE2, h1, s_run, "fade", 0.4)
    add(h1, BRK2, s_hands, "memory", 0.6)
    add(BRK2, CH2, s_shatter, "white", 0.1)
    # FINAL CHORUS
    f1 = snap(CH2 + 2 * bar)
    add(CH2, f1, s_title, "white", 0.12, variant=2)
    f2 = snap(f1 + 6 * bar)
    shots = []
    seq = [(s_memory_walk, 1.0), (s_present_alone, 2.5), (s_her_smile, 1.5), (s_phone_chat, 2.0),
           (s_memory_evening, 2.0), (s_eyes, 2.0), (s_memory_eyes, 0.8), (s_separated, 3.0),
           (s_orbit, 2.0), (s_room, 1.0), (s_her_smile, 2.5), (s_window_rain, 1.0)]
    x = 0.0
    for fn, off in seq:
        if x >= f2 - f1 - 0.3:
            break
        shots.append((x, fn, off))
        x = snap(f1 + x + bar) - f1
    add(f1, f2, s_montage, "cut", shots=shots)
    f3 = snap(f2 + 3.5 * bar)
    add(f2, f3, s_skate_away, "white", 0.15)
    add(f3, OUTRO, s_watch, "fade", 0.5)
    # OUTRO
    o1 = snap(OUTRO + 4.5 * bar)
    o2 = min(dur - 2.0, snap(o1 + 2.5 * bar))
    add(OUTRO, o1, s_dawn_bench, "fade", 1.0)
    add(o1, o2, s_pullback, "fade", 0.8)
    add(o2, dur + 1.0, s_end, "cut")
    return S
