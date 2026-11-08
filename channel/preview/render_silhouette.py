"""Cinematic-silhouette version of the Hypothetica Episode 1 preview.

Solid black silhouette characters against glowing gradient skies, widescreen bars, film grain.
Usage: python3 render_silhouette.py <out_dir> [start step]
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
SS = 2                     # supersampling for smooth silhouettes
FPS = 24
BAR = 78                   # letterbox bar height
AMBER = (255, 176, 64)
SIL = (8, 8, 12)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DURATION = 36.0


# ---------------------------------------------------------------- helpers
def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def fade(t, a, b, f=0.4):
    return ease((t - a) / f) * ease((b - t) / f)


def gradient(stops):
    """Vertical gradient from [(pos 0..1, (r,g,b)), ...]."""
    ys = np.linspace(0, 1, H)
    cols = np.zeros((H, 3))
    pos = [p for p, _ in stops]
    for c in range(3):
        cols[:, c] = np.interp(ys, pos, [col[c] for _, col in stops])
    arr = np.repeat(cols[:, None, :], W, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def glow(img, cx, cy, r, color, strength=1.0):
    layer = Image.new("L", (W, H), 0)
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(255 * min(1, strength)))
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.7))
    return Image.composite(Image.new("RGB", (W, H), color), img, layer)


def disc(img, cx, cy, r, color, alpha=1.0):
    m = Image.new("L", (W * SS, H * SS), 0)
    ImageDraw.Draw(m).ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=int(255 * alpha))
    img.paste(color, (0, 0), m.resize((W, H), Image.LANCZOS))


class Mask:
    """Supersampled silhouette mask; draw in 1x coordinates."""

    def __init__(self):
        self.m = Image.new("L", (W * SS, H * SS), 0)
        self.d = ImageDraw.Draw(self.m)

    def line(self, pts, w, fill=255):
        p = [(x * SS, y * SS) for x, y in pts]
        self.d.line(p, fill=fill, width=int(w * SS), joint="curve")
        for x, y in p:  # round caps
            r = w * SS / 2
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def circle(self, cx, cy, r, fill=255):
        self.d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=fill)

    def poly(self, pts, fill=255):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)

    def rect(self, x1, y1, x2, y2, fill=255):
        self.d.rectangle([x1 * SS, y1 * SS, x2 * SS, y2 * SS], fill=fill)

    def paste(self, img, color=SIL, alpha=1.0, blur=0):
        m = self.m.resize((W, H), Image.LANCZOS)
        if blur:
            m = m.filter(ImageFilter.GaussianBlur(blur))
        if alpha < 1:
            m = m.point(lambda v: int(v * alpha))
        img.paste(color, (0, 0), m)


def limb(m, x, y, a1, a2, l1, l2, w):
    """Two-segment limb from (x,y); angles in degrees from straight down."""
    kx = x + l1 * math.sin(math.radians(a1))
    ky = y + l1 * math.cos(math.radians(a1))
    ex = kx + l2 * math.sin(math.radians(a2))
    ey = ky + l2 * math.cos(math.radians(a2))
    m.line([(x, y), (kx, ky), (ex, ey)], w)
    return ex, ey


def wren(m, x, y, s=1.0, walk=None, sit=False, wind=0.0):
    """Wren silhouette: stick-figure proportions, square glasses + scarf tail. (x,y) = feet."""
    lw = 9 * s
    hip_y = y - 92 * s if not sit else y - 40 * s
    neck_y = hip_y - 78 * s
    head_r = 30 * s
    # legs
    if sit:
        limb(m, x, hip_y, 80, 10, 50 * s, 44 * s, lw)
        limb(m, x, hip_y, 70, 5, 50 * s, 44 * s, lw)
    else:
        ph = walk if walk is not None else 0
        sw = 28 if walk is not None else 6
        for sgn in (1, -1):
            a = sgn * sw * math.sin(ph) if walk is not None else sgn * 9
            knee = a - max(0, sgn * math.cos(ph)) * 22 if walk is not None else sgn * 4
            limb(m, x, hip_y, a, knee, 48 * s, 46 * s, lw)
    # torso
    m.line([(x, hip_y), (x + 3 * s, neck_y)], lw * 1.15)
    # arms
    ph = walk if walk is not None else 0
    for sgn in (1, -1):
        if sit:
            limb(m, x + 3 * s, neck_y + 8 * s, 40, 75, 38 * s, 36 * s, lw * 0.9)
        else:
            a = sgn * (26 * math.sin(ph) if walk is not None else 0) + sgn * 10
            limb(m, x + 3 * s, neck_y + 8 * s, a, a + sgn * 14 - 6, 40 * s, 38 * s, lw * 0.9)
    # head
    hx, hy = x + 5 * s, neck_y - head_r - 2 * s
    m.circle(hx, hy, head_r)
    # square glasses sticking out of the profile + scarf
    m.rect(hx + head_r - 6 * s, hy - 6 * s, hx + head_r + 7 * s, hy + 3 * s)
    m.line([(x - 8 * s, neck_y + 4 * s), (x + 14 * s, neck_y + 4 * s)], 8 * s)
    flap = math.sin(wind * 3.1) * 8
    m.poly([(x - 6 * s, neck_y), (x - 44 * s, neck_y + (10 + flap) * s), (x - 52 * s, neck_y + (2 + flap) * s),
            (x - 40 * s, neck_y + (-4 + flap * 0.6) * s), (x - 6 * s, neck_y + 10 * s)])
    return hx, hy, head_r


# ---------------------------------------------------------------- static layers
rng = random.Random(3)
GRAIN = [Image.effect_noise((W, H), 40).convert("L") for _ in range(4)]

SKY_DUSK = gradient([(0, (18, 20, 48)), (0.45, (120, 54, 78)), (0.72, (240, 128, 70)), (1, (255, 200, 120))])
SKY_HOME = gradient([(0, (40, 22, 18)), (0.6, (170, 92, 48)), (1, (230, 160, 90))])
SKY_DAWN = gradient([(0, (60, 96, 150)), (0.55, (230, 170, 140)), (1, (255, 214, 160))])
SKY_NIGHT = gradient([(0, (4, 6, 18)), (0.6, (16, 22, 52)), (1, (38, 40, 80))])
SKY_TITLE = gradient([(0, (6, 6, 10)), (1, (22, 18, 16))])

STARS = [(rng.uniform(0, W), rng.uniform(BAR, H * 0.6), rng.uniform(0.6, 1.8), rng.uniform(0, 6.28)) for _ in range(220)]


def hills(m, base, amp, seed, freq=1.0):
    r = random.Random(seed)
    ph = [r.uniform(0, 6.28) for _ in range(3)]
    pts = [(0, H)]
    for x in range(0, W + 20, 20):
        y = base - amp * (0.6 * math.sin(x / 260 * freq + ph[0]) + 0.3 * math.sin(x / 110 * freq + ph[1])
                          + 0.1 * math.sin(x / 40 + ph[2]))
        pts.append((x, y))
    pts.append((W, H))
    m.poly(pts)


def skyline(m, base, seed, scroll=0.0):
    r = random.Random(seed)
    x = -200
    while x < W + 400:
        bw, bh = r.randint(50, 130), r.randint(80, 300)
        xx = x - scroll % 400
        m.rect(xx, base - bh, xx + bw, base)
        if r.random() < 0.3:
            m.rect(xx + bw / 2 - 3, base - bh - 40, xx + bw / 2 + 3, base - bh)
        x += bw + r.randint(4, 30)


def tree(m, x, base, s=1.0):
    m.line([(x, base), (x, base - 120 * s)], 14 * s)
    for i, (dx, dy, r) in enumerate([(0, -160, 60), (-45, -130, 45), (45, -130, 45), (0, -205, 40)]):
        m.circle(x + dx * s, base + dy * s, r * s)


# ---------------------------------------------------------------- scenes
def sc_dot(t):
    img = SKY_TITLE.copy()
    a = fade(t, 0.3, 4.4, 0.6)
    pulse = 0.85 + 0.15 * math.sin(t * 4)
    img = glow(img, 640, 340, 60 * pulse, AMBER, 0.9 * a)
    disc(img, 640, 340, 5 + 2 * pulse, (255, 240, 200), a)
    return img


def sc_tray(t):
    img = SKY_HOME.copy()
    img = glow(img, 980, 230, 140, (255, 210, 140), 0.8)
    m = Mask()
    m.rect(0, 520, W, H)                                   # table
    # window frame
    m.rect(820, 90, 832, 420); m.rect(1128, 90, 1140, 420); m.rect(820, 250, 1140, 262); m.rect(820, 90, 1140, 102)
    m.rect(970, 90, 982, 420); m.rect(800, 410, 1160, 426)
    # tray with food on it
    m.poly([(360, 520), (390, 500), (890, 500), (920, 520)])
    m.circle(470, 462, 40); m.line([(470, 422), (482, 398)], 6)                   # apple
    m.poly([(560, 500), (700, 500), (630, 420)])                                   # sandwich
    m.rect(750, 410, 820, 500); m.poly([(750, 410), (785, 380), (820, 410)])      # milk carton
    blur = 18 * ease((t - 7.4) / 1.6)
    m.paste(img, alpha=1 - 0.75 * ease((t - 7.4) / 1.8), blur=blur)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur * 0.5))
    return img


def sc_wren(t):
    img = SKY_DUSK.copy()
    img = glow(img, 640, 470, 260, (255, 190, 110), 0.9)
    disc(img, 640, 470, 150, (255, 222, 160))
    m = Mask()
    hills(m, 560, 30, 11)
    rise = ease((t - 9.4) / 2.2)
    x, y = 640, 560 + (1 - rise) * 40
    hx, hy, hr = wren(m, x, y, 1.6, wind=t)
    tree(m, 230, 600, 1.4)
    m.paste(img)
    if t > 12.8:  # the memory spark: glasses light up amber
        f = (0.6 + 0.4 * math.sin(t * 8) * math.sin(t * 2.9)) * ease((t - 12.8) / 0.6)
        img = glow(img, hx + hr + 1, hy - 2, 28, AMBER, f)
        disc(img, hx + hr + 1, hy - 1.5, 6, (255, 220, 150), f)
    return img


def sc_title(t):
    img = SKY_TITLE.copy()
    a = fade(t, 18.0, 22.4, 0.5)
    img = glow(img, 640, 330, 300, (70, 46, 20), a)
    txt = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(txt)
    spacing = 24 - 10 * ease((t - 18) / 4)
    font = ImageFont.truetype(FONT_BOLD, 76)
    word = "HYPOTHETICA"
    widths = [d.textlength(c, font=font) for c in word]
    x = 640 - (sum(widths) + spacing * (len(word) - 1)) / 2
    for c, w_ in zip(word, widths):
        d.text((x, 330), c, font=font, fill=int(255 * a), anchor="lm")
        x += w_ + spacing
    img.paste((245, 240, 230), (0, 0), txt)
    sub = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sub).text((640, 405), "EPISODE 1  ·  NEVER FORGET", font=ImageFont.truetype(FONT_REG, 26),
                             fill=int(255 * fade(t, 18.8, 22.4, 0.5)), anchor="mm")
    img.paste(AMBER, (0, 0), sub)
    return img


def sc_street(t):
    img = SKY_DAWN.copy()
    img = glow(img, 300, 380, 200, (255, 236, 200), 0.7)
    back = Mask(); skyline(back, 470, 5, scroll=(t - 22.6) * 8); back.paste(img, (96, 92, 120))
    mid = Mask(); skyline(mid, 500, 9, scroll=(t - 22.6) * 18); mid.paste(img, (52, 48, 70))
    m = Mask()
    m.rect(0, 520, W, H)                                   # street
    # street lamp
    m.line([(1180, 520), (1180, 300), (1140, 290)], 8); m.poly([(1120, 288), (1160, 288), (1150, 302), (1130, 302)])
    # parked car
    cx = 900
    m.poly([(cx - 150, 510), (cx - 150, 470), (cx - 80, 462), (cx - 40, 418), (cx + 70, 418), (cx + 110, 462),
            (cx + 160, 468), (cx + 160, 510)])
    m.circle(cx - 90, 512, 26); m.circle(cx + 100, 512, 26)
    wx = 140 + (t - 22.6) * 82
    wren(m, wx, 520, 1.05, walk=t * 6.2, wind=t)
    m.paste(img)
    # amber "noticing" rings
    rings = [(24.0, (cx + 5, 490, 36)), (24.7, (cx - 40, 440, 90)), (25.4, (1140, 296, 30)), (26.1, (520, 470, 60))]
    for when, (rx, ry, rr) in rings:
        if t > when:
            k = ease((t - when) / 0.35)
            ring = Image.new("L", (W * SS, H * SS), 0)
            R = rr * (1.4 - 0.4 * k)
            ImageDraw.Draw(ring).ellipse([(rx - R) * SS, (ry - R) * SS, (rx + R) * SS, (ry + R) * SS],
                                         outline=int(235 * k), width=4 * SS)
            ring = ring.resize((W, H), Image.LANCZOS)
            img = Image.composite(Image.new("RGB", (W, H), AMBER), img, ring.filter(ImageFilter.GaussianBlur(4)))
            img.paste(AMBER, (0, 0), ring)
    if t > 23.0:  # small plate tag text
        tag = Image.new("L", (W, H), 0)
        ImageDraw.Draw(tag).text((cx + 5, 440), "7KX-219", font=ImageFont.truetype(FONT_BOLD, 18),
                                 fill=int(255 * ease((t - 24.2) / 0.4)), anchor="mm")
        img.paste(AMBER, (0, 0), tag)
    return img


def memory_card(m, x, y, kind):
    m.rect(x - 44, y - 32, x + 44, y + 32, fill=255)
    m.rect(x - 38, y - 26, x + 38, y + 26, fill=0)
    if kind == 0:
        m.circle(x, y, 16); m.circle(x, y, 12, fill=0); m.line([(x, y - 9), (x, y), (x + 7, y + 4)], 3)
    elif kind == 1:
        m.circle(x, y + 3, 14); m.line([(x, y - 11), (x + 5, y - 20)], 3)
    elif kind == 2:
        m.poly([(x - 28, y + 12), (x - 28, y + 2), (x - 12, y), (x - 5, y - 10), (x + 14, y - 10), (x + 20, y),
                (x + 28, y + 2), (x + 28, y + 12)])
    elif kind == 3:
        m.circle(x, y - 6, 9); m.line([(x, y + 3), (x, y + 16)], 5)
    else:
        m.poly([(x - 18, y + 16), (x - 18, y - 2), (x, y - 18), (x + 18, y - 2), (x + 18, y + 16)])


def sc_night(t):
    img = SKY_NIGHT.copy()
    sd = ImageDraw.Draw(img)
    for sx, sy, r, ph in STARS:
        b = int(150 + 100 * math.sin(t * 2 + ph))
        sd.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(b, b, min(255, b + 20)))
    img = glow(img, 1040, 170, 50, (220, 225, 255), 0.7)
    disc(img, 1040, 170, 34, (235, 236, 245))
    p = ease((t - 27.8) / 2.0)
    # floating amber memories, flowing out of Wren's head
    cards = Mask()
    for i in range(10):
        k = ((t - 27.8) * 0.18 + i / 10) % 1
        x = 560 - 520 * k + 40 * math.sin(i * 1.7)
        y = 360 - 230 * k - 40 * math.sin(k * 3 + i)
        if k * 10 < p * 10:
            memory_card(cards, x, y, i % 5)
    trail = cards.m.resize((W, H), Image.LANCZOS)
    img = Image.composite(Image.new("RGB", (W, H), AMBER), img, trail.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.8)))
    img.paste((255, 205, 120), (0, 0), trail)
    m = Mask()
    hills(m, 560, 50, 21, 0.8)
    hx, hy, hr = wren(m, 620, 548, 1.2, sit=True, wind=t * 0.5)
    tree(m, 1000, 590, 1.6)
    m.paste(img)
    img = glow(img, hx + hr, hy - 2, 24, AMBER, 0.8 * p)
    return img


def sc_end(t):
    img = SKY_TITLE.copy()
    a = ease((t - 33.0) / 0.8)
    img = glow(img, 640, 330, 220, (90, 56, 16), a)
    tx = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(tx)
    d.text((640, 325), "NEVER FORGET", font=ImageFont.truetype(FONT_BOLD, 80), fill=int(255 * a), anchor="mm")
    img.paste(AMBER, (0, 0), tx)
    sub = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sub).text((640, 405), "full episode coming soon  ·  Hypothetica",
                             font=ImageFont.truetype(FONT_REG, 24), fill=int(210 * a), anchor="mm")
    img.paste((235, 230, 220), (0, 0), sub)
    return img


SCENES = [(0.0, 4.4, sc_dot), (4.4, 9.4, sc_tray), (9.4, 17.8, sc_wren), (17.8, 22.6, sc_title),
          (22.6, 27.6, sc_street), (27.6, 33.0, sc_night), (33.0, DURATION, sc_end)]
XF = 0.5  # crossfade seconds

CAPTIONS = [
    (0.6, 4.0, "What's the first thing you ever remember?"),
    (4.6, 9.0, "Now... what did you have for lunch eleven days ago?"),
    (9.6, 12.6, "Gone, right? Your brain threw it away."),
    (12.8, 17.4, "But what if it didn't? What if you never forgot anything, ever again?"),
    (22.8, 27.4, "Wren notices every license plate. Every crack in the sidewalk."),
    (27.8, 32.6, "And that night... every second is still there."),
]


def frame(t, idx):
    img = None
    for i, (a, b, fn) in enumerate(SCENES):
        if a <= t < b:
            img = fn(t)
            if i + 1 < len(SCENES) and t > b - XF:
                img = Image.blend(img, SCENES[i + 1][2](t), ease((t - (b - XF)) / XF))
            break
    if img is None:
        img = SCENES[-1][2](t)
    # slow push-in for a cinematic feel
    z = 1.0 + 0.03 * ((t * 0.25) % 1)
    if z > 1.001:
        cw, ch = W / z, H / z
        img = img.crop(((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)).resize((W, H), Image.BICUBIC)
    # film grain
    g = GRAIN[idx % 4]
    img = Image.blend(img, Image.merge("RGB", [g, g, g]), 0.045)
    # letterbox + captions
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, BAR], fill=(0, 0, 0)); d.rectangle([0, H - BAR, W, H], fill=(0, 0, 0))
    font = ImageFont.truetype(FONT_REG, 27)
    for a, b, text in CAPTIONS:
        al = fade(t, a, b, 0.3)
        if al > 0:
            layer = Image.new("L", (W, H), 0)
            ImageDraw.Draw(layer).text((W / 2, H - BAR / 2), text, font=font, fill=int(255 * al), anchor="mm")
            img.paste((240, 236, 226), (0, 0), layer)
    gf = ease(t / 0.5) * ease((DURATION - t) / 0.8)
    if gf < 1:
        img = Image.blend(Image.new("RGB", (W, H)), img, gf)
    return img


def main():
    out = os.path.join(sys.argv[1], "frames")
    os.makedirs(out, exist_ok=True)
    start, step = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1)
    for i in range(start, int(DURATION * FPS), step):
        frame(i / FPS, i).save(os.path.join(out, f"f{i:05d}.png"), compress_level=1)


if __name__ == "__main__":
    main()
