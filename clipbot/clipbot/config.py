"""Loads config.yaml and fills in defaults."""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

DEFAULTS = {
    "twitch": {
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "http://localhost:8765/callback",
    },
    "channels": [],
    "detector": {
        "window_seconds": 12,        # how much recent chat counts as "right now"
        "baseline_seconds": 300,     # how much history counts as "normal"
        "spike_ratio": 3.0,          # right-now rate must be this many times normal
        "min_messages": 15,          # ...and at least this many messages in the window
        "keyword_hits": 8,           # OR this many hype keywords/emotes in the window
        "cooldown_seconds": 180,     # min gap between clips on one channel
        "warmup_seconds": 90,        # learn the baseline before clipping
        "keywords": [
            "clip", "clip it", "clip that", "LUL", "LULW", "KEKW", "OMEGALUL",
            "LMAO", "LMFAO", "POG", "Pog", "PogChamp", "PogU", "POGGERS",
            "W", "WW", "HUH", "monkaS", "no way", "NO SHOT", "LETS GO",
        ],
    },
    "video": {
        "vertical": True,
        "burn_caption": True,
        "font_file": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    },
    "captions": {
        "hashtags": ["twitch", "twitchclips", "streamer", "fyp"],
        "credit": True,
    },
    "tiktok": {
        "enabled": False,
        "client_key": "",
        "client_secret": "",
        "redirect_uri": "",
        "mode": "direct",            # direct = post with caption; draft = send to inbox
        "privacy_level": "SELF_ONLY",
        "max_posts_per_day": 5,
        "disable_comment": False,
        "disable_duet": False,
        "disable_stitch": False,
    },
    "paths": {
        "clips_dir": "clips",
        "tokens_file": "tokens.json",
        "db_file": "clipbot.db",
    },
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def normalize_channels(raw: list) -> list[dict]:
    """Channels may be plain names or {name, tiktok, hashtags} dicts."""
    channels = []
    for entry in raw or []:
        if isinstance(entry, str):
            entry = {"name": entry}
        channels.append({
            "name": entry["name"].lower().lstrip("#"),
            "tiktok": bool(entry.get("tiktok", False)),
            "hashtags": list(entry.get("hashtags", [])),
        })
    return channels


def load(path: str | Path) -> dict:
    path = Path(path)
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    cfg = _merge(DEFAULTS, data or {})
    cfg["channels"] = normalize_channels(cfg["channels"])
    base = path.resolve().parent
    for key, value in cfg["paths"].items():
        p = Path(value)
        cfg["paths"][key] = str(p if p.is_absolute() else base / p)
    return cfg
