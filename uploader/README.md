# Hushfall Uploader

Uploads your videos to YouTube with the title, description, tags and thumbnail filled in. Before each upload it
**researches your competition**: it pulls public data on the best-performing recent videos in your niche (and on
competitor channels you list), then tells you what's winning and adds the winning tags for you.

Run it on **your own computer**, because it signs in to your YouTube account in your browser.

## What the competitor research checks
- **Top performers** by *views per day* (so new hits count, not just old videos)
- **Best video length** (1h vs 3h vs 8h vs 10h) by median views per day
- **Winning title words**: words that show up far more often in the top quarter than in the rest
- **Tags** used by high-performing videos, added to your tags (up to YouTube's 500-character limit)
- **Engagement** (likes per view) of the winners vs everyone, as a rough quality signal
- **Upload days and times** the winners used

Each run saves a report to `reports/` (Markdown + JSON) so you can follow trends week to week.
It only looks at public statistics. It never downloads or copies anyone's videos, titles or thumbnails.

## One-time setup (about 10 minutes)
1. **Install Python 3**: python.org/downloads (on Windows, tick "Add Python to PATH").
2. **Create a Google Cloud project**: go to console.cloud.google.com → project picker → **New project** → name it "Hushfall".
3. **Turn on the YouTube API**: **APIs & Services → Library** → search "YouTube Data API v3" → **Enable**.
4. **Consent screen**: **APIs & Services → OAuth consent screen** → External → fill in the app name and your email.
   Under **Test users**, add the Google account that owns your channel.
5. **Credentials**: **APIs & Services → Credentials → Create credentials → OAuth client ID** → type **Desktop app**
   → Create → **Download JSON**. Rename it to `client_secret.json` and put it in this `uploader` folder.
6. **Install the libraries** (in a terminal, inside this folder):
   ```
   python3 -m pip install -r requirements.txt
   ```
   (On Windows, use `py` instead of `python3`.)

The first time you upload, a browser window opens and asks you to sign in and allow access. Your login is saved
in `token.json` so you only do this once. Never share `client_secret.json` or `token.json`.

## Use it
```
python3 upload.py                        # choose a video from a list (looks here, ../asmr, Downloads, Desktop)
python3 upload.py rainy-window-1h.mp4    # a specific file
python3 upload.py --dry-run              # preview the details without uploading
python3 upload.py --publish-at 2026-11-14T15:00:00Z   # schedule it
python3 trends.py rainy-window           # competitor research only, no upload
```
On Windows you can double-click **start.bat**; on Mac, double-click **start.command**.

## Add your competitors
In `videos.json`, under `research → competitors`, list the channel handles you want to track:
```json
"competitors": ["@SomeRainChannel", "@AnotherSleepChannel"]
```
`queries` are the YouTube searches used to find trending videos in your niche. Edit them for each new scene.

## Adding a new video
Copy the `rainy-window` block in `videos.json`, rename it, and set `match` to part of the new file's name
(e.g. `"snowy-cabin"`). The uploader picks the preset whose `match` appears in the file name.

## Two things Google enforces
- **Videos uploaded through a new, unaudited app stay Private.** This is Google's rule for every API app.
  After uploading, open the YouTube Studio link the uploader prints and switch the video to **Public** there,
  or apply for the free "YouTube API Services audit" in Google Cloud to remove the lock.
- **Daily quota:** the default 10,000 units/day is enough for about **4 uploads with research per day**
  (an upload costs 1,600 units; each research search costs 100).

Custom thumbnails require a verified channel (youtube.com/verify).
