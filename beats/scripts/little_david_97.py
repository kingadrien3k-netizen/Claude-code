"""nocap — "Little David 97" — ghetto gospel lane.
Choir: Fisk University Jubilee Singers, "Little David, Play On Yo' Harp" (Victor 16448, 1909), public domain (US).
Outputs: master WAV (24-bit), MP3, stems (choir/lead/pad/drums/808) as 24-bit WAVs.
"""
import os
import sys
import wave
import numpy as np

SR = 44100
BPM = 97
STEP = 60 / BPM / 4
BAR = 16 * STEP
rng = np.random.default_rng(1997)
CHOP_SRC = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(os.path.join(OUT, "stems"), exist_ok=True)

LAYOUT = [("intro", 4), ("verse", 8), ("hook", 8), ("verse", 8), ("hook", 8),
          ("bridge", 4), ("hook", 8), ("outro", 2)]
SECS = [s for s, n in LAYOUT for _ in range(n)]
NB = len(SECS)
N = int(NB * BAR * SR) + 3 * SR


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def fft_filter(x, lo=0.0, hi=None, order=4):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1)) ** order)
    if hi:
        g *= 1 / (1 + (f / hi) ** order)
    return np.fft.irfft(X * g, len(x))


def add(buf, sig, t, gain=1.0):
    i = int(round(t * SR))
    if i < 0 or i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def norm(x):
    p = np.abs(x).max()
    return x / p if p else x


# ================= CHOIR CHOP =================
def load_wav_mono(path):
    w = wave.open(path)
    sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    a = a.reshape(-1, ch).mean(1)
    assert sr == SR and sw == 2
    return a


def stft_denoise(x, n=2048, hop=512, strength=1.6, floor=0.12):
    win = np.hanning(n)
    pad = np.concatenate([np.zeros(n), x, np.zeros(n)])
    frames = np.lib.stride_tricks.sliding_window_view(pad, n)[::hop] * win
    S = np.fft.rfft(frames, axis=1)
    mag = np.abs(S)
    energy = mag.sum(1)
    quiet = mag[energy <= np.percentile(energy, 12)]
    noise = np.median(quiet, axis=0)
    gain = np.maximum(floor, 1 - strength * noise / np.maximum(mag, 1e-9))
    # smooth gain over time to avoid musical noise
    k = np.ones(5) / 5
    gain = np.apply_along_axis(lambda g: np.convolve(g, k, "same"), 0, gain)
    Y = np.fft.irfft(S * gain, n, axis=1) * win
    out = np.zeros(len(pad))
    for i, fr in enumerate(Y):
        out[i * hop:i * hop + n] += fr
    out /= (win ** 2).sum() / hop
    return out[n:n + len(x)]


src = load_wav_mono(CHOP_SRC)
src = stft_denoise(src)
# this section of the record sits ~47 cents flat of E minor -> retune UP to concert E
step_ = 2 ** (47 / 1200)
pos = np.arange(0, len(src) - 1, step_)
src = np.interp(pos, np.arange(len(src)), src)
src = fft_filter(src, 140, 6500)
T = lambda s: int(s / step_ * SR)     # original-recording seconds -> retuned samples

intro_chop = src[T(92.6):T(92.6) + int(4 * BAR * SR) + int(0.6 * SR)].copy()
fade = int(0.08 * SR)
intro_chop[:fade] *= np.linspace(0, 1, fade)
intro_chop[-int(0.6 * SR):] *= np.linspace(1, 0, int(0.6 * SR))

# short stabs for the bridge breakdown (sustained chord moments)
def stab(start, dur):
    s = src[T(start):T(start) + int(dur * SR)].copy()
    a = int(0.006 * SR); r = int(0.05 * SR)
    s[:a] *= np.linspace(0, 1, a); s[-r:] *= np.linspace(1, 0, r)
    return s

STABS = [stab(114.2, 4 * STEP), stab(138.0, 3 * STEP), stab(140.0, 6 * STEP), stab(115.2, 8 * STEP)]

