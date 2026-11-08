"""Render a rough chalkboard animatic of the Hypothetica Episode 1 opening.

Usage: python3 render_preview.py <out_dir>
Writes PNG frames to <out_dir>/frames, then encode with ffmpeg (see make_preview.sh).
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H = 1280, 720
FPS = 24
BOARD = (30, 42, 36)
CHALK = (236, 236, 228)
AMBER = (242, 169, 59)
RED = (214, 72, 64)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

rng = random.Random(7)


# ---------------------------------------------------------------- textures
def make_board():
    img = Image.new("RGB", (W, H), BOARD)
    noise = Image.effect_noise((W, H), 18).convert("L")
    tint = Image.merge("RGB", [noise.point(lambda v: v * 0.12)] * 3)
    img = ImageChops.add(img, tint, scale=1.0, offset=-12)
    # faint old erased smudges
    smudge = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(smudge)
    for _ in range(14):
        x, y = rng.randint(0, W), rng.randint(0, H)
        d.ellipse([x - 220, y - 40, x + 220, y + 40], fill=rng.randint(6, 14))
    smudge = smudge.filter(ImageFilter.GaussianBlur(40))
    img = Image.composite(Image.new("RGB", (W, H), (70, 84, 76)), img, smudge)
    # vignette
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-200, -160, W + 200, H + 160], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    return Image.composite(img, Image.new("RGB", (W, H), (12, 18, 15)), vig)


BOARD_IMG = make_board()
GRAIN = Image.effect_noise((W, H), 90).convert("L").point(lambda v: 255 if v > 95 else int(v * 1.6))


# ---------------------------------------------------------------- strokes
def jitter(points, amt=1.6, seed=0):
    r = random.Random(seed)
    return [(x + r.uniform(-amt, amt), y + r.uniform(-amt, amt)) for x, y in points]


def densify(points, step=6):
    out = []
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / step))
        for i in range(n):
            out.append((x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n))
    out.append(points[-1])
    return out


class Stroke:
    _seed = 0

    def __init__(self, points, color=CHALK, width=5):
        Stroke._seed += 1
        self.pts = jitter(densify(points), seed=Stroke._seed)
        self.pts2 = jitter(self.pts, 1.2, seed=Stroke._seed + 999)
        self.color = color
        self.width = width
        self.length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(self.pts, self.pts[1:]))

    def moved(self, dx, dy):
        s = Stroke.__new__(Stroke)
        s.__dict__.update(self.__dict__)
        s.pts = [(x + dx, y + dy) for x, y in self.pts]
        s.pts2 = [(x + dx, y + dy) for x, y in self.pts2]
        return s

    def partial(self, frac):
        if frac >= 1:
            return self.pts, self.pts2
        target = self.length * max(0.0, frac)
        acc, i = 0.0, 1
        while i < len(self.pts):
            seg = math.hypot(self.pts[i][0] - self.pts[i - 1][0], self.pts[i][1] - self.pts[i - 1][1])
            if acc + seg > target:
                break
            acc += seg
            i += 1
        return self.pts[:i], self.pts2[:i]


def circle(cx, cy, r, n=40, start=-90, sweep=360):
    return [(cx + r * math.cos(math.radians(start + sweep * i / n)),
             cy + r * math.sin(math.radians(start + sweep * i / n))) for i in range(n + 1)]


def rect(x1, y1, x2, y2):
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]


def render_strokes(base, strokes, progress=1.0, alpha=1.0, blur=0.0):
    """Draw strokes onto base. progress reveals strokes sequentially (0..1)."""
    by_color = {}
    total = sum(s.length for s in strokes) or 1
    budget = total * progress
    for s in strokes:
        if budget <= 0:
            break
        frac = min(1.0, budget / s.length) if s.length else 1
        budget -= s.length
        p1, p2 = s.partial(frac)
        layer = by_color.setdefault(s.color, Image.new("L", (W, H), 0))
        d = ImageDraw.Draw(layer)
        if len(p1) > 1:
            d.line(p1, fill=230, width=s.width, joint="curve")
            d.line(p2, fill=120, width=max(2, s.width - 2), joint="curve")
    for color, layer in by_color.items():
        layer = ImageChops.multiply(layer, GRAIN)
        if blur:
            layer = layer.filter(ImageFilter.GaussianBlur(blur))
        if alpha < 1:
            layer = layer.point(lambda v: int(v * alpha))
        base.paste(Image.new("RGB", (W, H), color), (0, 0), layer)
    return base


def chalk_text(base, text, xy, size, color=CHALK, alpha=1.0, anchor="mm", bold=True):
    layer = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    for dx, dy, v in [(0, 0, 235), (1.5, -1, 110), (-1, 1.5, 90)]:
        d.text((xy[0] + dx, xy[1] + dy), text, font=font, fill=v, anchor=anchor)
    layer = ImageChops.multiply(layer, GRAIN.point(lambda v: min(255, v + 60)))
    if alpha < 1:
        layer = layer.point(lambda v: int(v * alpha))
    base.paste(Image.new("RGB", (W, H), color), (0, 0), layer)


def caption(base, text, alpha):
    if alpha <= 0:
        return
    font = ImageFont.truetype(FONT_REG, 30)
    band = Image.new("L", (W, H), 0)
    ImageDraw.Draw(band).rectangle([0, H - 96, W, H - 30], fill=int(150 * alpha))
    band = band.filter(ImageFilter.GaussianBlur(12))
    base.paste((8, 12, 10), (0, 0), band)
    layer = Image.new("L", (W, H), 0)
    ImageDraw.Draw(layer).text((W / 2, H - 63), text, font=font, fill=int(255 * alpha), anchor="mm")
    base.paste((248, 246, 238), (0, 0), layer)


def glow(base, cx, cy, r, color, strength):
    layer = Image.new("L", (W, H), 0)
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(255 * strength))
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.6))
    overlay = Image.new("RGB", (W, H), color)
    return Image.composite(overlay, base, layer.point(lambda v: int(v * 0.55)))


# ---------------------------------------------------------------- drawings
def wren(cx, cy, s=1.0, walk=None):
    """Wren: round head, square glasses, scarf, rounded body, mitten hands. Not a stick figure."""
    st = []
    st.append(Stroke(circle(cx, cy, 62 * s), width=6))                      # head
    g = 22 * s
    for ox in (-30 * s, 30 * s):                                             # square glasses
        st.append(Stroke(rect(cx + ox - g, cy - 10 * s - g * 0.8, cx + ox + g, cy - 10 * s + g * 0.8), width=5))
    st.append(Stroke([(cx - 8 * s, cy - 12 * s), (cx + 8 * s, cy - 12 * s)], width=4))   # bridge
    st.append(Stroke(circle(cx, cy + 22 * s, 14 * s, n=12, start=20, sweep=140), width=4))  # smile
    by = cy + 62 * s
    st.append(Stroke([(cx - 50 * s, by + 4 * s), (cx, by + 16 * s), (cx + 50 * s, by + 4 * s)], AMBER if False else RED, 9))  # scarf
    st.append(Stroke([(cx + 30 * s, by + 10 * s), (cx + 44 * s, by + 58 * s), (cx + 26 * s, by + 62 * s)], RED, 8))
    body = [(cx - 46 * s, by + 14 * s), (cx - 58 * s, by + 120 * s), (cx - 30 * s, by + 150 * s),
            (cx + 30 * s, by + 150 * s), (cx + 58 * s, by + 120 * s), (cx + 46 * s, by + 14 * s)]
    st.append(Stroke(body, width=6))                                         # body outline
    swing = math.sin(walk) * 26 * s if walk is not None else 0
    for side in (-1, 1):                                                     # arms + mittens
        hx, hy = cx + side * 82 * s, by + 92 * s - side * swing * 0.4
        st.append(Stroke([(cx + side * 50 * s, by + 40 * s), (hx, hy)], width=int(12 * s)))
        st.append(Stroke(circle(hx, hy + 8 * s, 17 * s, n=16), width=6))
    for side in (-1, 1):                                                     # legs + feet
        lx = cx + side * 24 * s + (side * swing if walk is not None else 0)
        fy = by + 205 * s
        st.append(Stroke([(cx + side * 24 * s, by + 150 * s), (lx, fy)], width=int(14 * s)))
        st.append(Stroke([(lx - side * 10 * s, fy + 4 * s), (lx - side * 10 * s, fy - 8 * s),
                          (lx + side * 30 * s, fy - 6 * s), (lx + side * 34 * s, fy + 6 * s),
                          (lx - side * 10 * s, fy + 4 * s)], width=6))
    for k in range(5):                                                       # sweater stripes
        yy = by + (40 + k * 22) * s
        half = (48 + min(k, 3) * 3) * s
        st.append(Stroke([(cx - half + 6 * s, yy), (cx + half - 6 * s, yy)], CHALK, 2))
    return st


def lunch_tray(cx, cy):
    st = [Stroke(rect(cx - 210, cy - 120, cx + 210, cy + 120), width=6),
          Stroke([(cx - 40, cy - 120), (cx - 40, cy + 120)]),
          Stroke([(cx - 40, cy), (cx + 210, cy)]),
          Stroke(circle(cx - 125, cy, 50)),                                   # apple
          Stroke([(cx - 125, cy - 50), (cx - 115, cy - 75)]),
          Stroke([(cx + 10, cy - 30), (cx + 160, cy - 30), (cx + 85, cy - 95), (cx + 10, cy - 30)]),  # sandwich
          Stroke(rect(cx + 40, cy + 30, cx + 130, cy + 95))]                 # milk carton
    return st


def street():
    st = [Stroke([(0, 560), (W, 560)], width=6),
          Stroke([(0, 590), (W, 590)], width=3)]
    for x in (180, 520, 900):                                                # sidewalk cracks
        st.append(Stroke([(x, 560), (x + 14, 570), (x - 6, 580), (x + 10, 590)], width=3))
    # car on the right
    cx = 960
    st += [Stroke([(cx - 170, 495), (cx - 170, 435), (cx - 90, 435), (cx - 50, 375), (cx + 80, 375),
                   (cx + 120, 435), (cx + 180, 440), (cx + 180, 495), (cx - 170, 495)], width=6),
           Stroke(circle(cx - 100, 503, 36)), Stroke(circle(cx + 110, 503, 36)),
           Stroke(rect(cx - 30, 455, cx + 50, 480), width=3)]                # license plate
    return st


def filmstrip(x0, y, n=6):
    st = []
    for i in range(n):
        x = x0 + i * 120
        st.append(Stroke(rect(x, y, x + 110, y + 80), AMBER, 4))
        for k in range(4):
            st.append(Stroke(rect(x + 10 + k * 25, y - 16, x + 22 + k * 25, y - 6), AMBER, 2))
        mx, my = x + 55, y + 40
        icon = i % 6
        if icon == 0:   # clock
            st += [Stroke(circle(mx, my, 24), AMBER, 3), Stroke([(mx, my - 16), (mx, my), (mx + 12, my + 6)], AMBER, 3)]
        elif icon == 1:  # apple
            st += [Stroke(circle(mx, my + 4, 20), AMBER, 3), Stroke([(mx, my - 16), (mx + 6, my - 28)], AMBER, 3)]
        elif icon == 2:  # car
            st += [Stroke([(mx - 34, my + 12), (mx - 34, my - 2), (mx - 14, my - 2), (mx - 6, my - 16), (mx + 18, my - 16),
                           (mx + 26, my - 2), (mx + 34, my), (mx + 34, my + 12), (mx - 34, my + 12)], AMBER, 3)]
        elif icon == 3:  # sun
            st.append(Stroke(circle(mx, my, 12), AMBER, 3))
            for a in range(0, 360, 60):
                c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
                st.append(Stroke([(mx + 18 * c, my + 18 * sn), (mx + 28 * c, my + 28 * sn)], AMBER, 3))
        elif icon == 4:  # face
            st += [Stroke(circle(mx, my, 24), AMBER, 3), Stroke(circle(mx, my + 4, 10, n=10, start=20, sweep=140), AMBER, 3)]
        else:            # house
            st += [Stroke([(mx - 24, my + 22), (mx - 24, my - 4), (mx, my - 26), (mx + 24, my - 4), (mx + 24, my + 22),
                           (mx - 24, my + 22)], AMBER, 3)]
    return st


# ---------------------------------------------------------------- timeline
def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def fade(t, a, b, f=0.4):
    """1 inside [a,b], fading in/out over f seconds."""
    return ease((t - a) / f) * ease((b - t) / f)


TRAY = lunch_tray(640, 320)
WREN_HOOK = wren(640, 230, 1.0)
STREET = street()
PLATE_BOX = Stroke(rect(925, 447, 1015, 488), AMBER, 4)
CRACK_BOXES = [Stroke(circle(x + 4, 575, 30, n=24), AMBER, 3) for x in (180, 520)]
CAR_BOX = Stroke(rect(780, 360, 1150, 550), AMBER, 3)
FILM = filmstrip(160, 120, n=9)

CAPTIONS = [
    (0.6, 4.0, "What's the first thing you ever remember?"),
    (4.4, 9.0, "Now... what did you have for lunch eleven days ago?"),
    (9.4, 12.6, "Gone, right? Your brain threw it away."),
    (12.8, 17.4, "But what if it didn't? What if you never forgot anything, ever again?"),
    (22.6, 27.4, "Wren notices every license plate. Every crack in the sidewalk."),
    (27.6, 32.4, "And that night... every second is still there."),
]

DURATION = 36.0


def frame(t):
    img = BOARD_IMG.copy()

    # 1. chalk dot
    if t < 4.6:
        a = fade(t, 0.2, 4.4)
        r = 6 + 4 * ease((t - 0.2) / 0.6)
        render_strokes(img, [Stroke(circle(640, 330, r, n=16), width=6)], alpha=a)

    # 2. lunch tray draws, then smudges away
    if 4.2 <= t < 9.6:
        draw_p = ease((t - 4.4) / 2.6)
        smudge = ease((t - 7.6) / 1.8)
        render_strokes(img, TRAY, progress=draw_p, alpha=1 - smudge, blur=smudge * 14)

    # 3. Wren draws in, amber flicker in glasses
    if 9.4 <= t < 18.2:
        p = ease((t - 9.6) / 3.2)
        out = ease((t - 17.4) / 0.8)
        if t > 13.0:
            flick = 0.55 + 0.45 * math.sin(t * 9) * math.sin(t * 3.7)
            img = glow(img, 610, 220, 40, AMBER, flick * (1 - out))
            img = glow(img, 670, 220, 40, AMBER, flick * (1 - out))
        render_strokes(img, WREN_HOOK, progress=p, alpha=1 - out)

    # 4. title card + eraser wipe
    if 17.8 <= t < 22.6:
        a = fade(t, 18.0, 22.4, 0.5)
        chalk_text(img, "HYPOTHETICA", (640, 320), 96, alpha=a)
        chalk_text(img, "Episode 1:  Never Forget", (640, 410), 40, AMBER, alpha=fade(t, 18.8, 22.4, 0.5), bold=False)
        if t > 21.6:  # eraser swipe
            x = -300 + (W + 600) * ease((t - 21.6) / 0.9)
            band = Image.new("L", (W, H), 0)
            ImageDraw.Draw(band).rectangle([x - 900, 0, x, H], fill=255)
            img.paste(BOARD_IMG, (0, 0), band.filter(ImageFilter.GaussianBlur(30)))
            ImageDraw.Draw(img).rounded_rectangle([x - 10, 280, x + 70, 440], 12, fill=(150, 110, 70))
            ImageDraw.Draw(img).rectangle([x - 10, 400, x + 70, 440], fill=(60, 60, 64))

    # 5. street walk with amber "noticing"
    if 22.4 <= t <= DURATION:
        sp = ease((t - 22.6) / 1.6)
        out = ease((t - 27.4) / 0.8)
        if out < 1:
            render_strokes(img, STREET, progress=sp, alpha=1 - out)
            wx = 120 + (t - 22.6) * 70
            bob = abs(math.sin(t * 5)) * -6
            w = [s.moved(0, 0) for s in wren(wx, 250 + bob, 0.9, walk=t * 5)]
            render_strokes(img, w, progress=ease((t - 22.8) / 1.2), alpha=1 - out)
            for when, s in [(24.4, CRACK_BOXES[0]), (25.0, CAR_BOX), (25.6, PLATE_BOX), (26.3, CRACK_BOXES[1])]:
                if t > when:
                    render_strokes(img, [s], progress=ease((t - when) / 0.35), alpha=1 - out)
        # 6. amber filmstrip of memories, night
        if t > 27.6:
            p = ease((t - 27.8) / 2.6)
            img = glow(img, 640, 160, 260, AMBER, 0.25 * p)
            shift = (t - 29.0) * -40 if t > 29.0 else 0
            render_strokes(img, [s.moved(shift, 0) for s in FILM], progress=p)
            render_strokes(img, wren(640, 360, 0.75), progress=ease((t - 28.0) / 1.5))
        # end card
        if t > 33.0:
            a = ease((t - 33.0) / 0.8)
            dim = Image.new("L", (W, H), int(200 * a))
            img.paste(BOARD_IMG, (0, 0), dim)
            chalk_text(img, "NEVER FORGET", (640, 330), 84, AMBER, alpha=a)
            chalk_text(img, "full episode coming soon  -  Hypothetica", (640, 420), 28, alpha=a * 0.8, bold=False)

    for a, b, text in CAPTIONS:
        caption(img, text, fade(t, a, b, 0.3))

    # global fade in/out
    g = ease(t / 0.5) * ease((DURATION - t) / 0.8)
    if g < 1:
        img = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, g)
    return img


def main():
    out = os.path.join(sys.argv[1], "frames")
    os.makedirs(out, exist_ok=True)
    n = int(DURATION * FPS)
    start, step = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1)
    for i in range(start, n, step):
        frame(i / FPS).save(os.path.join(out, f"f{i:05d}.png"), compress_level=1)


if __name__ == "__main__":
    main()
