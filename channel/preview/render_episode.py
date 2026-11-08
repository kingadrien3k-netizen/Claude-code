"""Full voiceless Episode 1 of Hypothetica: "What If You Could Never Forget Anything?"

Story told with on-screen text over cinematic silhouette animation + generated ambient score.
Usage:
  python3 render_episode.py frames <out_dir> [start step]
  python3 render_episode.py music <out.wav>
  python3 render_episode.py still <t> <out.png>
"""
import math
import os
import random
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from render_silhouette import (AMBER, BAR, FONT_BOLD, FONT_REG, FPS, GRAIN, H, SIL, SKY_DAWN, SKY_DUSK,
                               SKY_HOME, SKY_NIGHT, SKY_TITLE, SS, STARS, W, Mask, disc, ease, fade, glow,
                               gradient, hills, limb, memory_card, skyline, tree)

RED = (196, 38, 44)
CAPTION_FONT = ImageFont.truetype(FONT_REG, 29)
CAPTION_BOLD = ImageFont.truetype(FONT_BOLD, 29)


# ---------------------------------------------------------------- characters
def person(m, x, y, s=1.0, walk=None, sit=False, arms=None, wind=0.0, wren=True, face=1):
    """Silhouette figure. (x,y) = feet. arms=(left_deg, right_deg) from straight down (positive = forward).
    wren=True adds square glasses + scarf; False draws a long-haired figure in a coat."""
    lw = 9 * s
    hip_y = y - 92 * s if not sit else y - 40 * s
    neck_y = hip_y - 78 * s
    head_r = 30 * s
    if sit:
        limb(m, x, hip_y, 80 * face, 10 * face, 50 * s, 44 * s, lw)
        limb(m, x, hip_y, 70 * face, 5 * face, 50 * s, 44 * s, lw)
    else:
        for sgn in (1, -1):
            if walk is not None:
                a = sgn * 28 * math.sin(walk)
                knee = a - max(0, sgn * math.cos(walk)) * 22
            else:
                a, knee = sgn * 9, sgn * 4
            limb(m, x, hip_y, a * face, knee * face, 48 * s, 46 * s, lw)
    m.line([(x, hip_y), (x + 3 * s * face, neck_y)], lw * 1.15)
    if not wren:  # coat
        m.poly([(x - 16 * s, neck_y + 10 * s), (x + 18 * s, neck_y + 10 * s), (x + 30 * s, hip_y + 30 * s),
                (x - 28 * s, hip_y + 30 * s)])
    for i, sgn in enumerate((1, -1)):
        if arms is not None:
            a = arms[i]
            limb(m, x + 3 * s * face, neck_y + 8 * s, a * face, a * face * 0.85, 40 * s, 38 * s, lw * 0.9)
        elif sit:
            limb(m, x + 3 * s * face, neck_y + 8 * s, 40 * face, 75 * face, 38 * s, 36 * s, lw * 0.9)
        else:
            a = sgn * (26 * math.sin(walk) if walk is not None else 0) + sgn * 10
            limb(m, x + 3 * s * face, neck_y + 8 * s, a, a + sgn * 14 - 6, 40 * s, 38 * s, lw * 0.9)
    hx, hy = x + 5 * s * face, neck_y - head_r - 2 * s
    m.circle(hx, hy, head_r)
    if wren:
        gx = hx + (head_r - 6 * s) * face
        m.rect(min(gx, gx + 13 * s * face), hy - 6 * s, max(gx, gx + 13 * s * face), hy + 3 * s)
        m.line([(x - 8 * s, neck_y + 4 * s), (x + 14 * s, neck_y + 4 * s)], 8 * s)
        flap = math.sin(wind * 3.1) * 8
        bx = -face
        m.poly([(x + 6 * s * bx, neck_y), (x + 44 * s * bx, neck_y + (10 + flap) * s),
                (x + 52 * s * bx, neck_y + (2 + flap) * s), (x + 40 * s * bx, neck_y + (-4 + flap * 0.6) * s),
                (x + 6 * s * bx, neck_y + 10 * s)])
    else:  # long hair
        m.poly([(hx - 28 * s * face, hy - 14 * s), (hx - 40 * s * face, hy + 52 * s), (hx - 8 * s * face, hy + 44 * s),
                (hx + 4 * s * face, hy - 26 * s)])
    return hx, hy, head_r


def umbrella(img, x, y, s=1.0, color=RED):
    """Canopy centred at (x,y); returns img."""
    m = Mask()
    r = 62 * s
    m.d.pieslice([(x - r) * SS, (y - r * 0.8) * SS, (x + r) * SS, (y + r * 0.8) * SS], 180, 360, fill=255)
    for k in range(4):  # scalloped edge
        cx = x - r + r / 4 + k * r / 2
        m.circle(cx, y, r / 4, fill=0)
    m.paste(img, color)
    h = Mask()
    h.line([(x, y - r * 0.8), (x, y + 70 * s)], 4 * s)
    h.paste(img)


# ---------------------------------------------------------------- scenes  (u = local time, d = duration)
rng = random.Random(42)