# ================= INSTRUMENTS =================
def organ(freq, dur, bars=(0.5, 1, 1.5, 2, 3), lv=(0.8, 1.0, 0.7, 0.35, 0.2),
          perc=0.0, leslie=6.3, click=0.15):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.0025 * np.sin(2 * np.pi * leslie * t)
    s = np.zeros(n)
    for h, a in zip(bars, lv):
        s += a * np.sin(2 * np.pi * freq * h * np.cumsum(vib) / SR)
    if perc:
        s += perc * np.sin(2 * np.pi * freq * 3 * t) * np.exp(-t * 9)
    s *= 1 + 0.18 * np.sin(2 * np.pi * leslie * t + 1.3)
    if click:
        c = min(n, 220)
        s[:c] += click * rng.uniform(-1, 1, c) * np.linspace(1, 0, c)
    a = min(n, 90); r = min(n, int(0.03 * SR))
    s[:a] *= np.linspace(0, 1, a); s[-r:] *= np.linspace(1, 0, r)
    return np.tanh(0.9 * s) / 0.9


def kick():
    n = int(0.42 * SR); t = np.arange(n) / SR
    f = 52 + 170 * np.exp(-t * 45)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    beater = fft_filter(rng.uniform(-1, 1, n), 2500, 9000) * np.exp(-t * 220)
    return np.tanh(2.4 * (body + 0.55 * beater)) / np.tanh(2.4)


def snare():
    n = int(0.33 * SR); t = np.arange(n) / SR
    noise = fft_filter(rng.uniform(-1, 1, n), 1500, 10000)
    noise = norm(noise) * np.exp(-t * 19)
    crack = fft_filter(rng.uniform(-1, 1, n), 3000, 9000) * np.exp(-t * 90)
    body = (np.sin(2 * np.pi * 205 * t) + 0.5 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t * 28)
    return np.tanh(1.8 * (0.75 * noise + 0.6 * norm(crack) + 0.65 * body))


def hat(length=0.045):
    n = int(length * SR); t = np.arange(n) / SR
    s = fft_filter(rng.uniform(-1, 1, n), 7800, 15000)
    return norm(s) * np.exp(-t * (75 if length < 0.1 else 13))


def bass808(freq, dur, slide_from=None, drive=3.2):
    n = int(dur * SR); t = np.arange(n) / SR
    f = np.full(n, freq)
    if slide_from:
        g = min(n, int(0.11 * SR))
        f[:g] = np.geomspace(slide_from, freq, g)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    amp = np.exp(-t * 0.55)
    a = min(n, 120); amp[:a] *= np.linspace(0, 1, a)
    r = min(n, int(0.025 * SR)); amp[-r:] *= np.linspace(1, 0, r)
    return np.tanh(drive * s * amp) / np.tanh(drive)


K, SN, H, OH = kick(), snare(), hat(), hat(0.28)

# ================= MUSIC =================
SWING = 0.12 * STEP


def st(step):
    return step * STEP + (SWING if int(round(step)) % 2 else 0)


def rhodes(freq, dur, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    idx = (1.2 + 1.6 * vel) * np.exp(-t * 5)
    s = np.sin(2 * np.pi * freq * t + idx * np.sin(2 * np.pi * freq * t))
    s += 0.18 * vel * np.sin(2 * np.pi * freq * 14.0 * t) * np.exp(-t * 40)   # tine
    s += 0.22 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 2.5)
    s *= np.exp(-t * 1.1) * (1 + 0.15 * np.sin(2 * np.pi * 4.8 * t))         # tremolo
    a = min(n, 50); r = min(n, int(0.04 * SR))
    s[:a] *= np.linspace(0, 1, a); s[-r:] *= np.linspace(1, 0, r)
    return np.tanh((1.0 + vel) * s) / np.tanh(1.0 + vel)                       # bark


