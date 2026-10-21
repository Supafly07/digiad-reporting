#!/bin/bash
# Join the rendered chapter parts (no re-encode) and add the narration once -> out/full-video.mp4.
# Parts come from: npx remotion render src/index.ts Part out/parts/partNN.mp4 --props='{"settingsFile":"full/settings.json","part":N}' --muted
set -e
cd "$(dirname "$0")/../.."
ls out/parts/part??.mp4 | sed "s|^out/parts/|file '|; s|$|'|" > out/parts/list.txt
ffmpeg -v error -y -f concat -safe 0 -i out/parts/list.txt -c copy out/parts/joined.mp4
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 out/parts/joined.mp4)
audio=public/full/narration.wav
[ -f "$audio" ] || audio=public/full/narration.mp3
# The narration starts at 0:00 like the timeline; pad its tail with silence to the video's length.
ffmpeg -v error -y -i out/parts/joined.mp4 -i "$audio" -map 0:v -map 1:a -c:v copy \
  -af "apad" -t "$dur" -c:a aac -b:a 192k -ar 48000 -movflags +faststart out/full-video.mp4
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact out/full-video.mp4