def sc_dot(u, d):
    img = SKY_TITLE.copy()
    a = fade(u, 0.2, d - 0.1, 0.6)
    p = 0.85 + 0.15 * math.sin(u * 4)
    img = glow(img, 640, 340, 60 * p, AMBER, 0.9 * a)
    disc(img, 640, 340, 5 + 2 * p, (255, 240, 200), a)
    return img


def sc_tray(u, d):
    img = SKY_HOME.copy()
    img = glow(img, 980, 230, 140, (255, 210, 140), 0.8)
    m = Mask()
    m.rect(0, 520, W, H)
    for r in [(820, 90, 832, 420), (1128, 90, 1140, 420), (820, 250, 1140, 262), (820, 90, 1140, 102),
              (970, 90, 982, 420), (800, 410, 1160, 426)]:
        m.rect(*r)
    m.poly([(360, 520), (390, 500), (890, 500), (920, 520)])
    m.circle(470, 462, 40); m.line([(470, 422), (482, 398)], 6)
    m.poly([(560, 500), (700, 500), (630, 420)])
    m.rect(750, 410, 820, 500); m.poly([(750, 410), (785, 380), (820, 410)])
    k = ease((u - d * 0.55) / (d * 0.35))
    m.paste(img, alpha=1 - 0.75 * k, blur=18 * k)
    if k:
        img = img.filter(ImageFilter.GaussianBlur(9 * k))
    return img


def sc_sunset(u, d):
    img = SKY_DUSK.copy()
    img = glow(img, 640, 470, 260, (255, 190, 110), 0.9)
    disc(img, 640, 470, 150, (255, 222, 160))
    m = Mask()
    hills(m, 560, 30, 11)
    rise = ease(u / 2.2)
    hx, hy, hr = person(m, 640, 560 + (1 - rise) * 40, 1.6, wind=u)
    tree(m, 230, 600, 1.4)
    m.paste(img)
    if u > d * 0.4:
        f = (0.6 + 0.4 * math.sin(u * 8) * math.sin(u * 2.9)) * ease((u - d * 0.4) / 0.6)
        img = glow(img, hx + hr + 1, hy - 2, 28, AMBER, f)
        disc(img, hx + hr + 1, hy - 1.5, 6, (255, 220, 150), f)
    return img


def sc_title(u, d):
    img = SKY_TITLE.copy()
    a = fade(u, 0.1, d - 0.1, 0.6)
    img = glow(img, 640, 330, 300, (70, 46, 20), a)
    txt = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(txt)
    spacing = 24 - 10 * ease(u / d)
    font = ImageFont.truetype(FONT_BOLD, 76)
    word = "HYPOTHETICA"
    widths = [dr.textlength(c, font=font) for c in word]
    x = 640 - (sum(widths) + spacing * (len(word) - 1)) / 2
    for c, w_ in zip(word, widths):
        dr.text((x, 330), c, font=font, fill=int(255 * a), anchor="lm")
        x += w_ + spacing
    img.paste((245, 240, 230), (0, 0), txt)
    sub = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sub).text((640, 405), "EPISODE 1  ·  NEVER FORGET", font=ImageFont.truetype(FONT_REG, 26),
                             fill=int(255 * fade(u, 0.8, d - 0.1, 0.6)), anchor="mm")
    img.paste(AMBER, (0, 0), sub)
    return img


def sc_bedroom(u, d):
    img = gradient([(0, (200, 170, 150)), (1, (255, 220, 180))])   # dawn through window
    wall = Mask()
    wall.rect(0, 0, W, 100); wall.rect(0, 0, 760, H); wall.rect(1040, 0, W, H); wall.rect(0, 430, W, H)
    wall.rect(890, 100, 902, 430); wall.rect(760, 260, 1040, 272)
    wall.paste(img, (58, 56, 78))
    img = glow(img, 880, 380, 330, (190, 150, 130), 0.55)              # light spilling into the room
    m = Mask()
    m.rect(0, 600, W, H)                                                # floor
    m.rect(890, 100, 902, 430); m.rect(760, 260, 1040, 272); m.rect(740, 422, 1060, 436)
    m.rect(140, 470, 640, 540); m.rect(130, 380, 160, 600); m.rect(620, 470, 650, 600)
    m.rect(690, 500, 760, 600); m.rect(700, 470, 750, 500)
    if u < d * 0.45:
        m.circle(210, 448, 26); m.line([(240, 462), (560, 462)], 18)
    else:
        person(m, 300, 500, 1.0, sit=True)
    m.paste(img)
    blink = 1 if (u * 2) % 2 < 1.4 else 0.35
    t = Image.new("L", (W, H), 0)
    ImageDraw.Draw(t).text((725, 485), "7:02", font=ImageFont.truetype(FONT_BOLD, 17), fill=int(255 * blink), anchor="mm")
    img.paste(AMBER, (0, 0), t)
    return img


