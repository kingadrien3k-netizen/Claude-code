"""Builds the on-video hook text and the TikTok post caption."""
from __future__ import annotations

import random
import re

from .detector import Trigger

FUNNY = {"lul", "lulw", "kekw", "omegalul", "lmao", "lmfao", "lol", "xd", "icant", "pepelaugh"}
HYPE = {"pog", "pogchamp", "pogu", "poggers", "w", "ww", "lets", "go", "goat", "insane", "clean"}
SHOCK = {"huh", "monkas", "what", "no", "way", "shot", "wtf", "bruh"}

HOOKS = {
    "funny": ["{s} had chat CRYING", "chat could not breathe after this", "{s} why would you do that",
              "this is why I watch {s}"],
    "hype": ["{s} just went CRAZY", "nobody expected {s} to pull this off", "{s} is HIM",
             "chat lost it when {s} did this"],
    "shock": ["wait... what just happened", "{s} did NOT see that coming", "chat was NOT ready",
              "{s} can't believe it"],
    "default": ["chat went wild for this {s} moment", "{s} moment chat won't forget",
                "you had to be there... so here it is"],
}
TIKTOK_TITLE_LIMIT = 2200


def mood(trigger: Trigger) -> str:
    terms = {t.lower() for t in trigger.top_terms}
    for name, words in (("funny", FUNNY), ("hype", HYPE), ("shock", SHOCK)):
        if terms & words:
            return name
    return "default"


def _tag(text: str) -> str:
    return "#" + re.sub(r"[^\w]", "", text.lower())


def build(streamer: str, game: str | None, trigger: Trigger, cfg: dict,
          extra_tags: list[str] = (), rng: random.Random | None = None) -> tuple[str, str]:
    """Returns (hook_text_for_video, tiktok_caption)."""
    rng = rng or random.Random()
    hook = rng.choice(HOOKS[mood(trigger)]).format(s=streamer)

    tags = [_tag(streamer)]
    if game:
        tags.append(_tag(game))
    tags += [_tag(t) for t in [*extra_tags, *cfg.get("hashtags", [])]]
    tags = list(dict.fromkeys(t for t in tags if len(t) > 1))  # dedupe, keep order

    parts = [hook]
    if cfg.get("credit", True):
        parts.append(f"🎥 twitch.tv/{streamer}")
    parts.append(" ".join(tags))
    caption = "\n".join(parts)[:TIKTOK_TITLE_LIMIT]
    return hook, caption
