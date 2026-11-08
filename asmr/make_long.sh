#!/usr/bin/env bash
# Build a long ambient video from the seamless loop + generated rain audio.
# Usage: ./make_long.sh <hours> [output.mp4]      e.g. ./make_long.sh 3
# No re-encoding of the video, so even an 8-hour file builds in a few minutes.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
HOURS=${1:-1}
OUT=${2:-"$here/rainy-window-${HOURS}h.mp4"}
SECS=$(python3 -c "print(int(float('$HOURS')*3600))")
TMP=$(mktemp -d)
[ -f "$here/rainy-window-loop.mp4" ] || { echo "missing rainy-window-loop.mp4 (see README)"; exit 1; }
python3 "$here/render_ambient.py" audio "$TMP/rain.wav" 10
ffmpeg -y -loglevel error -stream_loop -1 -i "$here/rainy-window-loop.mp4" -stream_loop -1 -i "$TMP/rain.wav" \
  -map 0:v -map 1:a -t "$SECS" -c:v copy -c:a aac -b:a 160k -movflags +faststart "$OUT"
rm -rf "$TMP"
echo "wrote $OUT"
