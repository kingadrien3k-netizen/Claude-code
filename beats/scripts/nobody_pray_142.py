"""nocap — "Nobody Pray 142" — ghetto gospel lane.
Choir: Fisk University Jubilee Singers, "I Couldn't Hear Nobody Pray" (Victor, 1909), public domain (US).
Outputs: master WAV (24-bit), MP3, stems (choir/lead/pad/drums/808) as 24-bit WAVs.
"""
import os
import sys
import wave
import numpy as np

SR = 44100
BPM = 142
STEP = 60 / BPM / 4
BAR = 16 * STEP
rng = np.random.default_rng(1909)
CHOP_SRC = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(os.path.join(OUT, "stems"), exist_ok=True)

LAYOUT = [("intro", 4), ("verse", 16), ("hook", 8), ("verse", 16), ("hook", 8),
          ("bridge", 8), ("hook", 8), ("outro", 4)]
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
# recording runs ~ +38 cents sharp (78rpm speed) -> retune down to true F#
ratio = 2 ** (37.6 / 1200)
pos = np.arange(0, len(src) - 1, 1 / ratio)
src = np.interp(pos, np.arange(len(src)), src)
src = fft_filter(src, 140, 6500)
T = lambda s: int(s * ratio * SR)     # original-recording seconds -> retuned samples

intro_chop = src[T(144.0):T(144.0) + int(4 * BAR * SR) + int(0.6 * SR)].copy()
fade = int(0.08 * SR)
intro_chop[:fade] *= np.linspace(0, 1, fade)
intro_chop[-int(0.6 * SR):] *= np.linspace(1, 0, int(0.6 * SR))

# short stabs for the bridge breakdown (sustained chord moments)
def stab(start, dur):
    s = src[T(start):T(start) + int(dur * SR)].copy()
    a = int(0.006 * SR); r = int(0.05 * SR)
    s[:a] *= np.linspace(0, 1, a); s[-r:] *= np.linspace(1, 0, r)
    return s

STABS = [stab(148.2, 4 * STEP), stab(149.6, 3 * STEP), stab(150.6, 6 * STEP), stab(131.1, 8 * STEP)]

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
# D#m7 | Bmaj7 | F#/A# | C#   (F# major / D# minor — the chop's native key)
CH = [
    dict(pad=[51, 54, 58, 61], root=39),   # D#m7: D#3 F#3 A#3 C#4, 808 D#2
    dict(pad=[47, 51, 54, 58], root=35),   # Bmaj7
    dict(pad=[46, 49, 54, 58], root=34),   # F#/A#
    dict(pad=[49, 53, 56, 61], root=37),   # C# (E# = F)
]
# (midi, start step, length in steps) — CALL bars 1-2, RESPONSE bars 3-4
CALL = [[(70, 0, 3), (73, 3, 3), (70, 6, 2), (68, 10, 2), (66, 12, 4)],
        [(63, 0, 6), (66, 8, 2), (68, 11, 5)]]
RESP = [[(73, 0, 3), (70, 3, 3), (68, 6, 2), (66, 8, 2), (63, 12, 4)],
        [(66, 0, 4), (65, 4, 2), (66, 6, 10)]]
RUN = [(66, 12, 1), (68, 13, 1), (70, 14, 1), (73, 15, 1)]     # verse fill into next phrase
KICK_A = [0, 5, 11]
KICK_B = [0, 2, 9, 13]

choir = np.zeros(N); lead = np.zeros(N); pad = np.zeros(N); drums = np.zeros(N); b808 = np.zeros(N)

add(choir, intro_chop, 0, 1.0)

