#!/usr/bin/env bash
# Render the Episode 1 chalkboard preview: frames (4 parallel workers) -> MP4 with a soft ambient pad.
set -euo pipefail
OUT=${1:-./build}
here=$(cd "$(dirname "$0")" && pwd)
rm -rf "$OUT"; mkdir -p "$OUT"
for k in 0 1 2 3; do python3 "$here/render_preview.py" "$OUT" $k 4 & done; wait
ffmpeg -y -loglevel error -framerate 24 -i "$OUT/frames/f%05d.png" \
  -f lavfi -i "aevalsrc='0.05*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.1*t))+0.04*sin(2*PI*164.8*t)*(0.6+0.4*sin(2*PI*0.13*t))+0.03*sin(2*PI*220*t)+0.02*sin(2*PI*329.6*t)*(0.5+0.5*sin(2*PI*0.07*t))':s=44100:d=36" \
  -filter_complex "[1:a]lowpass=f=900,afade=t=in:d=2,afade=t=out:st=33.5:d=2.5,volume=1.4[a]" \
  -map 0:v -map "[a]" -c:v libx264 -pix_fmt yuv420p -crf 22 -preset slow -c:a aac -b:a 128k -shortest \
  "$here/ep01-preview.mp4"
echo "wrote $here/ep01-preview.mp4"
