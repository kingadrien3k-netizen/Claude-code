"""Turns a 16:9 Twitch clip into a 9:16 TikTok video with optional burned-in text."""
from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
from pathlib import Path

W, H = 1080, 1920


def _ascii_safe(text: str) -> str:
    # The default font has no emoji; drop characters it can't draw.
    return "".join(ch for ch in text if ord(ch) < 0x2000).strip()


def render(src: Path, dst: Path, hook: str | None, cfg: dict) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    filters = []
    if cfg.get("vertical", True):
        # Blurred, zoomed copy fills the background; the real clip sits in the middle.
        filters.append(
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=25:2[bg];"
            f"[0:v]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v0]"
        )
    else:
        filters.append("[0:v]null[v0]")

    textfiles = []
    font = cfg.get("font_file")
    text = _ascii_safe(hook or "") if cfg.get("burn_caption", True) else ""
    if text and font and os.path.exists(font):
        # One drawtext per line so every line is centered on its own.
        # Text goes through files so quotes/colons in it never break the filter.
        size, step = 72, 92
        draws = []
        for i, line in enumerate(textwrap.wrap(text.upper(), 16)[:4]):
            fd, path = tempfile.mkstemp(suffix=".txt")
            with os.fdopen(fd, "w") as f:
                f.write(line)
            textfiles.append(path)
            draws.append(f"drawtext=fontfile='{font}':textfile='{path}':fontsize={size}:fontcolor=white:"
                         f"borderw=7:bordercolor=black:x=(w-text_w)/2:y=h*0.12+{i * step}")
        filters.append("[v0]" + ",".join(draws) + "[v]")
    else:
        filters.append("[v0]null[v]")

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
        "-filter_complex", ";".join(filters),
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", "30", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True)
    finally:
        for path in textfiles:
            os.unlink(path)
    return dst
