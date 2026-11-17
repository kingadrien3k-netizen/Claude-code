"""nocap — "Ever Leave 95" — BabyStayDown-style pluggnb. Melody C from Adrien's "bow bow bow, wow wow wow wow wow".
All sounds synthesized. Outputs master WAV (24-bit), stems lead/pad/drums/808."""
import os, sys, wave
import numpy as np

SR = 44100
BPM = 95
STEP = 60 / BPM / 4
BAR = 16 * STEP
SWING = 0.08 * STEP
rng = np.random.default_rng(95)
OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, "stems"), exist_ok=True)

LAYOUT = [("intro", 4), ("hook", 8), ("verse", 12), ("hook", 8), ("verse", 12),
          ("bridge", 4), ("hook", 8), ("outro", 4)]
SECS = [s for s, n in LAYOUT for _ in range(n)]
NB = len(SECS)
N = int(NB * BAR * SR) + 4 * SR


def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
def st(s): return s * STEP + (SWING if int(round(s)) % 2 else 0)
def norm(x):
    p = np.abs(x).max(); return x / p if p else x


def fft_filter(x, lo=0.0, hi=None, order=4):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if lo: g *= 1 / (1 + (lo / np.maximum(f, 1)) ** order)
    if hi: g *= 1 / (1 + (f / hi) ** order)
    return np.fft.irfft(X * g, len(x))


def add(buf, sig, t, gain=1.0):
    i = int(round(t * SR))
    if i < 0 or i >= len(buf): return
    j = min(len(buf), i + len(sig)); buf[i:j] += sig[: j - i] * gain


# ---------- sounds ----------
def pluck(f, dur, bright=0.6):
    n = int(dur * SR); p = max(2, int(round(SR / f))); y = np.zeros(n + p + 1)
    b = rng.uniform(-1, 1, p + 1)
    y[:p + 1] = bright * b + (1 - bright) * np.sin(np.linspace(0, 2 * np.pi, p + 1))
    for i in range(p + 1, len(y), p):
        j = min(len(y), i + p); y[i:j] = 0.997 * 0.5 * (y[i - p:j - p] + y[i - p - 1:j - p - 1])
    s = y[:n]; r = min(n, 400); s[-r:] *= np.linspace(1, 0, r); return s


def bell(f, dur):
    t = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 4)
         + 0.1 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 7)) * np.exp(-t * 2.0)
    s[:60] *= np.linspace(0, 1, 60); return s


def lead_note(m, dur):
    # dreamy: pluck + bell + slightly detuned pluck an octave up, soft
    f = midi(m)
    return 0.55 * pluck(f, dur) + 0.35 * bell(f, dur) + 0.15 * pluck(f * 2 * 1.003, dur, 0.3)


def airpad(notes, dur):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for m in notes:
        for det in (-0.12, 0.0, 0.12):
            s += 2 * ((t * midi(m + det)) % 1) - 1
    s = fft_filter(s, 200, 2200)
    s *= 1 + 0.2 * np.sin(2 * np.pi * 0.25 * t)
    env = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.5)
    return norm(s) * env


def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 110 * np.exp(-t * 40)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12)
    c = fft_filter(rng.uniform(-1, 1, n), 2000, 7000) * np.exp(-t * 250)
    return np.tanh(1.6 * (s + 0.3 * c))


def snare():   # soft pluggnb snare: noise + body, no hard crack
    n = int(0.3 * SR); t = np.arange(n) / SR
    no = norm(fft_filter(rng.uniform(-1, 1, n), 1200, 8000)) * np.exp(-t * 22)
    body = np.sin(2 * np.pi * 220 * t) * np.exp(-t * 30)
    return 0.7 * no + 0.5 * body


def hat(L=0.04):
    n = int(L * SR); t = np.arange(n) / SR
    return norm(fft_filter(rng.uniform(-1, 1, n), 8000, 14000)) * np.exp(-t * (80 if L < 0.1 else 12))


def bass808(f, dur, slide_from=None):
    n = int(dur * SR); t = np.arange(n) / SR; fr = np.full(n, f)
    if slide_from:
        g = min(n, int(0.12 * SR)); fr[:g] = np.geomspace(slide_from, f, g)
    s = np.sin(2 * np.pi * np.cumsum(fr) / SR)
    amp = np.exp(-t * 0.6); a = min(n, 150); amp[:a] *= np.linspace(0, 1, a)
    r = min(n, int(0.03 * SR)); amp[-r:] *= np.linspace(1, 0, r)
    return np.tanh(1.8 * s * amp) / np.tanh(1.8)       # clean-ish pluggnb 808


K, SN, H, OH = kick(), snare(), hat(), hat(0.25)

# ---------- music ----------
CH = [dict(pad=[57, 60, 64, 67, 71], root=33),   # Am9
      dict(pad=[53, 57, 60, 64], root=29),       # Fmaj7
      dict(pad=[50, 53, 57, 60, 64], root=38),   # Dm9
      dict(pad=[52, 56, 59, 64], root=40)]       # E
R = [(0, 0, 4), (0, 4, 4), (0, 8, 6), (1, 0, 2), (1, 2, 2), (1, 4, 2), (1, 6, 2), (1, 8, 8)]
CALL = [72, 76, 79, 81, 79, 76, 74, 76]      # Melody C
ANSWER = [72, 76, 81, 83, 81, 80, 76, 76]    # harmonic-minor answer over Dm9 -> E
KICK_A, KICK_B = [0, 6, 11], [0, 3, 9]

