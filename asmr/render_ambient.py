"""Hushfall ambient video #1: "Rainy Night Window".

Makes a seamless 20-second video loop and a seamless rain soundtrack, which ffmpeg then
loops into a video of any length (1h, 3h, 8h...).

Usage:
  python3 render_ambient.py frames <out_dir> [start step]
  python3 render_ambient.py audio <out.wav> [minutes]
  python3 render_ambient.py still <t> <out.png>
"""
import math
import os
import random
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.signal import butter, sosfilt

W, H = 1280, 720
SS = 2
FPS = 24
LOOP = 20.0                       # seconds; every motion repeats exactly on this period
N_FRAMES = int(LOOP * FPS)
WARM = (255, 186, 110)
SIL = (10, 9, 12)

# window opening (outside visible through it)
WX1, WY1, WX2, WY2 = 300, 70, 980, 520


def per(t, period):
    """Phase 0..1 of a motion whose period divides LOOP."""
    return (t / period) % 1.0


def gradient(stops, w=W, h=H):
    ys = np.linspace(0, 1, h)
    cols = np.stack([np.interp(ys, [p for p, _ in stops], [c[i] for _, c in stops]) for i in range(3)], 1)
    return Image.fromarray(np.repeat(cols[:, None, :], w, 1).astype(np.uint8), "RGB")


class Mask:
    def __init__(self):
        self.m = Image.new("L", (W * SS, H * SS), 0)
        self.d = ImageDraw.Draw(self.m)

    def rect(self, x1, y1, x2, y2, fill=255):
        self.d.rectangle([x1 * SS, y1 * SS, x2 * SS, y2 * SS], fill=fill)

    def rrect(self, x1, y1, x2, y2, r, fill=255):
        self.d.rounded_rectangle([x1 * SS, y1 * SS, x2 * SS, y2 * SS], r * SS, fill=fill)

    def ellipse(self, x1, y1, x2, y2, fill=255):
        self.d.ellipse([x1 * SS, y1 * SS, x2 * SS, y2 * SS], fill=fill)

    def poly(self, pts, fill=255):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)

    def line(self, pts, w, fill=255):
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=int(w * SS), joint="curve")

    def get(self):
        return self.m.resize((W, H), Image.LANCZOS)


def glow_layer(cx, cy, r, strength=1.0):
    l = Image.new("L", (W, H), 0)
    ImageDraw.Draw(l).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(255 * strength))
    return l.filter(ImageFilter.GaussianBlur(r * 0.7))


# ---------------------------------------------------------------- static layers
rng = random.Random(21)

# outside: night city, blurred bokeh lights
OUTSIDE = gradient([(0, (8, 12, 30)), (0.55, (22, 30, 62)), (1, (40, 44, 72))])
_b = Image.new("RGB", (W, H), (0, 0, 0))
_bd = ImageDraw.Draw(_b)
for _ in range(70):
    x, y = rng.uniform(WX1 - 40, WX2 + 40), rng.uniform(260, WY2 + 20)
    r = rng.uniform(4, 16)
    c = rng.choice([(255, 190, 110), (255, 214, 150), (150, 180, 255), (255, 150, 120), (200, 220, 255)])
    k = rng.uniform(0.25, 0.8)
    _bd.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(v * k) for v in c))
# distant building silhouettes
_city = Mask()
x = WX1 - 60
while x < WX2 + 60:
    bw, bh = rng.randint(40, 110), rng.randint(60, 200)
    _city.rect(x, 520 - bh, x + bw, 560)
    x += bw + rng.randint(2, 20)
OUTSIDE.paste((14, 16, 30), (0, 0), _city.get())
# tiny lit windows in buildings
_wd = ImageDraw.Draw(_b)
for _ in range(120):
    x, y = rng.uniform(WX1, WX2), rng.uniform(340, 520)
    if _city.get().getpixel((int(x), int(y))) > 128 and rng.random() < 0.5:
        _wd.rectangle([x, y, x + 3, y + 4], fill=(180, 140, 80))
OUTSIDE = Image.blend(OUTSIDE, OUTSIDE, 1)
OUTSIDE = Image.composite(Image.new("RGB", (W, H)), OUTSIDE, Image.new("L", (W, H), 0))
OUTSIDE = Image.fromarray(np.clip(np.asarray(OUTSIDE, np.int16) + np.asarray(_b.filter(ImageFilter.GaussianBlur(6)), np.int16), 0, 255).astype(np.uint8))
OUTSIDE_BLUR = OUTSIDE.filter(ImageFilter.GaussianBlur(2.5))   # seen through wet glass