def sc_street(u, d):
    img = SKY_DAWN.copy()
    img = glow(img, 300, 380, 200, (255, 236, 200), 0.7)
    b = Mask(); skyline(b, 470, 5, scroll=u * 8); b.paste(img, (96, 92, 120))
    mid = Mask(); skyline(mid, 500, 9, scroll=u * 18); mid.paste(img, (52, 48, 70))
    m = Mask()
    m.rect(0, 520, W, H)
    m.line([(1180, 520), (1180, 300), (1140, 290)], 8); m.poly([(1120, 288), (1160, 288), (1150, 302), (1130, 302)])
    cx = 900
    m.poly([(cx - 150, 510), (cx - 150, 470), (cx - 80, 462), (cx - 40, 418), (cx + 70, 418), (cx + 110, 462),
            (cx + 160, 468), (cx + 160, 510)])
    m.circle(cx - 90, 512, 26); m.circle(cx + 100, 512, 26)
    # stranger on phone
    person(m, 1060, 520, 0.95, wren=False, arms=(10, 150), face=-1)
    wx = 80 + u * 52
    person(m, wx, 520, 1.05, walk=u * 6.2, wind=u)
    m.paste(img)
    rings = [(0.45, (cx + 5, 490, 36), "7KX-219"), (0.55, (cx - 40, 440, 90), None),
             (0.65, (1040, 340, 40), "\"...by Friday, okay?\""), (0.75, (520, 470, 60), None)]
    for frac, (rx, ry, rr), label in rings:
        when = d * frac
        if u > when:
            k = ease((u - when) / 0.35)
            ring = Image.new("L", (W * SS, H * SS), 0)
            R = rr * (1.4 - 0.4 * k)
            ImageDraw.Draw(ring).ellipse([(rx - R) * SS, (ry - R) * SS, (rx + R) * SS, (ry + R) * SS],
                                         outline=int(235 * k), width=4 * SS)
            ring = ring.resize((W, H), Image.LANCZOS)
            img = Image.composite(Image.new("RGB", (W, H), AMBER), img, ring.filter(ImageFilter.GaussianBlur(4)))
            img.paste(AMBER, (0, 0), ring)
            if label:
                tg = Image.new("L", (W, H), 0)
                ImageDraw.Draw(tg).text((rx, ry - rr - 14), label, font=ImageFont.truetype(FONT_BOLD, 17),
                                        fill=int(255 * k), anchor="mm")
                img.paste(AMBER, (0, 0), tg)
    return img


def night_base(u):
    img = SKY_NIGHT.copy()
    sd = ImageDraw.Draw(img)
    for sx, sy, r, ph in STARS:
        b = int(150 + 100 * math.sin(u * 2 + ph))
        sd.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(b, b, min(255, b + 20)))
    img = glow(img, 1040, 170, 50, (220, 225, 255), 0.7)
    disc(img, 1040, 170, 34, (235, 236, 245))
    return img


def sc_night(u, d):
    img = night_base(u)
    p = ease(u / 2.0)
    cards = Mask()
    for i in range(12):
        k = (u * 0.12 + i / 12) % 1
        x = 560 - 520 * k + 40 * math.sin(i * 1.7)
        y = 360 - 230 * k - 40 * math.sin(k * 3 + i)
        if i / 12 < p:
            memory_card(cards, x, y, i % 5)
    tr = cards.m.resize((W, H), Image.LANCZOS)
    img = Image.composite(Image.new("RGB", (W, H), AMBER), img, tr.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.8)))
    img.paste((255, 205, 120), (0, 0), tr)
    m = Mask()
    hills(m, 560, 50, 21, 0.8)
    hx, hy, hr = person(m, 620, 548, 1.2, sit=True, wind=u * 0.5)
    tree(m, 1000, 590, 1.6)
    m.paste(img)
    return glow(img, hx + hr, hy - 2, 24, AMBER, 0.8 * p)


def shelves(m):
    r = random.Random(8)
    for sx in (40, 900):
        m.rect(sx, 120, sx + 340, 132); m.rect(sx, 120, sx + 12, 560); m.rect(sx + 328, 120, sx + 340, 560)
        for row in range(4):
            y = 232 + row * 108
            m.rect(sx, y, sx + 340, y + 10)
            x = sx + 16
            while x < sx + 320:
                bw = r.randint(12, 26)
                bh = r.randint(60, 96)
                if r.random() < 0.85:
                    m.rect(x, y - bh, x + bw - 3, y)
                x += bw


def sc_books(u, d):
    img = gradient([(0, (44, 30, 22)), (1, (150, 100, 60))])
    img = glow(img, 640, 300, 260, (255, 210, 150), 0.8)
    m = Mask()
    m.rect(0, 560, W, H)
    shelves(m)
    hx, hy, hr = person(m, 640, 560, 1.25, wind=u)
    m.paste(img)
    fly = Mask()
    r = random.Random(3)
    starts = [(r.choice([200, 1070]) + r.uniform(-120, 120), r.uniform(150, 500)) for _ in range(14)]
    am = Mask()
    for i, (sx, sy) in enumerate(starts):
        k = ((u - 1.0) * 0.55 - i * 0.18)
        if 0 < k < 1:
            e = ease(k)
            x, y = sx + (hx - sx) * e, sy + (hy - sy) * e - 120 * math.sin(e * math.pi)
            ang = k * 6
            sz = 22 * (1 - 0.6 * e)
            pts = [(x + sz * math.cos(ang + a), y + sz * 0.7 * math.sin(ang + a)) for a in (0.6, 2.5, 3.7, 5.7)]
            (am if e > 0.5 else fly).poly(pts)
    fly.paste(img)
    am.paste(img, AMBER)
    return glow(img, hx + 4, hy, 40, AMBER, 0.5 + 0.3 * math.sin(u * 5) if u > 1.5 else 0)


