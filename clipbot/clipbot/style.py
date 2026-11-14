"""'Pro' render style, modelled on what big clip channels post:

- layout "center": full-bleed 9:16 crop on the streamer (IRL / just-chatting streams)
- layout "split":  facecam on top, gameplay below
- layout "blur":   whole frame over a blurred copy (safe default)
- word-by-word captions: 2-3 words at a time, current word highlighted and popping
- hook title in a white box at the top
- a quick zoom punch-in on the loudest moment
"""
from __future__ import annotations

import array
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("clipbot.style")

W, H = 1080, 1920


@dataclass
class Word:
    start: float
    end: float
    text: str


# --------------------------------------------------------------------------- audio
def probe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def loudest_moment(path: Path, window: float = 0.5) -> float | None:
    """Timestamp (seconds) of the loudest half-second: usually the scream/reaction."""
    rate = 8000
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate),
                           "-f", "s16le", "-"], capture_output=True)
    if proc.returncode or not proc.stdout:
        return None
    samples = array.array("h")
    samples.frombytes(proc.stdout[: len(proc.stdout) // 2 * 2])
    step = int(rate * window)
    best_t, best_e = None, -1.0
    for i in range(0, len(samples) - step, step):
        chunk = samples[i:i + step]
        energy = sum(s * s for s in chunk[::4]) / (len(chunk) / 4)
        if energy > best_e:
            best_t, best_e = i / rate, energy
    return best_t


# --------------------------------------------------------------------------- speech
def transcribe(path: Path, model_size: str = "base") -> list[Word]:
    """Word timings via faster-whisper. Returns [] if it isn't installed."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log.warning("faster-whisper not installed; no spoken captions (pip install faster-whisper)")
        return []
    model = WhisperModel(model_size, device="auto", compute_type="int8")
    segments, _ = model.transcribe(str(path), word_timestamps=True, vad_filter=True)
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append(Word(w.start, w.end, text))
    return words


# --------------------------------------------------------------------------- captions
def _ts(t: float) -> str:
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02}:{t % 60:05.2f}"


def _esc(text: str) -> str:
    # The bundled fonts have no emoji glyphs; drop them instead of drawing boxes.
    text = "".join(ch for ch in text if ord(ch) < 0x2000).strip()
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def group_words(words: list[Word], max_words: int = 3, max_chars: int = 16, max_gap: float = 0.6):
    groups, cur = [], []
    for w in words:
        too_long = len(" ".join(x.text for x in cur + [w])) > max_chars
        gap = cur and w.start - cur[-1].end > max_gap
        if cur and (len(cur) >= max_words or too_long or gap):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def build_ass(words: list[Word], hook: str | None, duration: float, caption_y: int,
              font: str = "DejaVu Sans", highlight: str = "&H0000E5FF&") -> str:
    """ASS subtitle script. Colours are &HBBGGRR&; default highlight is yellow."""
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,{font},92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,4,5,40,40,0,1",
        f"Style: Hook,{font},58,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,22,0,8,90,90,150,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if hook:
        lines.append(f"Dialogue: 1,{_ts(0)},{_ts(duration)},Hook,,0,0,0,,{_esc(hook)}")
    pos = f"\\pos({W // 2},{caption_y})"
    for group in group_words(words):
        for i, w in enumerate(group):
            start = w.start
            end = group[i + 1].start if i + 1 < len(group) else w.end + 0.15
            parts = []
            for j, other in enumerate(group):
                t = _esc(other.text.upper())
                if j == i:  # active word: highlighted, pops from 115% to 100%
                    t = (f"{{\\c{highlight}\\fscx115\\fscy115\\t(0,90,\\fscx100\\fscy100)}}"
                         f"{t}{{\\c&H00FFFFFF&\\fscx100\\fscy100}}")
                parts.append(t)
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Cap,,0,0,0,,{{{pos}}}{' '.join(parts)}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- video
def layout_filter(layout: str, facecam: tuple[float, float, float, float] | None,
                  focus_x: float = 0.5) -> tuple[str, int]:
    """filter_complex producing [lay] at 1080x1920, and the caption y position."""
    if layout == "center":
        # Fill the height, then crop a 9:16 window around focus_x (0=left, 1=right).
        return (f"[0:v]scale=-2:{H},crop={W}:{H}:'(iw-{W})*{focus_x}':0,setsar=1[lay]", int(H * 0.68))
    if layout == "split":
        if not facecam:
            raise ValueError("split layout needs facecam=x,y,w,h (fractions of the frame)")
        x, y, w, h = facecam
        top_h, bot_h = int(H * 0.4), H - int(H * 0.4)
        return (
            f"[0:v]split[a][b];"
            f"[a]crop=iw*{w}:ih*{h}:iw*{x}:ih*{y},scale={W}:{top_h}:force_original_aspect_ratio=increase,"
            f"crop={W}:{top_h},setsar=1[cam];"
            f"[b]scale=-2:{bot_h},crop={W}:{bot_h},setsar=1[game];"
            f"[cam][game]vstack[lay]",
            top_h,  # captions sit on the seam between facecam and gameplay
        )
    return (
        f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=25:2[bg];"
        f"[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[lay]",
        int(H * 0.72),
    )


def render_pro(src: Path, dst: Path, hook: str | None = None, *, layout: str = "center",
               facecam=None, focus_x: float = 0.5, words: list[Word] | None = None,
               transcribe_audio: bool = True, punch: bool = True, font: str = "DejaVu Sans",
               whisper_model: str = "base") -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(src)
    if words is None:
        words = transcribe(src, whisper_model) if transcribe_audio else []

    graph, caption_y = layout_filter(layout, facecam, focus_x)
    last = "lay"
    if punch:
        peak = loudest_moment(src)
        if peak is not None:
            a, b = max(peak - 0.2, 0), peak + 1.6
            # snap in to 118% over 0.15s, hold, snap back out
            z = f"if(between(it,{a:.2f},{b:.2f}),1+0.18*min((it-{a:.2f})/0.15,1),1)"
            graph += (f";[lay]zoompan=z='{z}':d=1:x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
                      f":s={W}x{H}:fps=30[zm]")
            last = "zm"

    fd, ass_path = tempfile.mkstemp(suffix=".ass")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(build_ass(words, hook, duration, caption_y, font))
    graph += f";[{last}]ass='{ass_path}'[v]"

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", graph,
           "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           str(dst)]
    try:
        subprocess.run(cmd, check=True)
    finally:
        os.unlink(ass_path)
    return dst
