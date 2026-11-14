"""Decides when chat activity means "something clip-worthy just happened"."""
from __future__ import annotations

import re
import time
from collections import Counter, deque
from dataclasses import dataclass, field


@dataclass
class Trigger:
    reason: str            # "spike" or "keywords"
    messages: int          # messages in the current window
    rate: float            # messages/second right now
    baseline: float        # normal messages/second
    keyword_hits: int
    top_terms: list[str] = field(default_factory=list)


class SpikeDetector:
    """One per channel. Feed it messages, call check() about once a second."""

    def __init__(self, cfg: dict, clock=time.monotonic):
        self.cfg = cfg
        self.clock = clock
        self.started = clock()
        self.last_clip = float("-inf")
        self.events: deque[tuple[float, str, bool]] = deque()
        self._keywords = [k.lower() for k in cfg["keywords"]]
        self._kw_re = re.compile(
            r"(?<!\w)(" + "|".join(re.escape(k) for k in sorted(self._keywords, key=len, reverse=True)) + r")(?!\w)",
            re.IGNORECASE,
        ) if self._keywords else None

    def is_keyword(self, text: str) -> bool:
        return bool(self._kw_re and self._kw_re.search(text))

    def add(self, text: str, now: float | None = None) -> None:
        now = self.clock() if now is None else now
        self.events.append((now, text, self.is_keyword(text)))
        horizon = now - self.cfg["baseline_seconds"]
        while self.events and self.events[0][0] < horizon:
            self.events.popleft()

    def check(self, now: float | None = None) -> Trigger | None:
        now = self.clock() if now is None else now
        c = self.cfg
        if now - self.started < c["warmup_seconds"]:
            return None
        if now - self.last_clip < c["cooldown_seconds"]:
            return None

        window_start = now - c["window_seconds"]
        baseline_start = now - c["baseline_seconds"]
        recent = [e for e in self.events if e[0] >= window_start]
        older = [e for e in self.events if baseline_start <= e[0] < window_start]

        n = len(recent)
        rate = n / c["window_seconds"]
        older_span = min(c["baseline_seconds"], now - self.started) - c["window_seconds"]
        baseline = len(older) / older_span if older_span > 0 else 0.0
        # A quiet chat shouldn't trigger on 3 messages; floor the baseline.
        floor = c["min_messages"] / c["window_seconds"] / c["spike_ratio"]
        kw = sum(1 for e in recent if e[2])

        reason = None
        if n >= c["min_messages"] and rate >= c["spike_ratio"] * max(baseline, floor):
            reason = "spike"
        elif kw >= c["keyword_hits"]:
            reason = "keywords"
        if not reason:
            return None

        self.last_clip = now
        return Trigger(reason, n, rate, baseline, kw, top_terms(t for _, t, _ in recent))


def top_terms(messages, limit: int = 3) -> list[str]:
    """Most-repeated words/emotes in a batch of chat messages."""
    counts: Counter[str] = Counter()
    for msg in messages:
        # count each word once per message so one spammer doesn't dominate
        counts.update({w for w in re.findall(r"[\w']+", msg) if len(w) > 1})
    return [w for w, _ in counts.most_common(limit)]
