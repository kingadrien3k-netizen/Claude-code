#!/usr/bin/env python3
"""Hushfall Uploader: upload a video to your YouTube channel with its title, description and tags filled in.

Run it on your own computer:
    python3 upload.py                      # pick a video from a list, uses the matching preset
    python3 upload.py path/to/video.mp4    # upload a specific file
    python3 upload.py --dry-run            # show what would be uploaded, without uploading

First-time setup (client_secret.json) is explained in README.md.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLIENT_SECRET = HERE / "client_secret.json"
TOKEN = HERE / "token.json"
PRESETS = HERE / "videos.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
SEARCH_DIRS = [HERE, HERE.parent / "asmr", Path.home() / "Downloads", Path.home() / "Desktop", Path.home() / "Videos",
               Path.home() / "Movies"]
RETRY_STATUS = {500, 502, 503, 504}


# ---------------------------------------------------------------- helpers
def die(msg):
    print(f"\n✖ {msg}")
    sys.exit(1)


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    try:
        ans = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        ans = ""
    return ans or (default or "")


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def load_presets():
    if not PRESETS.exists():
        return {}
    with open(PRESETS, encoding="utf-8") as f:
        return json.load(f)


def find_videos():
    seen, out = set(), []
    for d in SEARCH_DIRS:
        if d.is_dir():
            for p in sorted(d.glob("*.mp4")):
                if "loop" in p.name or p.resolve() in seen:
                    continue
                seen.add(p.resolve())
                out.append(p)
    return out


def pick_video():
    vids = find_videos()
    if not vids:
        die("No .mp4 videos found. Put the video in this folder (or Downloads), or run: python3 upload.py path/to/video.mp4")
    print("\nVideos found:")
    for i, p in enumerate(vids, 1):
        print(f"  {i}. {p.name}  ({human(p.stat().st_size)})  — {p.parent}")
    choice = ask("\nWhich one? Enter a number", "1")
    try:
        return vids[int(choice) - 1]
    except (ValueError, IndexError):
        die("That's not one of the numbers in the list.")


def match_preset(video, presets, name=None):
    if name:
        if name not in presets:
            die(f"No preset called '{name}' in videos.json. Available: {', '.join(presets) or 'none'}")
        return name, presets[name]
    for key, p in presets.items():
        if p.get("match", key) in video.name:
            return key, p
    return None, {}


# ---------------------------------------------------------------- YouTube
def youtube_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        die("Missing libraries. Run:  python3 -m pip install -r requirements.txt")

    creds = None
    if TOKEN.exists():
        saved = json.loads(TOKEN.read_text()).get("scopes", [])
        if set(SCOPES) <= set(saved):          # re-login if the app now needs more permissions
            creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds or not creds.valid:
            if not CLIENT_SECRET.exists():
                die("client_secret.json not found next to upload.py. Follow 'One-time setup' in README.md.")
            print("\nA browser window will open. Sign in with the Google account that owns your YouTube channel.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0, prompt="consent")
        TOKEN.write_text(creds.to_json())
        try:
            TOKEN.chmod(0o600)
        except OSError:
            pass
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(yt, video, body):
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=16 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media, notifySubscribers=True)
    total = video.stat().st_size
    response, tries, start = None, 0, time.time()
    print(f"\nUploading {video.name} ({human(total)})…")
    while response is None:
        try:
            status, response = req.next_chunk()
            if status:
                done = status.resumable_progress
                pct = done / total
                speed = done / max(1, time.time() - start)
                eta = (total - done) / max(1, speed)
                bar = "█" * int(pct * 30) + "░" * (30 - int(pct * 30))
                print(f"\r  {bar} {pct * 100:5.1f}%  {human(speed)}/s  ~{int(eta // 60)}m{int(eta % 60):02d}s left ",
                      end="", flush=True)
            tries = 0
        except HttpError as e:
            if e.resp.status in RETRY_STATUS:
                tries += 1
            elif e.resp.status == 403 and b"quota" in e.content.lower():
                die("YouTube's daily upload quota for this app is used up. Try again tomorrow.")
            else:
                die(f"YouTube rejected the upload ({e.resp.status}): {e.content.decode(errors='ignore')[:400]}")
        except (OSError, TimeoutError) as e:
            tries += 1
            print(f"\n  Connection problem ({e}); retrying…")
        if tries:
            if tries > 8:
                die("Too many failed retries. Check your internet connection and run again.")
            wait = min(64, 2 ** tries) + random.random()
            time.sleep(wait)
    print(f"\r  {'█' * 30} 100.0%{' ' * 30}")
    return response


def set_thumbnail(yt, video_id, path):
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    try:
        yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(path))).execute()
        print("  ✔ Thumbnail set")
    except HttpError as e:
        print(f"  ⚠ Thumbnail not set ({e.resp.status}). Your channel may need phone verification for custom "
              "thumbnails: youtube.com/verify — you can also add it in YouTube Studio.")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Upload a video to YouTube with preset title/description/tags.")
    ap.add_argument("video", nargs="?", help="path to the .mp4 (leave out to choose from a list)")
    ap.add_argument("--preset", help="preset name from videos.json")
    ap.add_argument("--title")
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"])
    ap.add_argument("--publish-at", help="schedule, e.g. 2026-11-10T18:00:00Z (video stays private until then)")
    ap.add_argument("--thumbnail", help="path to a .jpg/.png thumbnail")
    ap.add_argument("--dry-run", action="store_true", help="show the details without uploading")
    ap.add_argument("--no-trends", action="store_true", help="skip the competitor research step")
    args = ap.parse_args()

    print("━━━ Hushfall Uploader ━━━")
    video = Path(args.video).expanduser() if args.video else pick_video()
    if not video.is_file():
        die(f"File not found: {video}")

    key, p = match_preset(video, load_presets(), args.preset)
    if key:
        print(f"\nUsing preset: {key}")
    title = args.title or p.get("title") or ask("Title", video.stem.replace("-", " ").title())
    privacy = args.privacy or p.get("privacy", "private")
    body = {
        "snippet": {
            "title": title[:100],
            "description": p.get("description", ""),
            "tags": p.get("tags", []),
            "categoryId": str(p.get("categoryId", "10")),
            "defaultLanguage": p.get("language", "en"),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": bool(p.get("madeForKids", False)),
            "embeddable": True,
        },
    }
    if args.publish_at:
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = args.publish_at
    if not args.no_trends and p.get("research"):
        if args.dry_run and not TOKEN.exists():
            print("\n(skipping competitor research in dry run: not signed in yet)")
        else:
            import trends
            report = trends.research(youtube_service(), p["research"], save_as=key)
            trends.print_report(report)
            body["snippet"]["tags"] = trends.merge_tags(body["snippet"]["tags"], report["suggested_tags"])
            missing = [w for w in report["title_keywords"][:8] if w.lower() not in title.lower()]
            if missing:
                print(f"\n  Winning title words you're not using: {', '.join(missing)}")
                new = ask("  Press Enter to keep your title, or type a new one", "")
                if new:
                    body["snippet"]["title"] = new[:100]
    thumb = args.thumbnail or p.get("thumbnail")
    thumb = (HERE / thumb if thumb and not Path(thumb).is_absolute() else Path(thumb)) if thumb else None

    print(f"\n  File:       {video}")
    print(f"  Title:      {body['snippet']['title']}")
    print(f"  Privacy:    {body['status']['privacyStatus']}" + (f" (goes public {args.publish_at})" if args.publish_at else ""))
    print(f"  Tags:       {', '.join(body['snippet']['tags'][:6])}{'…' if len(body['snippet']['tags']) > 6 else ''}")
    print(f"  For kids:   {'yes' if body['status']['selfDeclaredMadeForKids'] else 'no'}")
    print(f"  Thumbnail:  {thumb if thumb and thumb.exists() else 'none'}")
    if args.dry_run:
        print("\n(dry run: nothing uploaded)")
        return
    if ask("\nUpload now? (y/n)", "y").lower() not in ("y", "yes"):
        print("Cancelled.")
        return

    yt = youtube_service()
    resp = upload(yt, video, body)
    vid = resp["id"]
    print(f"\n✔ Uploaded!  https://youtu.be/{vid}")
    print(f"  Edit it in YouTube Studio: https://studio.youtube.com/video/{vid}/edit")
    if thumb and thumb.exists():
        set_thumbnail(yt, vid, thumb)
    if privacy != "private" and resp.get("status", {}).get("privacyStatus") == "private":
        print("  ⚠ YouTube kept it private: Google locks API uploads to private until the app passes its free audit.\n"
              "    Open the Studio link above and switch it to Public there (see README).")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