lead = np.zeros(N); pad = np.zeros(N); drums = np.zeros(N); b808 = np.zeros(N)

for b, sec in enumerate(SECS):
    t0 = b * BAR; pb = b % 4; ch = CH[pb]
    nxt = SECS[b + 1] if b + 1 < NB else None
    into_hook = nxt == "hook" and sec != "hook"

    # pad everywhere (thin in verses)
    g = {"intro": 1.0, "hook": 0.8, "verse": 0.45, "bridge": 0.7, "outro": 0.55}[sec]
    add(pad, airpad(ch["pad"], BAR + 0.05), t0, g)

    # lead: full motif in intro/hook/outro; verses only the "bow bow bow" part (vocal room)
    if pb in (0, 2):
        notes = CALL if pb == 0 else ANSWER
        for (bb, s, L), m in zip(R, notes):
            if sec == "verse" and bb == 1: continue
            if sec == "bridge" and bb == 0: continue
            gl = 0.55 if sec == "verse" else (1.4 if sec == "intro" else 1.0)
            add(lead, lead_note(m, L * STEP + 0.4), t0 + bb * BAR + st(s), gl)
            if sec == "hook":
                add(lead, lead_note(m + 12, L * STEP + 0.3), t0 + bb * BAR + st(s) + 0.012, 0.18)

    if sec in ("intro", "outro"):
        if sec == "intro" and b == 3:
            for k in range(6): add(drums, H, t0 + (10 + k) * STEP, 0.15 + 0.03 * k)
        continue

    # drums
    kp = KICK_A if b % 2 == 0 else KICK_B
    if sec != "bridge":
        for s in kp: add(drums, K, t0 + st(s), 0.85)
    add(drums, SN, t0 + st(4), 0.7)
    if not into_hook: add(drums, SN, t0 + st(12), 0.7)
    else:
        for k in range(6): add(drums, SN, t0 + (12 + k * 2 / 3) * STEP, 0.25 + 0.08 * k)
    for s in range(0, 16, 2):
        add(drums, H, t0 + st(s), 0.3 if s % 4 == 0 else 0.2)
    if b % 2 == 1 and sec != "bridge":
        for k in range(3): add(drums, H, t0 + (13 + k * 2 / 3) * STEP, 0.18)    # triplet roll
    if sec == "hook" and pb == 3: add(drums, OH, t0 + st(14), 0.15)

    # 808: hooks follow every kick with slides; verses softer on the one
    if sec == "hook":
        for i, s in enumerate(kp):
            end = kp[i + 1] if i + 1 < len(kp) else 16
            slide = midi(ch["root"] + 12) if (i == len(kp) - 1 and pb == 3) else None
            add(b808, bass808(midi(ch["root"]), (end - s) * STEP + 0.02, slide), t0 + st(s), 1.0)
    elif sec == "verse":
        add(b808, bass808(midi(ch["root"]), 9 * STEP), t0, 0.8)
        if pb == 3: add(b808, bass808(midi(ch["root"] + 7), 5 * STEP, midi(ch["root"])), t0 + st(11), 0.7)
    elif sec == "bridge":
        add(b808, bass808(midi(ch["root"]), 15 * STEP), t0, 0.55)


# ---------- mix ----------
def reverb(x, secs=3.0, lo=250, hi=6000, decay=1.8):
    n = int(secs * SR); ir = fft_filter(rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * decay), lo, hi)
    L = len(x) + n
    return norm(np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[: len(x)])


lead_s = norm(lead) * 0.75 + reverb(lead) * 0.4                 # dreamy wash
pad_s = fft_filter(norm(pad), 200, 5000)
duck = 1 - 0.4 * np.clip(np.abs(b808) * 1.3, 0, 1)
stems = {"lead": norm(lead_s) * 0.55, "pad": norm(pad_s * duck) * 0.22,
         "drums": norm(drums) * 0.6, "808": norm(b808) * 0.66}
end = int(NB * BAR * SR)
for k in stems:
    stems[k][int((NB - 2) * BAR * SR):end] *= np.linspace(1, 0.4, end - int((NB - 2) * BAR * SR))
    stems[k][end:] *= np.linspace(0.4, 0, len(stems[k]) - end)
mix = sum(stems.values())
master = np.tanh(1.5 * mix) / np.tanh(1.5)
master *= 10 ** (-0.3 / 20) / max(np.abs(master).max(), 1e-9) if np.abs(master).max() > 10 ** (-0.3 / 20) else 1


def write24(path, mono):
    i = (np.clip(mono, -1, 1) * 8388607).astype(np.int32); s = np.column_stack([i, i]).ravel()
    b = np.zeros((len(s), 3), np.uint8); b[:, 0] = s & 255; b[:, 1] = (s >> 8) & 255; b[:, 2] = (s >> 16) & 255
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); w.writeframes(b.tobytes())


write24(os.path.join(OUT, "nocap - Ever Leave 95 (Amin).wav"), master)
for k, v in stems.items():
    write24(os.path.join(OUT, "stems", f"Ever Leave 95 - {k}.wav"), v)
r = lambda x, a, c: 20 * np.log10(np.sqrt(np.mean(x[int(a * BAR * SR):int(c * BAR * SR)] ** 2)) + 1e-12)
print(f"{NB} bars {len(master)/SR:.1f}s | intro {r(master,0,4):.1f} hook {r(master,4,12):.1f} verse {r(master,12,24):.1f} bridge {r(master,44,48):.1f} dB")
