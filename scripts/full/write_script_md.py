"""Write script.md: narration by chapter, the shot list for every sentence, and the picture list.

The shot list comes from public/full/shots.json, which build_settings.py writes from the same
calls that make the animation, so the document always matches the video.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
script = json.loads((ROOT / "public/full/script.json").read_text())
shots = json.loads((ROOT / "public/full/shots.json").read_text())
words = json.loads((ROOT / "public/full/words.json").read_text())["words"]
start = {}
for w in words:
    start.setdefault(w["sid"], w["start"])

STYLE = ("Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook, "
         "with one soft blue accent added by the animation for light and movement.")

PICTURES = [
    ("01_walking_shoe", "A lace-up walking shoe from the side (from the short; not used in the long video's shots)"),
    ("02_legs_striding", "A pair of legs mid-stride, hips down, from the side"),
    ("03_thigh_muscle", "The thigh muscle (quadriceps) on its own, from the front"),
    ("04_blood_vessel", "A blood vessel cut open lengthwise, from the side"),
    ("05_heart", "A human heart, front view"),
    ("06_brain", "A human brain from the side"),
    ("07_walking_figure", "A woman walking, full figure, from the side"),
    ("08_pedometer", "An old 1960s clip-on mechanical step counter, front view"),
    ("09_calf_muscle", "The calf muscle on its own, from behind"),
    ("10_vein_valves", "A vein cut open to show two one-way valves, front view"),
    ("11_sugar_cube", "A single sugar cube, three-quarter view"),
    ("12_meal_plate", "A plate with a simple meal, seen from above"),
    ("13_muscle_fiber", "A bundle of muscle fibers, one end cut open, three-quarter view"),
    ("14_key", "An old-fashioned key from the side"),
    ("15_stethoscope", "A stethoscope lying in a loose curve, from above"),
    ("16_hippocampus", "The hippocampus on its own, from the side"),
    ("17_seahorse", "A seahorse from the side"),
    ("18_neuron", "A single nerve cell with its long axon, from the side"),
    ("19_light_bulb", "An old filament light bulb, front view"),
    ("20_metronome", "A wind-up metronome, front view"),
    ("21_footprint", "A single bare footprint, from above"),
]

mmss = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
out = ["# What Really Happens When You Walk — full video script", "",
       "About 10 minutes · 1,496 words · one calm narrator · 1920×1080, 60 fps.",
       "Every fact and number is in [facts.md](facts.md) with its source. The vertical short's script is in "
       "[script-short.md](script-short.md).", "",
       "## Style line", "", f"> {STYLE}", "",
       "## How to read the shot list", "",
       "Each sentence has its ID, the time it starts in the narration, what appears on screen (in order, each on "
       "its word) and what the camera does. Everything sits on one dotted page filmed by one camera that never "
       "stops drifting; nothing cuts — the camera moves from one part of the page to the next, with footprints "
       "walking along under it on the long trips. Faint, blurred giant footprints sit far behind each part of "
       "the page (a slower depth layer).", ""]
for ch in script:
    out += [f"## {ch['title']}" + ("" if ch["id"] in ("intro", "ending") else f" ({ch['id'].replace('ch', 'Chapter ')})"), ""]
    for p in ch["paragraphs"]:
        out += [f"**{p['id']}** — {p['text']}", ""]
    out += ["| ID | Time | Narration | On screen | Camera |", "|---|---|---|---|---|"]
    for p in ch["paragraphs"]:
        for s in p["sentences"]:
            sh = shots.get(s["id"], {"screen": [], "camera": []})
            cell = lambda xs: " ".join(xs).replace("|", "/") or "drifts"
            out.append(f"| {s['id']} | {mmss(start[s['id']])} | {s['text']} | {cell(sh['screen'])} | {cell(sh['camera'])} |")
    out.append("")
out += ["## Picture list", "",
        "21 pictures, each a single object, transparent cut-outs in `public/images/` (prompts and attempts in "
        "[public/images/prompts.md](public/images/prompts.md)). 1–7 were made for the short and reused.", "",
        "| # | File | Subject |", "|---|---|---|"]
for i, (f, d) in enumerate(PICTURES, 1):
    out.append(f"| {i} | `{f}.png` | {d} |")
(ROOT / "script.md").write_text("\n".join(out) + "\n")
print("script.md:", len(out), "lines")
