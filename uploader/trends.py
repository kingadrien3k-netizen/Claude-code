#!/usr/bin/env python3
"""Competitor research for your niche, using YouTube's public data (YouTube Data API v3).

It finds the best-performing recent videos for your search terms and competitor channels, then works out
what they have in common: video length, title words, tags, upload timing and engagement. It suggests
keywords and tags to use. It never copies anyone's titles, thumbnails, or videos.

Run on its own:   python3 trends.py rainy-window
(It also runs automatically inside upload.py for presets that have a "research" section.)
"""
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"
STOP = set("""a an and the of for to in on with by at from is it this that your you my our be are as or
no not just all into over under vs ft feat x i me we us his her its their them it's its' &
""".split())
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------------------------------------------------------------- data collection
def _parse_duration(iso):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _video_details(yt, ids):
    out = []
    for i in range(0, len(ids), 50):
        resp = yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50])).execute()
        out += resp.get("items", [])
    return out


def _search(yt, query, days, max_results):
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = yt.search().list(part="id", q=query, type="video", order="viewCount", publishedAfter=after,
                            maxResults=min(50, max_results), relevanceLanguage="en").execute()
    return [it["id"]["videoId"] for it in resp.get("items", []) if it["id"].get("videoId")]


def _channel_recent(yt, handle, n=25):
    handle = handle if handle.startswith("@") else "@" + handle
    resp = yt.channels().list(part="contentDetails,snippet,statistics", forHandle=handle).execute()
    items = resp.get("items", [])
    if not items:
        print(f"  ⚠ channel {handle} not found")
        return [], None
    ch = items[0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=min(50, n)).execute()
    info = {"handle": handle, "title": ch["snippet"]["title"],
            "subscribers": int(ch["statistics"].get("subscriberCount", 0) or 0),
            "videos": int(ch["statistics"].get("videoCount", 0) or 0)}
    return [it["contentDetails"]["videoId"] for it in pl.get("items", [])], info


def collect(yt, cfg):
    """cfg: {"queries": [...], "competitors": ["@handle", ...], "days": 180, "per_query": 25}"""
    ids, channels = [], []
    for q in cfg.get("queries", []):
        ids += _search(yt, q, cfg.get("days", 180), cfg.get("per_query", 25))
    for h in cfg.get("competitors", []):
        vids, info = _channel_recent(yt, h, cfg.get("per_channel", 25))
        ids += vids
        if info:
            channels.append(info)
    ids = list(dict.fromkeys(ids))
    return _video_details(yt, ids), channels


# ---------------------------------------------------------------- analysis
def _words(title):
    title = re.sub(r"[^\w\s'&-]", " ", title.lower())
    return [w for w in title.split() if w not in STOP and len(w) > 1 and not w.isdigit()]


def _phrases(title):
    w = _words(title)
    return set(w) | {f"{a} {b}" for a, b in zip(w, w[1:])}


