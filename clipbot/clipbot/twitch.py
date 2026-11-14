"""Twitch Helix API: live status, creating clips and downloading them."""
from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path

import requests

from .tokens import TokenStore

log = logging.getLogger("clipbot.twitch")

HELIX = "https://api.twitch.tv/helix"
OAUTH = "https://id.twitch.tv/oauth2"
SCOPES = "clips:edit"


class TwitchError(RuntimeError):
    pass


def auth_url(cfg: dict, state: str) -> str:
    q = requests.models.PreparedRequest()
    q.prepare_url(f"{OAUTH}/authorize", {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "scope": SCOPES,
        "state": state,
    })
    return q.url


def exchange_code(cfg: dict, code: str) -> dict:
    r = requests.post(f"{OAUTH}/token", data={
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": cfg["redirect_uri"],
    }, timeout=20)
    if not r.ok:
        raise TwitchError(f"token exchange failed: {r.status_code} {r.text}")
    return r.json()


class Twitch:
    def __init__(self, cfg: dict, tokens: TokenStore):
        self.cfg = cfg
        self.tokens = tokens
        self.http = requests.Session()

    # --- auth -------------------------------------------------------------
    def _refresh(self) -> None:
        refresh = self.tokens.get("twitch").get("refresh_token")
        if not refresh:
            raise TwitchError("no Twitch token; run: python -m clipbot auth twitch")
        r = self.http.post(f"{OAUTH}/token", data={
            "client_id": self.cfg["client_id"],
            "client_secret": self.cfg["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        }, timeout=20)
        if not r.ok:
            raise TwitchError(f"Twitch token refresh failed ({r.status_code}); run auth again")
        self.tokens.set("twitch", r.json())
        log.info("refreshed Twitch token")

    def _request(self, method: str, path: str, **kw) -> requests.Response:
        if self.tokens.expiring("twitch"):
            self._refresh()
        for attempt in range(2):
            headers = {
                "Client-Id": self.cfg["client_id"],
                "Authorization": f"Bearer {self.tokens.get('twitch')['access_token']}",
            }
            r = self.http.request(method, HELIX + path, headers=headers, timeout=20, **kw)
            if r.status_code == 401 and attempt == 0:
                self._refresh()
                continue
            if r.status_code == 429:
                reset = float(r.headers.get("Ratelimit-Reset", time.time() + 5))
                time.sleep(max(1.0, reset - time.time()))
                continue
            return r
        return r

    # --- endpoints --------------------------------------------------------
    def user_ids(self, logins: list[str]) -> dict[str, str]:
        ids = {}
        for i in range(0, len(logins), 100):
            r = self._request("GET", "/users", params=[("login", l) for l in logins[i:i + 100]])
            r.raise_for_status()
            ids.update({u["login"]: u["id"] for u in r.json()["data"]})
        missing = set(logins) - set(ids)
        if missing:
            log.warning("unknown Twitch channels: %s", ", ".join(sorted(missing)))
        return ids

    def live_streams(self, logins: list[str]) -> dict[str, dict]:
        """{login: stream} for the channels that are live right now."""
        live = {}
        for i in range(0, len(logins), 100):
            r = self._request("GET", "/streams", params=[("user_login", l) for l in logins[i:i + 100]])
            r.raise_for_status()
            live.update({s["user_login"].lower(): s for s in r.json()["data"]})
        return live

    def create_clip(self, broadcaster_id: str) -> str:
        r = self._request("POST", "/clips", params={"broadcaster_id": broadcaster_id})
        if r.status_code != 202:
            raise TwitchError(f"create clip failed: {r.status_code} {r.text}")
        return r.json()["data"][0]["id"]

    def wait_for_clip(self, clip_id: str, timeout: float = 30) -> dict:
        """Twitch takes ~15s to process a clip. Returns the clip once it exists."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(4)
            r = self._request("GET", "/clips", params={"id": clip_id})
            if r.ok and r.json()["data"]:
                return r.json()["data"][0]
        raise TwitchError(f"clip {clip_id} never finished processing")


def download_clip(url: str, out_path: Path) -> Path:
    """Twitch doesn't give a direct MP4 link, so let yt-dlp fetch it."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "yt_dlp", "--quiet", "--no-warnings", "--no-part",
           "-f", "best[ext=mp4]/best", "-o", str(out_path), url]
    for attempt in range(3):
        if subprocess.run(cmd).returncode == 0 and out_path.exists():
            return out_path
        time.sleep(5 * (attempt + 1))
    raise TwitchError(f"could not download {url}")
