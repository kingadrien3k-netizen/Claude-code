# Hushfall — ambient / ASMR background channel

**Name:** Hushfall
**Tagline:** *Quiet rooms for sleep, study, and slow nights.*

## Channel concept
Long, calm, voiceless videos (1–10 hours) of cozy silhouette scenes with gentle, natural-sounding ambience.
Viewers put them on while sleeping, studying, working, or reading. No talking, no music drops, no sudden sounds.

- **Look:** dark, warm silhouette rooms with one window to the outside world; soft glows; very slow, looping motion.
- **Sound:** generated from scratch (no stock or copyrighted audio) — rain, thunder, drips, fire, wind, etc.
- **Mascot:** a small sleeping cat that appears in every scene, breathing slowly. Viewers learn to look for it.
- **Lengths:** 1 hour, 3 hours, 8 hours ("full night") versions of each scene.

## Video #1: Rainy Night Window
A desk by a big window at night. Rain falls over blurred city lights, drops slide down the glass,
the cat sleeps on the sill, a desk lamp glows, steam curls from a mug. Soft distant thunder every few minutes.

**Title options**
1. Rainy Night by the Window 🌧️ 8 Hours of Rain Sounds for Sleep & Study
2. Cozy Rain on the Window — 3 Hours of Calm Night Ambience (No Music)
3. Rain, Lamp Light & a Sleeping Cat 🐈‍⬛ | Gentle Rain Sounds for Deep Sleep

**Description**
> Settle in by the window. Gentle rain, soft distant thunder, a warm lamp, and a sleeping cat on the sill.
>
> No music, no talking, no ads in the middle of the sound — just rain, for as long as you need it.
> Perfect for sleep, studying, reading, focus, or calming down after a long day.
>
> 🌧️ Rain on glass · ⛈️ Distant thunder · 💡 Warm lamp light · 🐈‍⬛ Sleeping cat
>
> Which room should we open next? Tell us in the comments.

**Tags:** rain sounds, rain sounds for sleeping, rain on window, cozy rain, rain ambience, sleep sounds,
study ambience, relaxing rain, thunderstorm sounds, asmr rain, night rain, rain for sleep, white noise, hushfall

**Thumbnail:** the window scene with the lamp glow brighter; text "RAINY NIGHT · 8 HOURS".

## Upcoming scene ideas
- Snowy cabin with a crackling fireplace
- Train compartment at night in the rain
- Lighthouse room during a storm
- Underwater-glass library (soft bubbling)
- Campfire under the stars with crickets
- Late-night diner booth in the rain

## Making the videos
Requires Python 3 (Pillow, numpy, scipy) and ffmpeg.

```bash
cd asmr
# 1. (only if you change the scene) re-render the 20-second seamless loop
OUT=build; for k in 0 1 2 3; do python3 render_ambient.py frames $OUT $k 4 & done; wait
ffmpeg -framerate 24 -i $OUT/frames/f%05d.png -c:v libx264 -pix_fmt yuv420p -crf 22 -g 48 rainy-window-loop.mp4

# 2. build a long version (hours)
./make_long.sh 1     # 1 hour
./make_long.sh 8     # 8 hours
```

`rainy-window-loop.mp4` (20 s) is already included, so step 1 is optional.
`loop-small.mp4` is a lighter copy of the same loop (~720 kbps) that keeps a 1-hour video under 400 MB;
use it with `ffmpeg -stream_loop -1 -i loop-small.mp4 ...` when file size matters.
The audio is a 10-minute seamless rain track that repeats underneath; the thunder lands at different
points against the 20-second picture loop, so it never feels like an obvious repeat.

## YouTube tips for ambient channels
- Upload the **8-hour** version as the main video; long watch time is what these channels live on.
- Turn **off mid-roll ads** on sleep videos (people leave if an ad wakes them up).
- Post a 1-minute vertical clip as a **Short** that points to the full video.
- Consistent thumbnails: same layout, different scene + one word.
