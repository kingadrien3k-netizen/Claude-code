"""Command line: python -m clipbot {run,auth,post,render,history}"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import http.server
import logging
import secrets
import sys
import urllib.parse
from pathlib import Path

from . import config, tiktok, twitch, video
from .bot import Bot
from .tokens import TokenStore


def _catch_redirect(redirect_uri: str) -> str | None:
    """If the redirect is localhost, run a one-shot server to catch it."""
    u = urllib.parse.urlparse(redirect_uri)
    if u.hostname not in ("localhost", "127.0.0.1"):
        return None
    got: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            got["url"] = self.path
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Authorized. You can close this tab and go back to the terminal.")

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer((u.hostname, u.port or 80), Handler)
    print(f"Waiting for the redirect on {redirect_uri} ...")
    server.handle_request()
    server.server_close()
    return got.get("url")


def cmd_auth(cfg: dict, service: str) -> None:
    tokens = TokenStore(cfg["paths"]["tokens_file"])
    state = secrets.token_urlsafe(16)
    mod, sub = (twitch, cfg["twitch"]) if service == "twitch" else (tiktok, cfg["tiktok"])
    print(f"\nOpen this link, log in and approve:\n\n  {mod.auth_url(sub, state)}\n")
    redirected = _catch_redirect(sub["redirect_uri"])
    if not redirected:
        redirected = input("Paste the full URL you were redirected to: ").strip()
    params = urllib.parse.parse_qs(urllib.parse.urlparse(redirected).query)
    if params.get("state", [""])[0] != state:
        sys.exit("state mismatch; start the auth again")
    if "code" not in params:
        sys.exit(f"no code in redirect: {params.get('error_description') or params}")
    tokens.set(service, mod.exchange_code(sub, params["code"][0]))
    print(f"Saved {service} token to {tokens.path}")


def cmd_post(cfg: dict, file: str, caption: str | None, mode: str | None) -> None:
    path = Path(file)
    if caption is None:
        txt = path.with_suffix(".txt")
        caption = txt.read_text().strip() if txt.exists() else ""
    tk = tiktok.TikTok(cfg["tiktok"], TokenStore(cfg["paths"]["tokens_file"]))
    publish_id = tk.upload(path, caption, mode)
    print("uploaded, publish_id:", publish_id)
    print("status:", tk.wait_for_status(publish_id))


def cmd_history(cfg: dict) -> None:
    from .store import Store
    for created, channel, reason, status, url, err in Store(cfg["paths"]["db_file"]).recent():
        when = dt.datetime.fromtimestamp(created).strftime("%m-%d %H:%M")
        print(f"{when}  {channel:<16} {reason or '':<9} {status or '':<17} {url or ''} {err or ''}")


def main() -> None:
    p = argparse.ArgumentParser(prog="clipbot", description="Clip Twitch hype moments and post them to TikTok")
    p.add_argument("-c", "--config", default="config.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="watch channels and clip")
    r.add_argument("--dry-run", action="store_true", help="only log when it would clip")
    r.add_argument("--no-upload", action="store_true", help="clip and render, but don't post")

    a = sub.add_parser("auth", help="log in to twitch or tiktok")
    a.add_argument("service", choices=["twitch", "tiktok"])

    po = sub.add_parser("post", help="post one video file to TikTok")
    po.add_argument("file")
    po.add_argument("--caption", help="defaults to the .txt file next to the video")
    po.add_argument("--mode", choices=["direct", "draft"])

    re_ = sub.add_parser("render", help="make a vertical TikTok video from any clip")
    re_.add_argument("src")
    re_.add_argument("dst")
    re_.add_argument("--text", help="hook text to burn into the video")

    sub.add_parser("history", help="show recent clips")

    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    cfg = config.load(args.config)

    if args.cmd == "run":
        try:
            asyncio.run(Bot(cfg, dry_run=args.dry_run, no_upload=args.no_upload).run())
        except KeyboardInterrupt:
            pass
    elif args.cmd == "auth":
        cmd_auth(cfg, args.service)
    elif args.cmd == "post":
        cmd_post(cfg, args.file, args.caption, args.mode)
    elif args.cmd == "render":
        video.render(Path(args.src), Path(args.dst), args.text, cfg["video"])
        print("wrote", args.dst)
    elif args.cmd == "history":
        cmd_history(cfg)


if __name__ == "__main__":
    main()
