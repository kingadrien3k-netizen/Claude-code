# Clipbot

Watches Twitch streamers' chats, clips the moments when chat explodes, turns each clip
into a vertical 9:16 video with hook text, and posts it to TikTok with a caption.

```
chat spike ─▶ Twitch clip ─▶ download ─▶ 1080×1920 + hook text ─▶ TikTok post (+ caption)
```

## How it decides what to clip
Every channel gets its own detector. First it learns what "normal" chat looks like
(the last 5 minutes), then clips when either:
- **spike**: the last 12 s has ≥ 3× the normal message rate (and at least 15 messages), or
- **keywords**: 8+ messages in the last 12 s contain hype words/emotes (`KEKW`, `POG`, `clip it`, `W`, …).

There is a 3-minute cooldown per channel. Every number is tunable in `config.yaml`.
For big streamers (10k+ viewers) raise `min_messages`; for small ones lower it.

## Setup

**1. Install** (Python 3.10+, plus `ffmpeg` on your PATH)
```bash
cd clipbot
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

**2. Twitch app**: go to https://dev.twitch.tv/console/apps, register an app, set the
redirect URL to `http://localhost:8765/callback`, and copy the client ID and secret into
`config.yaml`. Then:
```bash
python -m clipbot auth twitch     # opens a login link, saves tokens.json
```
Clips are created under the Twitch account you log in with.

**3. TikTok app**: at https://developers.tiktok.com create an app, add **Login Kit** and
**Content Posting API** (turn on Direct Post), request the scopes `user.info.basic`,
`video.publish` and `video.upload`, and register a redirect URL. TikTok requires an https
URL; any page you control works, because you only copy the URL from the browser bar
afterwards. Then:
```bash
python -m clipbot auth tiktok     # paste the URL you land on after approving
```

**4. Add channels** to `config.yaml`, then test without clipping:
```bash
python -m clipbot run --dry-run   # logs when it *would* clip
python -m clipbot run --no-upload # clips + renders to clips/tiktok/, no posting
python -m clipbot run             # the full bot
```

## TikTok rules you need to know
- **Private until audited.** Until TikTok audits your app, direct posts must use
  `privacy_level: SELF_ONLY`, so videos post as private. Make them public in the TikTok app,
  or apply for the audit in the developer portal and then set `PUBLIC_TO_EVERYONE`.
- **Draft mode has no caption.** `mode: draft` puts the video in your TikTok inbox to finish
  in the app, but TikTok's API doesn't accept a caption there. The caption is saved next to
  the video as a `.txt` file so you can paste it.
- **Posting limits.** TikTok caps posts per creator per day; `max_posts_per_day` (default 5)
  keeps the bot under it.

## Permission
The clips are the streamer's content. Only set `tiktok: true` on channels whose streamer
has OK'd reposting; many clip channels ask streamers first. Every caption credits
`twitch.tv/<streamer>`. Reposting without permission can get your TikTok account
copyright strikes.

## Other commands
```bash
python -m clipbot history                         # recent clips and their status
python -m clipbot render in.mp4 out.mp4 --text "hook"   # make any clip vertical
python -m clipbot post clips/tiktok/x.mp4         # (re)post one file, caption from x.txt
python -m unittest discover -s tests              # tests
```

## Files
| File | Purpose |
|---|---|
| `clipbot/bot.py` | Main loop: chat → detector → clip → render → post |
| `clipbot/detector.py` | Chat spike / hype-keyword detection |
| `clipbot/chat.py` | Anonymous read-only Twitch chat (IRC) |
| `clipbot/twitch.py` | Live status, create clip, download (yt-dlp) |
| `clipbot/video.py` | ffmpeg: 9:16 blurred-background layout + hook text |
| `clipbot/captions.py` | Hook text and caption with credit + hashtags |
| `clipbot/tiktok.py` | TikTok Content Posting API (direct post or inbox draft) |
| `clipbot/store.py` | SQLite history (`clipbot.db`) |