def analyze(items, channels=(), min_seconds=0):
    now = datetime.now(timezone.utc)
    vids = []
    for it in items:
        st, sn, cd = it.get("statistics", {}), it["snippet"], it.get("contentDetails", {})
        secs = _parse_duration(cd.get("duration"))
        if secs < min_seconds:
            continue
        pub = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
        age = max(1.0, (now - pub).total_seconds() / 86400)
        views = int(st.get("viewCount", 0) or 0)
        likes = int(st.get("likeCount", 0) or 0)
        comments = int(st.get("commentCount", 0) or 0)
        vids.append({
            "id": it["id"], "title": sn["title"], "channel": sn["channelTitle"], "published": sn["publishedAt"],
            "views": views, "views_per_day": views / age, "age_days": round(age), "seconds": secs,
            "like_rate": likes / views if views else 0, "comment_rate": comments / views if views else 0,
            "tags": sn.get("tags", []), "weekday": pub.weekday(), "hour_utc": pub.hour,
            "title_len": len(sn["title"]), "has_emoji": bool(re.search(r"[\U0001F300-\U0001FAFF☀-➿]", sn["title"])),
            "has_hours": bool(re.search(r"\b\d+\s*(hour|hours|hr|hrs|h)\b", sn["title"], re.I)),
            "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url", ""),
        })
    if not vids:
        return {"count": 0}
    vids.sort(key=lambda v: v["views_per_day"], reverse=True)
    top = vids[:max(5, len(vids) // 4)]          # "winners" = top quarter by views per day
    rest = vids[len(top):] or vids

    def med(key, group):
        return statistics.median(v[key] for v in group)

    # title words/phrases that show up much more in winners than in the rest
    tw, rw = Counter(), Counter()
    for v in top:
        tw.update(_phrases(v["title"]))
    for v in rest:
        rw.update(_phrases(v["title"]))
    scores = {}
    for w, c in tw.items():
        if c < 2:
            continue
        share_top, share_rest = c / len(top), rw[w] / len(rest)
        scores[w] = share_top * (1 + share_top - share_rest)
    title_keywords = [w for w, _ in sorted(scores.items(), key=lambda x: -x[1])][:15]

    # tags weighted by the views/day of videos that use them
    tag_score = defaultdict(float)
    tag_count = Counter()
    for v in vids:
        for t in {t.lower().strip() for t in v["tags"]}:
            tag_score[t] += v["views_per_day"] ** 0.5
            tag_count[t] += 1
    own_channels = {c["title"].lower() for c in channels}
    tags = [t for t, _ in sorted(tag_score.items(), key=lambda x: -x[1])
            if tag_count[t] >= 2 and t not in own_channels and len(t) <= 40][:30]

    # length buckets
    buckets = defaultdict(list)
    for v in vids:
        h = v["seconds"] / 3600
        b = "< 1h" if h < 1 else "1–2h" if h < 2.5 else "3h" if h < 5 else "8h" if h < 9.5 else "10h+"
        buckets[b].append(v["views_per_day"])
    length_perf = {b: {"videos": len(x), "median_views_per_day": round(statistics.median(x))} for b, x in buckets.items()}
    best_length = max(length_perf.items(), key=lambda kv: kv[1]["median_views_per_day"] if kv[1]["videos"] >= 2 else -1)[0]

    day_perf = defaultdict(list)
    for v in top:
        day_perf[DAYS[v["weekday"]]].append(v["views_per_day"])
    best_days = sorted(day_perf, key=lambda d: -len(day_perf[d]))[:3]
    hours = Counter(v["hour_utc"] for v in top).most_common(3)

    return {
        "date": now.strftime("%Y-%m-%d"),
        "count": len(vids),
        "winners": [{k: v[k] for k in ("title", "channel", "views", "views_per_day", "age_days", "seconds",
                                       "like_rate", "id", "thumbnail")} for v in top[:10]],
        "channels": list(channels),
        "title_keywords": title_keywords,
        "suggested_tags": tags,
        "length_performance": length_perf,
        "best_length": best_length,
        "best_days": best_days,
        "best_hours_utc": [h for h, _ in hours],
        "winners_median_title_len": round(med("title_len", top)),
        "winners_with_emoji_pct": round(100 * sum(v["has_emoji"] for v in top) / len(top)),
        "winners_with_hours_in_title_pct": round(100 * sum(v["has_hours"] for v in top) / len(top)),
        "winners_median_like_rate_pct": round(100 * med("like_rate", top), 2),
        "everyone_median_like_rate_pct": round(100 * med("like_rate", vids), 2),
    }


# ---------------------------------------------------------------- output
def merge_tags(own, suggested, limit=480):
    """Keep your tags first, then add winning tags until YouTube's 500-character tag limit."""
    out, seen = [], set()
    for t in list(own) + list(suggested):
        k = t.lower().strip()
        if not k or k in seen:
            continue
        if sum(len(x) + 3 for x in out) + len(t) + 3 > limit:
            break
        out.append(t)
        seen.add(k)
    return out


def print_report(r):
    if not r.get("count"):
        print("\n  (no competitor videos found — check the search terms in videos.json)")
        return
    print(f"\n━━━ Competitor research ({r['count']} videos analysed, {r['date']}) ━━━")
    print("\n  Top performers (views per day):")
    for v in r["winners"][:5]:
        print(f"   • {v['views_per_day']:>9,.0f}/day  {v['seconds'] / 3600:4.1f}h  {v['channel'][:22]:<22}  youtu.be/{v['id']}")
    print(f"\n  Best-performing length:  {r['best_length']}")
    for b, d in sorted(r["length_performance"].items()):
        print(f"     {b:<5} {d['videos']:>3} videos, median {d['median_views_per_day']:,}/day")
    print(f"  Winning title words:     {', '.join(r['title_keywords'][:10])}")
    print(f"  Winners' titles:         ~{r['winners_median_title_len']} chars, "
          f"{r['winners_with_emoji_pct']}% use emoji, {r['winners_with_hours_in_title_pct']}% say the length")
    print(f"  Engagement (likes/view): winners {r['winners_median_like_rate_pct']}% vs all {r['everyone_median_like_rate_pct']}%")
    print(f"  Common upload days:      {', '.join(r['best_days'])}   (UTC hours: {', '.join(map(str, r['best_hours_utc']))})")
    print(f"  Tags being added:        {', '.join(r['suggested_tags'][:10])}…")


def save(r, name):
    REPORTS.mkdir(exist_ok=True)
    base = REPORTS / f"{name}-{r.get('date', 'latest')}"
    base.with_suffix(".json").write_text(json.dumps(r, indent=2, ensure_ascii=False))
    lines = [f"# Competitor research: {name} ({r.get('date')})", "", f"{r.get('count', 0)} videos analysed.", "",
             "## Top performers", "", "| Views/day | Length | Channel | Video |", "|---|---|---|---|"]
    for v in r.get("winners", []):
        lines.append(f"| {v['views_per_day']:,.0f} | {v['seconds'] / 3600:.1f}h | {v['channel']} | https://youtu.be/{v['id']} |")
    lines += ["", f"**Best length:** {r.get('best_length')}  ",
              f"**Winning title words:** {', '.join(r.get('title_keywords', []))}  ",
              f"**Suggested tags:** {', '.join(r.get('suggested_tags', []))}  ",
              f"**Upload days:** {', '.join(r.get('best_days', []))}", "",
              "Compare the top performers' thumbnails yourself for style ideas; keep your own look."]
    base.with_suffix(".md").write_text("\n".join(lines))
    return base.with_suffix(".md")


def research(yt, cfg, save_as="niche"):
    print("\nResearching your competition on YouTube…")
    items, channels = collect(yt, cfg)
    r = analyze(items, channels, cfg.get("min_minutes", 0) * 60)
    if r.get("count"):
        print(f"  saved report: {save(r, save_as)}")
    return r


if __name__ == "__main__":
    from upload import load_presets, youtube_service
    presets = load_presets()
    name = sys.argv[1] if len(sys.argv) > 1 else next((k for k, p in presets.items() if p.get("research")), None)
    if not name or not presets.get(name, {}).get("research"):
        sys.exit("Usage: python3 trends.py <preset name with a 'research' section in videos.json>")
    print_report(research(youtube_service(), presets[name]["research"], save_as=name))