def softpad(notes, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for m in notes:
        for det in (-0.08, 0.0, 0.08):
            s += 2 * ((t * midi(m + det)) % 1) - 1
    s = fft_filter(s, 180, 1400)
    env = np.minimum(1, t / 0.5) * np.minimum(1, (dur - t) / 0.3)
    return norm(s) * env


# Em9 | Cmaj9 | Am9 | B7      (E minor — the chop's native key, retuned)
CH = [
    dict(keys=[52, 55, 59, 62, 66], root=28),   # Em9: E G B D F#
    dict(keys=[48, 52, 55, 59, 62], root=36),   # Cmaj9: C E G B D
    dict(keys=[45, 48, 52, 55, 59], root=33),   # Am9: A C E G B
    dict(keys=[47, 51, 54, 57, 60], root=35),   # B7(b9): B D# F# A C
]
# (midi, start step, length) — CALL bars 1-2, RESPONSE bars 3-4
CALL = [[(71, 0, 2), (74, 2, 1), (76, 3, 5), (79, 10, 2), (78, 12, 1), (76, 13, 3)],
        [(74, 2, 2), (71, 4, 4), (67, 10, 6)]]
RESP = [[(72, 0, 3), (71, 3, 1), (69, 4, 4), (76, 12, 4)],
        [(78, 0, 2), (75, 2, 2), (71, 4, 6), (69, 12, 2), (66, 14, 2)]]
KICK_A = [0, 3, 8, 11]
KICK_B = [0, 2, 10, 11]
COMP_VERSE = [0]            # verses: one soft chord per bar = vocal room
COMP_HOOK = [0, 7, 10]

choir = np.zeros(N); lead = np.zeros(N); pad = np.zeros(N); drums = np.zeros(N); b808 = np.zeros(N)

add(choir, intro_chop, 0, 1.0)

for b, sec in enumerate(SECS):
    t0 = b * BAR
    ch = CH[b % 4]
    nxt = SECS[b + 1] if b + 1 < NB else None
    into_hook = nxt == "hook" and sec != "hook"
    pb = b % 4

    # ---- Rhodes: chord comping (pad stem) + motif (lead stem) ----
    if sec in ("verse", "hook", "outro") or (sec == "intro" and b >= 2):
        comp = COMP_HOOK if sec == "hook" else COMP_VERSE
        g = {"verse": 0.5, "hook": 0.65, "outro": 0.6, "intro": 0.35}[sec]
        for s in comp:
            for k, m in enumerate(ch["keys"]):
                add(pad, rhodes(midi(m), BAR * (0.9 if s == 0 else 0.5), 0.5), t0 + st(s) + 0.006 * k, g * 0.2)
    if sec == "hook":
        for m, s, L in (CALL + RESP)[pb]:
            add(lead, rhodes(midi(m), L * STEP + 0.25, 1.0), t0 + st(s), 0.35)
        add(pad, softpad(ch["keys"][:4], BAR), t0, 0.12)

    # ---- choir breakdown in bridge ----
    if sec == "bridge":
        hits = [(0, 0), (3, 1), (6, 2), (10, 0), (12, 1)] if b % 2 == 0 else [(0, 3), (6, 2), (8, 1), (11, 0), (14, 1)]
        for s, k in hits:
            add(choir, STABS[k], t0 + st(s), 0.9)

    if sec in ("intro", "outro"):
        if sec == "intro" and b == 3:
            for k in range(8):
                add(drums, SN, t0 + (8 + k) * STEP, 0.15 + 0.07 * k)
        continue

    # ---- drums: knock ----
    kp = KICK_A if b % 2 == 0 else KICK_B
    for s in kp:
        add(drums, K, t0 + st(s), 1.0)
    add(drums, SN, t0 + st(4), 0.95)
    if not into_hook:
        add(drums, SN, t0 + st(12), 0.95)
    if pb == 1:
        add(drums, SN, t0 + st(7), 0.22)      # ghost
    if pb == 3 and not into_hook:
        add(drums, SN, t0 + st(15), 0.3)
    if into_hook:                              # snare roll into the hook
        for k in range(8):
            add(drums, SN, t0 + (12 + k * 0.5) * STEP, 0.3 + 0.08 * k)

    for s in range(16):
        if sec == "bridge" and s % 2:
            continue
        vel = [0.4, 0.14, 0.26, 0.16][s % 4]
        add(drums, H, t0 + st(s), vel)
    if sec == "hook":
        add(drums, OH, t0 + st(14), 0.2)
        if b % 2:
            for k in range(3):
                add(drums, H, t0 + (6 + k * 2 / 3) * STEP, 0.22)

    # ---- 808 ----
    if sec == "hook":
        for i, s in enumerate(kp):
            end = kp[i + 1] if i + 1 < len(kp) else 16
            if end - s < 2 and i + 1 < len(kp):
                continue                           # let double kicks ride one 808
            note = ch["root"]; slide = None
            if pb == 3 and i == len(kp) - 1:
                slide = midi(note - 5)              # slide up from below into the turnaround
            add(b808, bass808(midi(note), (end - s) * STEP + 0.02, slide), t0 + st(s), 1.0)
    elif sec == "verse":
        add(b808, bass808(midi(ch["root"]), 10 * STEP), t0, 0.85)
    elif sec == "bridge" and b % 2 == 0:
        add(b808, bass808(midi(ch["root"]), 14 * STEP, drive=2), t0, 0.6)

# ================= MIX =================
def reverb(x, secs=2.4, lo=200, hi=5500, decay=2.6):
    n = int(secs * SR)
    ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * decay)
    ir = fft_filter(ir, lo, hi)
    L = len(x) + n
    return norm(np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[: len(x)])