for b, sec in enumerate(SECS):
    t0 = b * BAR
    ch = CH[b % 4]
    nxt = SECS[b + 1] if b + 1 < NB else None
    into_hook = nxt == "hook" and sec != "hook"
    phrase_bar = b % 4

    # ---- pad (organ chord bed) ----
    if sec != "bridge":
        g = {"intro": 0.25, "verse": 0.55, "hook": 0.8, "outro": 0.5}[sec]
        for m in ch["pad"]:
            add(pad, organ(midi(m), BAR + 0.02, bars=(0.5, 1, 2), lv=(0.7, 1, 0.25),
                           leslie=0.9, click=0.05), t0, g * 0.25)

    # ---- lead organ ----
    if sec == "hook":
        motif = (CALL + RESP)[phrase_bar]
        oct_ = 0 if phrase_bar < 2 else -12          # response answers an octave down
        for m, s, L in motif:
            add(lead, organ(midi(m + oct_), L * STEP + 0.04, perc=0.6,
                            lv=(0.4, 1.0, 0.8, 0.6, 0.35)), t0 + s * STEP, 0.32)
    elif sec == "verse" and b % 8 == 7:
        for m, s, L in RUN:
            add(lead, organ(midi(m), L * STEP + 0.03, perc=0.6,
                            lv=(0.4, 1.0, 0.8, 0.6, 0.35)), t0 + s * STEP, 0.22)

    # ---- choir breakdown in bridge ----
    if sec == "bridge":
        hits = [(0, 0), (3, 1), (6, 2), (10, 0), (12, 1)] if b % 2 == 0 else [(0, 3), (8, 2), (11, 1), (14, 0)]
        for s, k in hits:
            add(choir, STABS[k], t0 + s * STEP, 0.9)

    if sec in ("intro", "outro"):
        if sec == "intro" and b == 3:                 # snare roll out of the choir into verse 1
            for k in range(8):
                add(drums, SN, t0 + (8 + k) * STEP, 0.15 + 0.06 * k)
        continue

    # ---- drums (knock) ----
    kp = KICK_A if b % 2 == 0 else KICK_B
    for s in kp:
        add(drums, K, t0 + s * STEP, 1.0)
    add(drums, SN, t0 + 8 * STEP, 0.95)
    if b % 4 == 3 and not into_hook:
        add(drums, SN, t0 + 15 * STEP, 0.35)          # ghost

    if into_hook:                                     # snare roll into the hook
        for k in range(8):
            add(drums, SN, t0 + (8 + k) * STEP, 0.25 + 0.09 * k)
        for k in range(8):
            add(drums, SN, t0 + (12 + k * 0.5) * STEP, 0.3 + 0.07 * k)

    # rolling 16th hats (bridge: half the hats, choir carries it)
    for s in range(16):
        if sec == "bridge" and s % 2:
            continue
        vel = [0.42, 0.18, 0.28, 0.2][s % 4]
        add(drums, H, t0 + s * STEP, vel)
    if sec == "hook" and b % 2 == 1:
        for k in range(6):
            add(drums, H, t0 + (12 + k * 2 / 3) * STEP, 0.22 + 0.03 * k)   # triplet roll
    if sec == "hook":
        add(drums, OH, t0 + 6 * STEP, 0.18)
    if sec == "verse" and b % 4 == 2:
        for k in range(4):
            add(drums, H, t0 + (14 + k * 0.5) * STEP, 0.2)                 # 32nd flick

    # ---- 808 ----
    if sec == "hook":                                  # follows the roots, slides
        for i, s in enumerate(kp):
            end = kp[i + 1] if i + 1 < len(kp) else 16
            slide = None
            note = ch["root"]
            if i == len(kp) - 1 and phrase_bar == 3:
                slide = midi(note + 7)
            if i == 1 and b % 2:
                note += 12; slide = midi(ch["root"])
            add(b808, bass808(midi(note), (end - s) * STEP + 0.02, slide), t0 + s * STEP, 1.0)
    elif sec == "verse":                               # verses: sparse 808 on the one
        add(b808, bass808(midi(ch["root"]), 7 * STEP), t0, 0.85)
    elif sec == "bridge" and b % 2 == 0:
        add(b808, bass808(midi(ch["root"]), 10 * STEP, drive=2), t0, 0.6)

# ================= MIX =================
def reverb(x, secs=2.4, lo=200, hi=5500, decay=2.6):
    n = int(secs * SR)
    ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * decay)
    ir = fft_filter(ir, lo, hi)
    L = len(x) + n
    return norm(np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[: len(x)])


choir_s = norm(choir) * 0.8 + reverb(choir, 3.0) * 0.28
lead_s = norm(lead) * 0.8 + reverb(lead, 1.8) * 0.18
pad_s = fft_filter(norm(pad), 160, 4500)                   # keep pad out of the 808's way
duck = 1 - 0.45 * np.clip(np.abs(b808) + np.abs(drums) * 0.3, 0, 1)
pad_s *= duck

stems = {
    "choir": norm(choir_s) * 0.95,
    "lead": norm(lead_s) * 0.42,
    "pad": norm(pad_s) * 0.26,
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


title = "nocap - Nobody Pray 142 (F#maj-D#m)"
write24(os.path.join(OUT, f"{title}.wav"), master)
for k, v in stems.items():
    write24(os.path.join(OUT, "stems", f"Nobody Pray 142 - {k}.wav"), v)

rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x[: end] ** 2)) + 1e-12)
print(f"{NB} bars, {len(master)/SR:.1f}s; master RMS {rms(master):.1f} dBFS, peak {20*np.log10(np.abs(master).max()):.2f} dBFS")
for k, v in stems.items():
    print(f"  {k:6s} RMS {rms(v):.1f} dBFS  peak {20*np.log10(np.abs(v).max()+1e-12):.1f}")
