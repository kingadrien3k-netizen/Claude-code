"""Stores OAuth tokens for Twitch and TikTok in a local JSON file."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


class TokenStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {}

    def get(self, service: str) -> dict:
        return self.data.get(service, {})

    def set(self, service: str, token_response: dict, expires_key: str = "expires_in") -> None:
        tok = dict(token_response)
        if expires_key in tok:
            tok["expires_at"] = time.time() + int(tok[expires_key])
        self.data[service] = {**self.get(service), **tok}
        self.path.write_text(json.dumps(self.data, indent=2))
        os.chmod(self.path, 0o600)

    def expiring(self, service: str, margin: int = 300) -> bool:
        return self.get(service).get("expires_at", 0) - margin < time.time()