def sc_trophy(u, d):
    img = gradient([(0, (10, 10, 16)), (1, (30, 26, 34))])
    cone = Image.new("L", (W, H), 0)
    ImageDraw.Draw(cone).polygon([(600, BAR), (680, BAR), (860, 560), (420, 560)], fill=120)
    img.paste((255, 236, 200), (0, 0), cone.filter(ImageFilter.GaussianBlur(24)))
    img = glow(img, 640, 560, 220, (255, 220, 160), 0.6)
    m = Mask()
    m.rect(0, 560, W, H)
    lift = ease((u - 0.6) / 1.0)
    hx, hy, hr = person(m, 640, 560, 1.3, arms=(10 - 170 * lift, -10 - 150 * lift))
    # trophy above raised hand
    tx, ty = 600 - 10 * lift, 450 - 210 * lift
    m.poly([(tx - 26, ty - 40), (tx + 26, ty - 40), (tx + 14, ty), (tx - 14, ty)])
    m.rect(tx - 5, ty, tx + 5, ty + 20); m.rect(tx - 16, ty + 20, tx + 16, ty + 28)
    # audience heads
    for i in range(16):
        ax = 40 + i * 80 + (i % 2) * 20
        m.circle(ax, 650 - (i % 3) * 6, 26)
    m.paste(img)
    if u > 1.4:  # confetti
        r = random.Random(5)
        cd = ImageDraw.Draw(img)
        for _ in range(90):
            x0 = r.uniform(0, W); sp = r.uniform(60, 140); ph = r.uniform(0, 6)
            y = BAR + ((u - 1.4) * sp + r.uniform(-200, 0))
            if BAR < y < 560:
                x = x0 + 14 * math.sin(u * 3 + ph)
                col = AMBER if r.random() < 0.5 else (240, 236, 226)
                cd.rectangle([x, y, x + 6, y + 10], fill=col)
    return img


def sc_card(u, d, title, lines):
    img = gradient([(0, (14, 16, 22)), (1, (30, 30, 40))])
    k = ease(u / 0.8)
    cx, cy = 640, 300 + (1 - k) * 60
    card = Image.new("L", (W, H), 0)
    ImageDraw.Draw(card).rounded_rectangle([cx - 330, cy - 150, cx + 330, cy + 150], 18, fill=int(255 * k))
    img.paste((236, 226, 204), (0, 0), card)
    tl = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(tl)
    dr.text((cx, cy - 90), title, font=ImageFont.truetype(FONT_BOLD, 40), fill=int(255 * k), anchor="mm")
    dr.line([(cx - 260, cy - 55), (cx + 260, cy - 55)], fill=int(160 * k), width=2)
    for i, ln in enumerate(lines):
        dr.text((cx, cy - 10 + i * 42), ln, font=ImageFont.truetype(FONT_REG, 26),
                fill=int(255 * ease((u - 0.8 - i * 0.5) / 0.5)), anchor="mm")
    img.paste((30, 28, 34), (0, 0), tl)
    tag = Image.new("L", (W, H), 0)
    ImageDraw.Draw(tag).text((cx - 310, cy - 128), "REAL SCIENCE", font=ImageFont.truetype(FONT_BOLD, 15),
                             fill=int(255 * k), anchor="lm")
    img.paste((190, 110, 20), (0, 0), tag)
    return img


def sc_science(u, d):
    return sc_card(u, d, "Hyperthymesia", ["Highly Superior Autobiographical Memory",
                                           "First described by researchers in 2006",
                                           "Only a few dozen confirmed cases"])


# neural tree for the "forgetting" scene
def build_branches():
    r = random.Random(12)
    segs = []

    def grow(x, y, ang, length, depth):
        if depth == 0 or length < 8:
            return
        x2, y2 = x + length * math.cos(ang), y + length * math.sin(ang)
        segs.append((x, y, x2, y2, depth, r.random()))
        for _ in range(2 if depth > 2 else r.choice([1, 2, 3])):
            grow(x2, y2, ang + r.uniform(-0.7, 0.7), length * r.uniform(0.62, 0.8), depth - 1)

    for a in range(8):
        grow(640, 330, a / 8 * 2 * math.pi + r.uniform(-0.2, 0.2), 70, 6)
    return segs


BRANCHES = build_branches()