choir_s = np.tanh(3.0 * norm(choir)) / np.tanh(3.0) * 0.8 + reverb(choir, 3.0) * 0.28
lead_s = norm(lead) * 0.8 + reverb(lead, 1.8) * 0.18
pad_s = fft_filter(norm(pad), 160, 4500)                   # keep pad out of the 808's way
duck = 1 - 0.45 * np.clip(np.abs(b808) + np.abs(drums) * 0.3, 0, 1)
pad_s *= duck

stems = {
    "choir": norm(choir_s) * 0.95,
    "lead": norm(lead_s) * 0.5,
    "pad": norm(pad_s) * 0.34,
    "drums": norm(drums) * 0.72,
    "808": norm(b808) * 0.62,
}

end = int(NB * BAR * SR)
tail = len(stems["drums"]) - end
for k in stems:
    stems[k][end:] *= np.linspace(1, 0, tail)

mix = sum(stems.values())
# saturating master glue: drive into tanh, ceiling -0.3 dBFS (not peak-normalized flat)
drive = 1.6
master = np.tanh(drive * mix) / np.tanh(drive) * 10 ** (-0.3 / 20)
master = master / max(1.0, np.abs(master).max() / 10 ** (-0.3 / 20))


def write24(path, mono):
    x = np.clip(mono, -1, 1)
    i = (x * 8388607).astype(np.int32)
    st = np.column_stack([i, i]).ravel()
    b = np.zeros((len(st), 3), np.uint8)
    b[:, 0] = st & 0xFF; b[:, 1] = (st >> 8) & 0xFF; b[:, 2] = (st >> 16) & 0xFF
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR)
        w.writeframes(b.tobytes())


title = "nocap - Little David 97 (Emin)"
write24(os.path.join(OUT, f"{title}.wav"), master)
for k, v in stems.items():
    write24(os.path.join(OUT, "stems", f"Little David 97 - {k}.wav"), v)

rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x[: end] ** 2)) + 1e-12)
print(f"{NB} bars, {len(master)/SR:.1f}s; master RMS {rms(master):.1f} dBFS, peak {20*np.log10(np.abs(master).max()):.2f} dBFS")
for k, v in stems.items():
    print(f"  {k:6s} RMS {rms(v):.1f} dBFS  peak {20*np.log10(np.abs(v).max()+1e-12):.1f}")
