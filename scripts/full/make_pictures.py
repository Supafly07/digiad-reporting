"""Make the new pictures for the full video: GPT Image 2.5 (Sunburst, 2K, high) on kie.ai,
then background removal (recraft/remove-background), saved as cut-outs in public/images/.

Usage: python3 scripts/full/make_pictures.py <name> [<name> ...]    (runs in parallel)
       python3 scripts/full/make_pictures.py --list                  (print the prompts)
Each run appends to scripts/full/pictures_log.jsonl (task ids, prompts, credits).
"""
import json, sys, time, urllib.request, concurrent.futures as cf
from pathlib import Path

API = "https://api.kie.ai/api/v1/jobs"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "public/images"
RAW = ROOT / "out/raw_pictures"  # originals with white background (not committed)
LOG = ROOT / "scripts/full/pictures_log.jsonl"

STYLE = ("Black and white scientific illustration, fine ink lines and soft graphite shading, like an old "
         "textbook, with one soft blue accent added by the animation for light and movement.")
SPACE = "Lots of empty space around it, nothing touching the edges."
# The style line mentions the blue the animation adds; without this the model paints it in.
MONO = ("Strictly monochrome graphite drawing in black, white and grey only: "
        "no blue, no glow, no light effects, no color of any kind.")
TAIL = "Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame."

SUBJECTS = {
    "08_pedometer": ("A single vintage 1960s mechanical pedometer with a belt clip, seen from the front, "
                     "with a plain round dial and one needle.", "1:1"),
    "09_calf_muscle": ("A single human calf muscle on its own, without skin or bone, anatomical illustration "
                       "seen from behind.", "2:3"),
    "10_vein_valves": ("A single short segment of a human leg vein, standing upright and cut open lengthwise "
                       "to show two thin one-way valves inside, seen from the side.", "2:3"),
    "11_sugar_cube": ("A single sugar cube, seen from a three-quarter angle.", "1:1"),
    "12_meal_plate": ("A single round dinner plate with a simple meal of rice, vegetables and a piece of fish, "
                      "seen from slightly above.", "3:2"),
    "13_muscle_fiber": ("A single bundle of muscle fibers, cut across at one end to show the many round fibers "
                        "inside, seen from a three-quarter angle.", "3:2"),
    "14_key": ("A single old-fashioned key, lying horizontally, seen from the side.", "3:2"),
    "15_stethoscope": ("A single stethoscope laid out in a loose curve, seen from above.", "1:1"),
    "16_hippocampus": ("A single human hippocampus on its own, the curved seahorse-shaped brain structure, "
                       "anatomical illustration seen from the side.", "3:2"),
    "17_seahorse": ("A single seahorse, seen from the side.", "2:3"),
    # Attempt 1 came out faint and wispy with a blue-tinted axon; attempt 2 asks for bolder drawing.
    "18_neuron": ("A single nerve cell (neuron) with a round cell body, a few thick branching dendrites and one "
                  "long axon curving to the right, drawn with bold ink lines and graphite shading, seen from the "
                  "side.", "3:2"),
    # Attempt 1 had a light-blue tint in the glass; attempt 2 asks for plain grey glass.
    "19_light_bulb": ("A single vintage light bulb with a visible filament and clear glass shaded only in grey, "
                      "standing upright, seen from the side.", "2:3"),
    "20_metronome": ("A single mechanical pyramid-shaped metronome with its pendulum arm upright in the middle, "
                     "seen from the front, with a plain face.", "2:3"),
    "21_footprint": ("A single outline drawing of the sole print of a bare human foot, seen from directly "
                     "above, toes pointing up.", "2:3"),
}


def prompt_for(name):
    subject, _ = SUBJECTS[name]
    return f"{subject} {MONO} {SPACE} {STYLE} {TAIL}"


def call(url, body=None):
    req = urllib.request.Request(url, method="POST" if body else "GET",
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def note(**kw):
    with LOG.open("a") as f:
        f.write(json.dumps({**kw, "time": time.time()}) + "\n")


def create(model, inp):
    r = call(f"{API}/createTask", {"model": model, "input": inp})
    if r.get("code") != 200:
        raise RuntimeError(f"createTask failed: {r}")
    return r["data"]["taskId"]


def wait(task_id, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = call(f"{API}/recordInfo?taskId={task_id}")["data"]
        if d and d["state"] in ("success", "fail"):
            if d["state"] == "fail":
                raise RuntimeError(f"task {task_id} failed: {d.get('failCode')} {d.get('failMsg')}")
            return json.loads(d["resultJson"])["resultUrls"][0], d.get("creditsConsumed") or 0
        time.sleep(5)
    raise TimeoutError(task_id)


def download(url, dest):
    # Result hosts are blocked by the network policy; kie's download-url gives a reachable signed link.
    signed = call("https://api.kie.ai/api/v1/common/download-url", {"url": url})["data"]
    urllib.request.urlretrieve(signed, dest)


def make(name, attempt):
    _, ratio = SUBJECTS[name]
    prompt = prompt_for(name)
    gen = create("gpt-image-2-5-sunburst-text-to-image",
                 {"prompt": prompt, "aspect_ratio": ratio, "resolution": "2K", "quality": "high"})
    note(name=name, attempt=attempt, step="gen", task=gen, prompt=prompt, ratio=ratio)
    url, gen_cr = wait(gen)
    download(url, RAW / f"{name}_a{attempt}.png")
    rb = create("recraft/remove-background", {"image": url})
    note(name=name, attempt=attempt, step="rb", task=rb)
    cut, rb_cr = wait(rb)
    download(cut, OUT / f"{name}.png")
    note(name=name, attempt=attempt, step="done", gen_credits=gen_cr, rb_credits=rb_cr)
    return gen_cr + rb_cr


if __name__ == "__main__":
    if "--list" in sys.argv:
        for n in SUBJECTS:
            print(f"{n} [{SUBJECTS[n][1]}]: {prompt_for(n)}\n")
        sys.exit()
    attempt = 1
    names = []
    for a in sys.argv[1:]:
        if a.startswith("--attempt="):
            attempt = int(a.split("=")[1])
        else:
            names.append(a)
    RAW.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(max_workers=7) as ex:
        futs = {ex.submit(make, n, attempt): n for n in names}
        for fut in cf.as_completed(futs):
            try:
                print(f"OK   {futs[fut]}  credits={fut.result()}", flush=True)
            except Exception as e:
                print(f"FAIL {futs[fut]}  {e}", flush=True)