def sc_brain(u, d):
    img = gradient([(0, (8, 10, 22)), (1, (22, 26, 48))])
    m_keep, m_amber = Mask(), Mask()
    stop = d * 0.72   # "Wren's brain stopped doing that."
    for x1, y1, x2, y2, depth, rv in BRANCHES:
        w = 1.5 + depth * 1.2
        if u < stop:
            prune = depth <= 2 and rv < 0.75
            a = 1 - ease((u - 1.5 - rv * 4) / 1.2) if prune else 1
            if a > 0.02:
                m_keep.line([(x1, y1), (x2, y2)], w, fill=int(255 * a))
        else:
            k = ease((u - stop - rv * 1.2) / 0.6)
            m_keep.line([(x1, y1), (x2, y2)], w, fill=int(255 * (1 - k)))
            m_amber.line([(x1, y1), (x2, y2)], w, fill=int(255 * k))
    blur = m_keep.m.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(8))
    img.paste((90, 140, 255), (0, 0), blur.point(lambda v: v // 2))
    m_keep.paste(img, (170, 200, 255))
    if u >= stop:
        ab = m_amber.m.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(10))
        img.paste(AMBER, (0, 0), ab.point(lambda v: v // 2))
        m_amber.paste(img, AMBER)
    return img


def bubble(m, x, y, w, h, tail_left=True):
    m.d.ellipse([(x - w / 2) * SS, (y - h / 2) * SS, (x + w / 2) * SS, (y + h / 2) * SS], fill=255)
    tx = x - w * 0.2 if tail_left else x + w * 0.2
    m.poly([(tx - 10, y + h / 2 - 8), (tx + 10, y + h / 2 - 8), (tx + (-24 if tail_left else 24), y + h / 2 + 22)])


def sc_bubbles(u, d):
    img = gradient([(0, (26, 18, 30)), (1, (70, 40, 46))])
    img = glow(img, 640, 380, 200, (180, 90, 70), 0.6)
    m = Mask()
    m.rect(0, 560, W, H)
    hx, hy, hr = person(m, 640, 560, 1.2, arms=(25, -25))
    m.paste(img)
    r = random.Random(9)
    words = ["You always...", "Why would you", "I didn't mean", "Remember when", "That was so", "...embarrassing",
             "You said that", "Never again", "Seriously?", "Why did I say", "Everyone saw", "I can't believe"]
    font = ImageFont.truetype(FONT_BOLD, 17)
    n = int(min(len(words), (u / d) * len(words) * 1.25 + 1))
    for i in range(n):
        ang = r.uniform(0, 2 * math.pi)
        rad = r.uniform(170, 330)
        x = 640 + rad * math.cos(ang) * 1.5
        y = 300 + rad * math.sin(ang) * 0.6
        x, y = min(max(x, 120), W - 120), min(max(y, BAR + 50), 500)
        pop = ease((u - i * d / len(words) / 1.25) / 0.25)
        bw, bh = 190 * pop, 64 * pop
        if bw < 4:
            continue
        b = Mask(); bubble(b, x, y, bw, bh, x > 640)
        img.paste((30, 22, 30), (0, 0), b.m.resize((W, H), Image.LANCZOS))
        o = Mask(); bubble(o, x, y, bw + 6, bh + 6, x > 640)
        ring = ImageChops_sub(o.m, b.m)
        img.paste(AMBER, (0, 0), ring.resize((W, H), Image.LANCZOS))
        t = Image.new("L", (W, H), 0)
        ImageDraw.Draw(t).text((x, y), words[i], font=font, fill=int(255 * pop), anchor="mm")
        img.paste(AMBER, (0, 0), t)
    return img


def ImageChops_sub(a, b):
    from PIL import ImageChops
    return ImageChops.subtract(a, b)


def sc_darkroom(u, d):
    img = gradient([(0, (8, 8, 12)), (1, (16, 14, 20))])
    # thin light slit between curtains
    slit = Image.new("L", (W, H), 0)
    ImageDraw.Draw(slit).rectangle([636, 110, 644, 430], fill=200)
    img.paste((255, 220, 170), (0, 0), slit.filter(ImageFilter.GaussianBlur(6)))
    beam = Image.new("L", (W, H), 0)
    ImageDraw.Draw(beam).polygon([(636, 430), (644, 430), (760, 640), (600, 640)], fill=40)
    img.paste((255, 220, 170), (0, 0), beam.filter(ImageFilter.GaussianBlur(14)))
    m = Mask()
    for side in (-1, 1):  # curtains with folds
        x0 = 640 + side * 4
        for k in range(6):
            xx = x0 + side * k * 32
            m.rect(min(xx, xx + side * 30), 100, max(xx, xx + side * 30), 470, fill=200 + (k % 2) * 55)
    m.rect(0, 560, W, H)
    hx, hy, hr = person(m, 360, 560, 1.2, sit=True)
    m.paste(img, (6, 6, 10))
    f = 0.55 + 0.25 * math.sin(u * 2.2)
    return glow(img, hx, hy, 70, AMBER, f)


def sc_fan(u, d):
    img = gradient([(0, (16, 12, 10)), (1, (40, 30, 22))])
    img = glow(img, 640, 380, 260, (90, 60, 20), 0.8)
    m, hot = Mask(), Mask()
    n = 9
    for i in range(n):
        a = math.radians(-60 + 120 * i / (n - 1)) * ease(u / 1.5)
        x = 640 + 260 * math.sin(a)
        y = 470 - 260 * math.cos(a) + 200
        (hot if i == 6 else m).rect(0, 0, 0, 0)
        memory_card(hot if i == 6 else m, x, y - 160, i % 5)
    m.paste(img, AMBER)
    pulse = ease((u - d * 0.45) / 0.6) * (0.6 + 0.4 * math.sin(u * 7))
    hm = hot.m.resize((W, H), Image.LANCZOS)
    img = Image.composite(Image.new("RGB", (W, H), (255, 220, 140)), img, hm.filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * pulse)))
    img.paste((255, 226 if pulse > 0.2 else 176, 150 if pulse > 0.2 else 64), (0, 0), hm)
    return img


def station(m, rain_phase=0.0):
    m.rect(0, 520, W, H)                                    # platform
    m.rect(0, BAR, W, 150)                                  # roof
    for x in range(60, W, 300):                             # pillars
        m.rect(x, 150, x + 22, 520)
        m.poly([(x - 30, 150), (x + 52, 150), (x + 11, 190)])
    m.line([(980, 150), (980, 200)], 4)                     # hanging clock
    m.circle(980, 228, 28)
    # train on the left
    m.poly([(0, 300), (330, 300), (380, 340), (380, 500), (0, 500)])


def rain(img, u, alpha=0.5):
    r = random.Random(1)
    layer = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(layer)
    for _ in range(260):
        x0, sp, ln = r.uniform(-100, W), r.uniform(500, 900), r.uniform(14, 30)
        y = (r.uniform(0, H) + u * sp) % H
        x = x0 + y * 0.18
        dr.line([(x, y), (x + ln * 0.18, y + ln)], fill=int(170 * alpha), width=1)
    img.paste((200, 210, 230), (0, 0), layer)


def sc_memory_station(u, d):
    img = gradient([(0, (60, 40, 20)), (1, (150, 104, 50))])
    img = glow(img, 700, 330, 300, (255, 200, 120), 0.7)
    m = Mask()
    station(m)
    person(m, 840, 520, 1.15, wren=False, arms=(40, 10), face=-1)
    m.paste(img, (40, 26, 14))
    umbrella(img, 830, 300, 1.0)
    rain(img, u, 0.35)
    # dreamy amber haze vignette
    v = Image.new("L", (W, H), 255)
    ImageDraw.Draw(v).ellipse([140, 40, W - 140, H - 40], fill=0)
    img.paste((255, 196, 110), (0, 0), v.filter(ImageFilter.GaussianBlur(70)).point(lambda p: int(p * 0.7)))
    q = Image.new("L", (W, H), 0)
    ImageDraw.Draw(q).text((640, 120 + 30), "", font=CAPTION_FONT)
    return img


def sc_black(u, d):
    img = SKY_TITLE.copy()
    k = fade(u, 0.3, d - 0.1, 0.8)
    m = Mask()
    hx, hy, hr = person(m, 640, 560, 1.4)
    m.paste(img, (24, 22, 26), alpha=k)
    return glow(img, hx + hr, hy - 2, 30, AMBER, 0.4 * k)


def sc_flip(u, d):
    img = gradient([(0, (10, 8, 8)), (1, (26, 20, 16))])
    dates = ["MAR 14, 2027", "JUL 02, 2027", "OCT 30, 2027", "JAN 09, 2028", "MAY 21, 2028", "DEC 01, 2029",
             "AUG 17, 2031", "FEB 28, 2034", "JUN 11, 2038", "SEP 05, 2041", "APR 23, 2047", "NOV 08, 2052"]
    speed = 1.2 + 6 * ease(u / d)
    idx = int(u * speed) % len(dates)
    flip = (u * speed) % 1
    sq = abs(math.cos(flip * math.pi)) if flip > 0.75 else 1
    m = Mask()
    cx, cy = 640, 310
    w2, h2 = 220, 140 * sq
    m.rect(cx - w2, cy - h2, cx + w2, cy + h2)
    m.rect(cx - w2 + 10, cy - h2 + 10, cx + w2 - 10, cy + h2 - 10, fill=0)
    img = glow(img, cx, cy, 260, (120, 70, 20), 0.7)
    m.paste(img, AMBER)
    if sq > 0.5:
        icon = Mask(); memory_card(icon, cx, cy - 30, idx % 5)
        icon.paste(img, AMBER)
        t = Image.new("L", (W, H), 0)
        ImageDraw.Draw(t).text((cx, cy + 70), dates[idx], font=ImageFont.truetype(FONT_BOLD, 34), fill=255, anchor="mm")
        img.paste((255, 220, 150), (0, 0), t)
    # clock hands spinning backwards behind
    if u > d * 0.6:
        k = ease((u - d * 0.6) / 1.0)
        ring = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(ring)
        dr.ellipse([cx - 330, cy - 230, cx + 330, cy + 230], outline=int(110 * k), width=3)
        ang = -u * 4
        dr.line([(cx, cy), (cx + 300 * math.cos(ang), cy + 210 * math.sin(ang))], fill=int(110 * k), width=3)
        img.paste(AMBER, (0, 0), ring)
    return img


def sc_station_real(u, d):
    img = gradient([(0, (36, 42, 60)), (1, (96, 104, 124))])
    img = glow(img, 640, 300, 280, (200, 210, 230), 0.5)
    m = Mask()
    station(m)
    turn = 1 if u > d * 0.25 else -1
    hx, hy, hr = person(m, 840, 520, 1.15, wren=False, arms=(40, 10), face=turn * -1)
    wx = min(560, 300 + u * 90)
    person(m, wx, 520, 1.15, walk=u * 6 if wx < 560 else None, wind=u)
    m.paste(img)
    umbrella(img, 830 + (0 if turn < 0 else 6), 300, 1.0)
    rain(img, u, 0.55)
    return img


def sc_end(u, d):
    img = SKY_TITLE.copy()
    a = ease((u - 0.4) / 1.2)
    img = glow(img, 640, 320, 240, (90, 56, 16), a)
    tx = Image.new("L", (W, H), 0)
    ImageDraw.Draw(tx).text((640, 320), "SURPRISE.", font=ImageFont.truetype(FONT_BOLD, 92), fill=int(255 * a), anchor="mm")
    img.paste(AMBER, (0, 0), tx)
    b = ease((u - 4.0) / 1.0)
    sub = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(sub)
    dr.text((640, 430), "HYPOTHETICA", font=ImageFont.truetype(FONT_BOLD, 30), fill=int(230 * b), anchor="mm")
    dr.text((640, 472), "What should we ask next? Tell us in the comments.", font=ImageFont.truetype(FONT_REG, 22),
            fill=int(200 * b), anchor="mm")
    img.paste((235, 230, 220), (0, 0), sub)
    return img


# ---------------------------------------------------------------- story timeline
STORY = [
    (sc_dot, ["What's the first thing you ever remember?"]),
    (sc_tray, ["Now... what did you have for lunch eleven days ago?", "Gone, right? Your brain threw it away."]),
    (sc_sunset, ["But what if it didn't?", "What if, starting tomorrow, you never forgot anything. Ever again?"]),
    (sc_title, [None]),
    (sc_bedroom, ["Wren wakes up on a Tuesday.", "It feels like any other Tuesday."]),
    (sc_street, ["But on the walk to the bus, something is different.",
                 "Wren notices every license plate. Every crack in the sidewalk.",
                 "Every word of a stranger's phone call."]),
    (sc_night, ["That night, Wren tries to remember the morning...",
                "...and it's all still there. Not a summary. Every single second."]),
    (sc_books, ["At first, it's incredible.", "Wren reads a textbook once and can recite every page."]),
    (sc_trophy, ["Wren wins trivia night. Alone. Against six teams.",
                 "For three weeks, a perfect memory feels like a superpower."]),
    (sc_science, ["Here's the strange part: a few real people live with something close to this.",
                  "They can recall almost every day of their lives. And many describe it as a movie that never stops playing."]),
    (sc_brain, ["Because forgetting isn't your brain failing. It's your brain working.",
                "While you sleep, your brain weakens connections it doesn't need.",
                "Forgetting is how you learn what matters.",
                "Wren's brain stopped doing that."]),
    (sc_bubbles, ["By month two, the problems start.",
                  "Every argument. Every embarrassing moment. Replaying perfectly.",
                  "A mistake from six weeks ago feels like it happened six seconds ago."]),
    (sc_darkroom, ["Wren starts staying home. Curtains closed.",
                   "Darkness gives the memory nothing new to save.",
                   "A perfect memory keeps everything. And it never lets you choose."]),
    (sc_fan, ["Then, one Thursday, sorting through old memories...", "...Wren finds one that doesn't fit."]),
    (sc_memory_station, ["A train station. A red umbrella.", "A woman saying: \"You're late. But I knew you'd come.\""]),
    (sc_black, ["Wren has never been there. Never met her.", "The memory is perfect.", "And it hasn't happened yet."]),
    (sc_flip, ["Then another. And another.", "Memories with dates that haven't come yet.",
               "Wren's brain didn't just stop forgetting.", "It stopped caring which direction time was going."]),
    (sc_station_real, ["Three weeks later, Wren stands on that platform.",
                       "\"You're late,\" she says. \"But I knew you'd come.\"",
                       "And Wren, who remembers everything that was and everything that will be...",
                       "...finally understands the one thing a perfect memory can never give back."]),
    (sc_end, [None]),
]
SILENT_SCENE = sc_black  # music drops out here


def cap_len(text):
    if text is None:
        return 4.6
    return max(3.0, len(text) / 15 + 1.4)


def build_timeline():
    scenes, caps, t = [], [], 0.0
    for fn, lines in STORY:
        start = t
        for ln in lines:
            dur = cap_len(ln) if fn is not sc_end else 7.5
            if ln:
                caps.append((t, t + dur, ln))
            t += dur
        t += 0.6
        scenes.append((start, t, fn))
    return scenes, caps, t


SCENES, CAPTIONS, DURATION = build_timeline()
XF = 0.6


def wrap(text, font, maxw):
    words, lines, cur = text.split(), [], ""
    dr = ImageDraw.Draw(Image.new("L", (1, 1)))
    for w_ in words:
        test = (cur + " " + w_).strip()
        if dr.textlength(test, font=font) > maxw and cur:
            lines.append(cur); cur = w_
        else:
            cur = test
    lines.append(cur)
    return lines


def frame(t, idx):
    img = None
    for i, (a, b, fn) in enumerate(SCENES):
        if a <= t < b:
            img = fn(t - a, b - a)
            if i + 1 < len(SCENES) and t > b - XF:
                na, nb, nfn = SCENES[i + 1]
                img = Image.blend(img, nfn(t - na, nb - na), ease((t - (b - XF)) / XF))
            break
    if img is None:
        a, b, fn = SCENES[-1]
        img = fn(t - a, b - a)
    z = 1.0 + 0.035 * ease(((t - next(a for a, b, _ in SCENES if a <= t < b or b >= DURATION)) / 12))
    cw, ch = W / z, H / z
    img = img.crop(((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)).resize((W, H), Image.BICUBIC)
    g = GRAIN[idx % 4]
    img = Image.blend(img, Image.merge("RGB", [g, g, g]), 0.045)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, BAR], fill=(0, 0, 0)); d.rectangle([0, H - BAR, W, H], fill=(0, 0, 0))
    for a, b, text in CAPTIONS:
        al = fade(t, a, b, 0.35)
        if al > 0:
            layer = Image.new("L", (W, H), 0)
            ld = ImageDraw.Draw(layer)
            lines = wrap(text, CAPTION_FONT, 1000)
            y0 = H - BAR / 2 - (len(lines) - 1) * 16
            for j, ln in enumerate(lines):
                ld.text((W / 2, y0 + j * 32), ln, font=CAPTION_FONT, fill=int(255 * al), anchor="mm")
            img.paste((244, 240, 230), (0, 0), layer)
    gf = ease(t / 0.6) * ease((DURATION - t) / 1.2)
    if gf < 1:
        img = Image.blend(Image.new("RGB", (W, H)), img, gf)
    return img


