"""Join the paragraph takes into one narration with natural pauses and even loudness.

Writes public/full/narration.wav + .mp3 and public/full/voice_layout.json (where every
paragraph starts in the joined file), which align_words.py uses to place the word timings.
"""
import json, re, subprocess
from pathlib import Path

LEAD_IN = 0.5          # silence before the first word
PAUSE_PARAGRAPH = 0.75  # between paragraphs inside a chapter
PAUSE_CHAPTER = 1.4     # before the first paragraph of a new chapter
TARGET_DB = -20.0       # mean volume every paragraph is matched to
RATE = 48000

root = Path(__file__).resolve().parents[2]
script = json.loads((root / "public/full/script.json").read_text())
work = root / "voice/work"
work.mkdir(parents=True, exist_ok=True)


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True)


def mean_db(path):
    out = run("ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-").stderr
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", out).group(1))


def duration(path):
    return float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)).stdout)


layout, pieces, t = [], [], LEAD_IN
silence = lambda s: f"anullsrc=r={RATE}:cl=mono:d={s}"
first = True
for ch in script:
    for i, par in enumerate(ch["paragraphs"]):
        src = root / f"voice/paragraphs/{par['id']}.mp3"
        trimmed = work / f"{par['id']}.wav"
        # Trim silence at both ends (keep a few ms of breath), mono 48 kHz.
        run("ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(RATE), "-af",
            "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.04,"
            "areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse",
            str(trimmed))
        gain = TARGET_DB - mean_db(trimmed)
        leveled = work / f"{par['id']}_lv.wav"
        run("ffmpeg", "-y", "-v", "error", "-i", str(trimmed), "-af", f"volume={gain:.2f}dB", str(leveled))
        if not first:
            gap = PAUSE_CHAPTER if i == 0 else PAUSE_PARAGRAPH
            pieces.append(("silence", gap))
            t += gap
        first = False
        d = duration(leveled)
        layout.append({"paragraph": par["id"], "chapter": ch["id"], "start": round(t, 4), "duration": round(d, 4),
                       "gain_db": round(gain, 2)})
        pieces.append(("file", leveled))
        t += d

# Concatenate with exact silences.
inputs, filters = [], []
for k, (kind, val) in enumerate(pieces):
    if kind == "file":
        inputs += ["-i", str(val)]
    else:
        inputs += ["-f", "lavfi", "-t", f"{val}", "-i", silence(val)]
    filters.append(f"[{k}:a]")
wav = root / "public/full/narration.wav"
run("ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex",
    "".join(filters) + f"concat=n={len(pieces)}:v=0:a=1,alimiter=limit=0.89:level=disabled[out]", "-map", "[out]",
    "-ar", str(RATE), str(wav))
run("ffmpeg", "-y", "-v", "error", "-i", str(wav), "-b:a", "192k", str(root / "public/full/narration.mp3"))
(root / "public/full/voice_layout.json").write_text(json.dumps(
    {"leadIn": LEAD_IN, "pauseParagraph": PAUSE_PARAGRAPH, "pauseChapter": PAUSE_CHAPTER,
     "duration": round(duration(wav), 4), "paragraphs": layout}, indent=1))
print(f"joined {len(layout)} paragraphs -> {duration(wav):.2f} s")
print("gain range", min(p['gain_db'] for p in layout), "to", max(p['gain_db'] for p in layout), "dB")
