#!/bin/bash
# Render every chapter part (muted); they are joined and the narration muxed afterwards.
export REMOTION_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell
cd /home/user/digiad-reporting
for n in 0 1 2 3 4 5 6 7 8 9; do
  f=out/parts/part$(printf %02d $n).mp4
  [ -s "$f" ] && { echo "skip $f"; continue; }
  start=$(date +%s)
  npx remotion render src/index.ts Part "$f.tmp.mp4" --props="{\"settingsFile\":\"full/settings.json\",\"part\":$n}" \
    --muted --codec h264 --crf 18 --concurrency 4 --log error || { echo "FAILED part $n"; exit 1; }
  mv "$f.tmp.mp4" "$f"
  echo "done $f in $(( $(date +%s) - start ))s"
done
echo ALL PARTS DONE