# interior: wall around window, frame, desk, lamp, plant, mug, books
ROOM = gradient([(0, (26, 20, 22)), (1, (44, 32, 30))])
INTERIOR = Mask()
INTERIOR.rect(0, 0, W, WY1); INTERIOR.rect(0, 0, WX1, H); INTERIOR.rect(WX2, 0, W, H); INTERIOR.rect(0, WY2, W, H)
FRAME = Mask()
for r_ in [(WX1 - 14, WY1 - 14, WX2 + 14, WY1), (WX1 - 14, WY2, WX2 + 14, WY2 + 18),
           (WX1 - 14, WY1 - 14, WX1, WY2 + 18), (WX2, WY1 - 14, WX2 + 14, WY2 + 18),
           ((WX1 + WX2) / 2 - 7, WY1, (WX1 + WX2) / 2 + 7, WY2), (WX1, 290 - 6, WX2, 290 + 6)]:
    FRAME.rect(*r_)
FRAME.rect(WX1 - 40, WY2 + 10, WX2 + 40, WY2 + 30)             # windowsill
FG = Mask()
FG.rect(0, 600, W, H)                                           # desk top + front
FG.rect(0, 588, W, 604)
# lamp (left)
FG.ellipse(120, 578, 230, 600); FG.line([(175, 588), (195, 450), (150, 380)], 9)
FG.poly([(100, 400), (190, 350), (225, 395), (150, 440)])
# books (right)
for i, (bw, bh) in enumerate([(26, 120), (22, 104), (30, 132), (20, 96)]):
    bx = 1040 + sum(w for w, _ in [(26, 0), (22, 0), (30, 0), (20, 0)][:i]) + i * 3
    FG.rect(bx, 590 - bh, bx + bw, 592)
FG.poly([(1150, 592), (1170, 500), (1192, 504), (1174, 592)])  # leaning book
# mug
FG.rrect(770, 528, 832, 596, 8); FG.d.ellipse([828 * SS, 542 * SS, 858 * SS, 578 * SS], outline=255, width=9 * SS)
# plant on sill
FG.rrect(880, 498, 940, 540, 6)
for a in (-50, -25, 0, 22, 48):
    ang = math.radians(a - 90)
    FG.line([(910, 500), (910 + 70 * math.cos(ang) * 0.7, 500 + 70 * math.sin(ang))], 9)
INTERIOR_M, FRAME_M, FG_M = INTERIOR.get(), FRAME.get(), FG.get()

# lamp light pools
LAMP_GLOW = glow_layer(170, 470, 260, 0.9)
WALL_GLOW = glow_layer(170, 300, 330, 0.55)
LAMP_BULB = glow_layer(168, 432, 40, 1.0)

# rain outside: thin falling lines. speed * LOOP must be a multiple of the travel height to loop.
OUT_RAIN = []
for _ in range(420):
    cycles = rng.randint(14, 24)                      # how many times it falls per loop
    OUT_RAIN.append((rng.uniform(WX1 - 60, WX2), rng.uniform(0, 1), cycles, rng.uniform(10, 22), rng.uniform(0.25, 0.7)))

# drops sliding down the glass: slow, wobbling, with a trail
GLASS = []
for _ in range(34):
    GLASS.append((rng.uniform(WX1 + 10, WX2 - 10), rng.uniform(0, 1), rng.choice([1, 2, 3]), rng.uniform(2.5, 5), rng.uniform(0, 6.28)))
STATIC_DROPS = [(rng.uniform(WX1, WX2), rng.uniform(WY1, WY2), rng.uniform(1.2, 3.2)) for _ in range(260)]


