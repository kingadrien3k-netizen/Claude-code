"""TikTok Content Posting API: upload a video and post it with a caption.

Docs: https://developers.tiktok.com/doc/content-posting-api-get-started
- "direct" mode needs the video.publish scope and sets the caption.
- "draft" mode needs video.upload; the video lands in your TikTok inbox and
  you add the caption in the app (the API can't set one in this mode).
- Until TikTok audits your app, direct posts must use privacy SELF_ONLY.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from .tokens import TokenStore

log = logging.getLogger("clipbot.tiktok")

API = "https://open.tiktokapis.com/v2"
AUTHORIZE = "https://www.tiktok.com/v2/auth/authorize/"
SCOPES = "user.info.basic,video.publish,video.upload"

MB = 1024 * 1024
MAX_SINGLE_CHUNK = 64 * MB
CHUNK = 10 * MB


class TikTokError(RuntimeError):
    pass


def auth_url(cfg: dict, state: str) -> str:
    q = requests.models.PreparedRequest()
    q.prepare_url(AUTHORIZE, {
        "client_key": cfg["client_key"],
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": cfg["redirect_uri"],
        "state": state,
    })
    return q.url


def exchange_code(cfg: dict, code: str) -> dict:
    r = requests.post(f"{API}/oauth/token/", data={
        "client_key": cfg["client_key"],
        "client_secret": cfg["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": cfg["redirect_uri"],
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
    body = r.json()
    if not r.ok or "access_token" not in body:
        raise TikTokError(f"token exchange failed: {body}")
    return body


def chunk_plan(size: int) -> tuple[int, int]:
    """(chunk_size, chunk_count) following TikTok's rules: small files go in one
    chunk; otherwise fixed-size chunks with the last chunk absorbing the remainder."""
    if size <= 0:
        raise ValueError("empty video")
    if size <= MAX_SINGLE_CHUNK:
        return size, 1
    return CHUNK, size // CHUNK


class TikTok:
    def __init__(self, cfg: dict, tokens: TokenStore):
        self.cfg = cfg
        self.tokens = tokens
        self.http = requests.Session()

    def _refresh(self) -> None:
        refresh = self.tokens.get("tiktok").get("refresh_token")
        if not refresh:
            raise TikTokError("no TikTok token; run: python -m clipbot auth tiktok")
        r = self.http.post(f"{API}/oauth/token/", data={
            "client_key": self.cfg["client_key"],
            "client_secret": self.cfg["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
        body = r.json()
        if "access_token" not in body:
            raise TikTokError(f"TikTok token refresh failed: {body}; run auth again")
        self.tokens.set("tiktok", body)
        log.info("refreshed TikTok token")

    def _post(self, path: str, payload: dict) -> dict:
        if self.tokens.expiring("tiktok"):
            self._refresh()
        r = self.http.post(f"{API}{path}", json=payload, timeout=30, headers={
            "Authorization": f"Bearer {self.tokens.get('tiktok')['access_token']}",
            "Content-Type": "application/json; charset=UTF-8",
        })
        body = r.json()
        err = body.get("error", {})
        if err.get("code", "ok") != "ok":
            raise TikTokError(f"{path}: {err.get('code')} - {err.get('message')}")
        return body.get("data", {})

    def creator_info(self) -> dict:
        return self._post("/post/publish/creator_info/query/", {})

    def upload(self, video: Path, caption: str, mode: str | None = None) -> str:
        """Uploads the file and returns TikTok's publish_id."""
        mode = mode or self.cfg["mode"]
        size = video.stat().st_size
        chunk_size, count = chunk_plan(size)
        source = {"source": "FILE_UPLOAD", "video_size": size,
                  "chunk_size": chunk_size, "total_chunk_count": count}

        if mode == "direct":
            info = self.creator_info()
            privacy = self.cfg["privacy_level"]
            options = info.get("privacy_level_options", [])
            if options and privacy not in options:
                raise TikTokError(f"privacy_level {privacy} not allowed; account allows {options}")
            data = self._post("/post/publish/video/init/", {
                "post_info": {
                    "title": caption,
                    "privacy_level": privacy,
                    "disable_comment": self.cfg["disable_comment"] or info.get("comment_disabled", False),
                    "disable_duet": self.cfg["disable_duet"] or info.get("duet_disabled", False),
                    "disable_stitch": self.cfg["disable_stitch"] or info.get("stitch_disabled", False),
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": source,
            })
        elif mode == "draft":
            data = self._post("/post/publish/inbox/video/init/", {"source_info": source})
        else:
            raise TikTokError(f"unknown tiktok mode {mode!r} (use direct or draft)")

        self._put_chunks(data["upload_url"], video, size, chunk_size, count)
        return data["publish_id"]

    def _put_chunks(self, url: str, video: Path, size: int, chunk_size: int, count: int) -> None:
        with video.open("rb") as f:
            for i in range(count):
                start = i * chunk_size
                end = size - 1 if i == count - 1 else start + chunk_size - 1
                f.seek(start)
                body = f.read(end - start + 1)
                r = self.http.put(url, data=body, timeout=300, headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(body)),
                    "Content-Range": f"bytes {start}-{end}/{size}",
                })
                if r.status_code not in (200, 201, 206):
                    raise TikTokError(f"chunk {i + 1}/{count} upload failed: {r.status_code} {r.text}")

    def wait_for_status(self, publish_id: str, timeout: float = 300) -> str:
        deadline = time.time() + timeout
        status = "UNKNOWN"
        while time.time() < deadline:
            data = self._post("/post/publish/status/fetch/", {"publish_id": publish_id})
            status = data.get("status", "UNKNOWN")
            if status == "FAILED":
                raise TikTokError(f"TikTok rejected the post: {data.get('fail_reason')}")
            if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
                return status
            time.sleep(5)
        return status
