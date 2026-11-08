# Hypothetica video renderer

| File | What it makes |
|------|---------------|
| `render_episode.py` | **Full voiceless Episode 1** (~3.7 min): all scenes, on-screen story text, generated music |
| `render_silhouette.py` | 36-second silhouette teaser (also holds the shared drawing helpers) |
| `render_preview.py` | 36-second chalkboard-style teaser (older style) |

## Render the full episode
Needs Python 3 with Pillow + numpy, and ffmpeg.

```bash
cd channel/preview
OUT=build; mkdir -p $OUT
for k in 0 1 2 3; do python3 render_episode.py frames $OUT $k 4 & done; wait   # 4 parallel workers
python3 render_episode.py music $OUT/music.wav
ffmpeg -framerate 24 -i $OUT/frames/f%05d.png -i $OUT/music.wav -map 0:v -map 1:a \
  -c:v libx264 -pix_fmt yuv420p -crf 21 -c:a aac -b:a 160k -shortest ep01-full-voiceless.mp4
```

Preview a single moment: `python3 render_episode.py still 34 test.png`

## Editing the story
All the on-screen text is in the `STORY` list at the bottom of `render_episode.py`: each entry is a scene
function plus the lines shown during it. Scene length is set automatically from how long the text takes to read.
