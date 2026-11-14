"""Main loop: watch chat, clip spikes, render vertical videos, post to TikTok."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from . import captions, video
from .chat import read_chat
from .detector import SpikeDetector, Trigger
from .store import Store
from .tiktok import TikTok
from .tokens import TokenStore
from .twitch import Twitch, download_clip

log = logging.getLogger("clipbot")

LIVE_POLL_SECONDS = 60


class Bot:
    def __init__(self, cfg: dict, dry_run: bool = False, no_upload: bool = False):
        self.cfg = cfg
        self.dry_run = dry_run
        self.no_upload = no_upload
        self.tokens = TokenStore(cfg["paths"]["tokens_file"])
        self.twitch = Twitch(cfg["twitch"], self.tokens)
        self.tiktok = TikTok(cfg["tiktok"], self.tokens)
        self.store = Store(cfg["paths"]["db_file"])
        self.clips_dir = Path(cfg["paths"]["clips_dir"])
        self.channels = {c["name"]: c for c in cfg["channels"]}
        self.detectors = {n: SpikeDetector(cfg["detector"]) for n in self.channels}
        self.live: dict[str, dict] = {}
        self.ids: dict[str, str] = {}
        self.upload_lock = asyncio.Lock()
        self.tasks: set[asyncio.Task] = set()

    async def run(self) -> None:
        if not self.channels:
            raise SystemExit("no channels in config.yaml")
        self.ids = await asyncio.to_thread(self.twitch.user_ids, list(self.channels))
        log.info("watching %d channels%s", len(self.ids), " (dry run)" if self.dry_run else "")
        await asyncio.gather(
            read_chat(list(self.ids), self.on_message),
            self.poll_live(),
            self.tick(),
        )

    def on_message(self, channel: str, user: str, text: str) -> None:
        det = self.detectors.get(channel)
        if det:
            det.add(text)

    async def poll_live(self) -> None:
        while True:
            try:
                now_live = await asyncio.to_thread(self.twitch.live_streams, list(self.ids))
                for name in now_live.keys() - self.live.keys():
                    log.info("%s went live: %s", name, now_live[name].get("title", ""))
                    self.detectors[name] = SpikeDetector(self.cfg["detector"])  # fresh baseline
                for name in self.live.keys() - now_live.keys():
                    log.info("%s went offline", name)
                self.live = now_live
            except Exception as exc:  # noqa: BLE001
                log.warning("live check failed: %s", exc)
            await asyncio.sleep(LIVE_POLL_SECONDS)

    async def tick(self) -> None:
        while True:
            await asyncio.sleep(1)
            for name in list(self.live):
                trig = self.detectors[name].check()
                if trig:
                    t = asyncio.create_task(self.handle(name, trig))
                    self.tasks.add(t)
                    t.add_done_callback(self.tasks.discard)

    async def handle(self, name: str, trig: Trigger) -> None:
        log.info("[%s] %s: %d msgs (%.1f/s vs %.1f/s normal), top: %s",
                 name, trig.reason, trig.messages, trig.rate, trig.baseline, ", ".join(trig.top_terms))
        if self.dry_run:
            return
        clip_id = None
        try:
            clip_id = await asyncio.to_thread(self.twitch.create_clip, self.ids[name])
            self.store.add(clip_id, name, trig.reason)
            clip = await asyncio.to_thread(self.twitch.wait_for_clip, clip_id)
            self.store.update(clip_id, clip_url=clip["url"], status="clipped")
            log.info("[%s] clip ready: %s", name, clip["url"])

            raw = self.clips_dir / "raw" / f"{name}_{clip_id}.mp4"
            await asyncio.to_thread(download_clip, clip["url"], raw)

            game = self.live.get(name, {}).get("game_name")
            hook, caption = captions.build(name, game, trig, self.cfg["captions"],
                                           self.channels[name]["hashtags"])
            out = self.clips_dir / "tiktok" / f"{name}_{clip_id}.mp4"
            await asyncio.to_thread(video.render, raw, out, hook, self.cfg["video"])
            out.with_suffix(".txt").write_text(caption + "\n")
            self.store.update(clip_id, video_path=str(out), caption=caption, status="rendered")
            log.info("[%s] rendered %s", name, out)

            await self.maybe_post(name, clip_id, out, caption)
        except Exception as exc:  # noqa: BLE001
            log.error("[%s] failed: %s", name, exc)
            if clip_id:
                self.store.update(clip_id, status="error", error=str(exc))

    async def maybe_post(self, name: str, clip_id: str, path: Path, caption: str) -> None:
        tk = self.cfg["tiktok"]
        if self.no_upload or not tk["enabled"]:
            return
        if not self.channels[name]["tiktok"]:
            log.info("[%s] not posting: tiktok is off for this channel", name)
            return
        async with self.upload_lock:
            if self.store.posts_last_24h() >= tk["max_posts_per_day"]:
                log.info("[%s] not posting: daily limit of %d reached", name, tk["max_posts_per_day"])
                return
            publish_id = await asyncio.to_thread(self.tiktok.upload, path, caption)
            self.store.update(clip_id, publish_id=publish_id, status="uploading")
            status = await asyncio.to_thread(self.tiktok.wait_for_status, publish_id)
            self.store.update(clip_id, status=status.lower())
            log.info("[%s] TikTok: %s", name, status)