# ---------------------------------------------------------------- soundtrack
def music(path, sr=44100):
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    out = np.zeros(n)
    # A minor -> F -> C -> G, 8 s per chord
    chords = [[110.0, 164.81, 220.0, 261.63], [87.31, 174.61, 220.0, 261.63],
              [130.81, 196.0, 261.63, 329.63], [98.0, 196.0, 246.94, 293.66]]
    seg = 8.0
    for ci in range(int(DURATION / seg) + 1):
        notes = chords[ci % 4]
        s0 = ci * seg
        idx = (t >= s0 - 1) & (t < s0 + seg + 1.5)
        tt = t[idx] - s0
        env = np.clip((tt + 1) / 2.5, 0, 1) * np.clip((seg + 1.5 - tt) / 2.5, 0, 1)
        sig = np.zeros_like(tt)
        for f in notes:
            sig += np.sin(2 * np.pi * f * t[idx]) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t[idx])
        out[idx] += 0.035 * env * sig
    # soft bell arpeggio
    rng_ = np.random.default_rng(4)
    for bi in range(int(DURATION / 2)):
        s0 = bi * 2.0 + 0.5
        chord = chords[int(s0 / seg) % 4]
        f = chord[rng_.integers(1, 4)] * 2
        i0 = int(s0 * sr)
        ln = int(2.5 * sr)
        tt = np.arange(min(ln, n - i0)) / sr
        out[i0:i0 + len(tt)] += 0.05 * np.exp(-tt * 1.6) * np.sin(2 * np.pi * f * tt) * (1 - np.exp(-tt * 80))
    # silence for the twist, then a low drone into the reveal
    for a, b, fn in SCENES:
        if fn is SILENT_SCENE:
            gate = np.clip((a + 0.2 - t) / 1.2, 0, 1) + np.clip((t - b + 0.6) / 1.5, 0, 1)
            out *= np.clip(gate, 0, 1)
        if fn is sc_flip:
            m = (t >= a) & (t < b)
            tt = t[m] - a
            out[m] += 0.06 * np.clip(tt / 3, 0, 1) * np.sin(2 * np.pi * 55 * t[m]) * (1 + 0.3 * np.sin(2 * np.pi * 0.5 * tt))
    out *= np.clip(t / 3, 0, 1) * np.clip((DURATION - t) / 4, 0, 1)
    out = np.tanh(out * 1.4) * 0.6
    data = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(data.tobytes())


def main():
    mode = sys.argv[1]
    if mode == "music":
        music(sys.argv[2])
    elif mode == "still":
        t = float(sys.argv[2])
        frame(t, 0).save(sys.argv[3])
    else:
        out = os.path.join(sys.argv[2], "frames")
        os.makedirs(out, exist_ok=True)
        start, step = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 1)
        for i in range(start, int(DURATION * FPS), step):
            frame(i / FPS, i).save(os.path.join(out, f"f{i:05d}.png"), compress_level=1)


if __name__ == "__main__":
    main()