# cat sleeping on the windowsill (original design: curled loaf with ear tips and a wrapped tail)
def cat(m, breath):
    cx, cy = 560, WY2 + 8
    sy = 1 + 0.035 * breath
    m.ellipse(cx - 80, cy - 52 * sy, cx + 80, cy + 4)                       # body
    m.ellipse(cx + 40, cy - 60 * sy, cx + 104, cy - 6)                      # head
    m.poly([(cx + 50, cy - 50 * sy), (cx + 56, cy - 78 * sy), (cx + 72, cy - 56 * sy)])   # ears
    m.poly([(cx + 80, cy - 56 * sy), (cx + 96, cy - 76 * sy), (cx + 100, cy - 48 * sy)])
    m.line([(cx - 76, cy - 6), (cx - 40, cy + 4), (cx + 20, cy + 6), (cx + 50, cy - 2)], 14)  # tail wrap


def frame(t):
    img = OUTSIDE_BLUR.copy()
    # occasional soft sheet-lightning glow, periodic so it loops (once per loop)
    ph = per(t, LOOP)
    flash = max(0.0, 1 - abs(ph - 0.62) / 0.012) * 0.5 + max(0.0, 1 - abs(ph - 0.655) / 0.008) * 0.35
    if flash > 0:
        img = Image.blend(img, Image.new("RGB", (W, H), (150, 160, 200)), flash * 0.35)
    # rain outside
    rl = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(rl)
    span = (WY2 + 60) - (WY1 - 60)
    for x0, off, cyc, ln, a in OUT_RAIN:
        y = WY1 - 60 + ((off + t / LOOP * cyc) % 1) * span
        x = x0 + (y - WY1) * 0.08
        rd.line([(x, y), (x + ln * 0.08, y + ln)], fill=int(255 * a), width=1)
    img.paste((170, 185, 220), (0, 0), rl)
    # glass: static beads + sliding drops with trails
    gl = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(gl)
    for x, y, r in STATIC_DROPS:
        gd.ellipse([x - r, y - r, x + r, y + r], fill=70)
    for x0, off, cyc, r, wph in GLASS:
        p = (off + t / LOOP * cyc) % 1
        # ease-in-out slide: drops hang, then run
        q = p - math.sin(2 * math.pi * p) / (2 * math.pi)
        y = WY1 + q * (WY2 - WY1 + 30)
        x = x0 + 3 * math.sin(q * 12 + wph)
        gd.line([(x0 + 3 * math.sin(wph), max(WY1, y - 120)), (x, y)], fill=35, width=2)
        gd.ellipse([x - r, y - r * 1.3, x + r, y + r], fill=150)
    glass = gl.filter(ImageFilter.GaussianBlur(0.8))
    img.paste((205, 215, 240), (0, 0), glass.point(lambda v: v // 2))
    # interior wall + warm lamp light
    img.paste(ROOM, (0, 0), INTERIOR_M)
    flick = 0.96 + 0.04 * math.sin(2 * math.pi * per(t, 5)) * math.sin(2 * math.pi * per(t, 2))
    img.paste((120, 70, 40), (0, 0), WALL_GLOW.point(lambda v: int(v * 0.6 * flick)))
    img.paste(SIL, (0, 0), FRAME_M)
    # cat breathing (4 s cycle) on the sill
    cm = Mask()
    cat(cm, math.sin(2 * math.pi * per(t, 4)))
    img.paste(SIL, (0, 0), cm.get())
    img.paste(SIL, (0, 0), FG_M)
    # lamp light pooling on desk + bulb
    img.paste(WARM, (0, 0), LAMP_GLOW.point(lambda v: int(v * 0.32 * flick)))
    img.paste((255, 230, 180), (0, 0), LAMP_BULB.point(lambda v: int(v * flick)))
    # steam from the mug (two wisps, 5 s cycle)
    st = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(st)
    for k in range(2):
        pts = []
        for i in range(30):
            f = i / 29
            y = 520 - f * 120
            x = 800 + k * 14 + 12 * math.sin(f * 7 + 2 * math.pi * per(t, 5) + k * 2) * (0.3 + f)
            pts.append((x, y))
        for i in range(29):
            a = int(110 * math.sin(math.pi * i / 29) * (1 - i / 34))
            sd.line([pts[i], pts[i + 1]], fill=a, width=5)
    img.paste((240, 220, 200), (0, 0), st.filter(ImageFilter.GaussianBlur(4)))
    # soft vignette
    return Image.composite(img, Image.new("RGB", (W, H), (4, 3, 5)), VIGNETTE)


VIGNETTE = Image.new("L", (W, H), 0)
ImageDraw.Draw(VIGNETTE).ellipse([-260, -200, W + 260, H + 200], fill=255)
VIGNETTE = VIGNETTE.filter(ImageFilter.GaussianBlur(140))


# ---------------------------------------------------------------- rain soundtrack
def bp(lo, hi, sr, order=2):
    return butter(order, [lo, hi], btype="band", fs=sr, output="sos")


def audio(path, minutes=10.0, sr=44100):
    n = int(minutes * 60 * sr)
    xf = int(6 * sr)                                    # crossfade for a seamless loop
    total = n + xf
    r = np.random.default_rng(7)
    out = np.zeros((total, 2), np.float32)
    # slow intensity swell (smooth random curve)
    knots = r.uniform(0.75, 1.15, int(total / sr / 20) + 3)
    swell = np.interp(np.arange(total) / sr / 20, np.arange(len(knots)), knots).astype(np.float32)
    s_hiss, s_body, s_roof = bp(1500, 9000, sr), bp(300, 2500, sr), butter(2, 180, fs=sr, output="sos")
    for ch in range(2):
        noise = r.standard_normal(total).astype(np.float32)
        out[:, ch] += 0.10 * sosfilt(s_hiss, noise)
        out[:, ch] += 0.22 * sosfilt(s_body, r.standard_normal(total).astype(np.float32))
        brown = np.cumsum(r.standard_normal(total).astype(np.float32)) * 0.02
        brown -= sosfilt(butter(1, 5, btype="low", fs=sr, output="sos"), brown)   # remove drift
        out[:, ch] += 0.5 * sosfilt(s_roof, brown)
    out *= swell[:, None]
    # individual drops tapping the glass
    ln = int(0.04 * sr)
    tt = np.arange(ln) / sr
    for _ in range(int(total / sr * 9)):
        i = r.integers(0, total - ln)
        f = r.uniform(1800, 5200)
        amp = r.uniform(0.01, 0.06) * swell[i]
        pan = r.uniform(0.15, 0.85)
        drop = (amp * np.exp(-tt * r.uniform(90, 180)) * np.sin(2 * np.pi * f * tt)).astype(np.float32)
        out[i:i + ln, 0] += drop * (1 - pan)
        out[i:i + ln, 1] += drop * pan
    # heavier drips off the gutter, slower and lower
    ln2 = int(0.12 * sr)
    tt2 = np.arange(ln2) / sr
    for _ in range(int(total / sr * 0.6)):
        i = r.integers(0, total - ln2)
        f = r.uniform(700, 1300)
        sweep = f * (1 + 0.6 * np.exp(-tt2 * 40))
        d = (0.08 * np.exp(-tt2 * 30) * np.sin(2 * np.pi * np.cumsum(sweep) / sr)).astype(np.float32)
        pan = r.uniform(0.3, 0.7)
        out[i:i + ln2, 0] += d * (1 - pan); out[i:i + ln2, 1] += d * pan
    # distant thunder every ~2-3 minutes
    lp = butter(3, 120, fs=sr, output="sos")
    tpos = r.uniform(30, 90)
    while tpos < total / sr - 15:
        i0 = int(tpos * sr); L = int(12 * sr)
        tt3 = np.arange(L) / sr
        env = (1 - np.exp(-tt3 * 3)) * np.exp(-tt3 / 3.2) * (1 + 0.5 * np.sin(tt3 * 5.3) * np.exp(-tt3))
        rumble = sosfilt(lp, r.standard_normal(L)).astype(np.float32) * env.astype(np.float32) * 0.9
        out[i0:i0 + L] += rumble[:, None]
        tpos += r.uniform(110, 190)
    # seamless loop: crossfade the tail into the head
    fade_in = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
    out[:xf] = out[:xf] * fade_in + out[n:n + xf] * (1 - fade_in)
    out = out[:n]
    out = np.tanh(out * 1.6) * 0.55
    data = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(data.tobytes())


def main():
    mode = sys.argv[1]
    if mode == "audio":
        audio(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 10.0)
    elif mode == "still":
        frame(float(sys.argv[2])).save(sys.argv[3])
    else:
        out = os.path.join(sys.argv[2], "frames")
        os.makedirs(out, exist_ok=True)
        start, step = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 1)
        for i in range(start, N_FRAMES, step):
            frame(i / FPS).save(os.path.join(out, f"f{i:05d}.png"), compress_level=1)


if __name__ == "__main__":
    main()
