"""Write public/full/settings.json (the animation) and public/full/shots.json (the shot list).

Authoring script for the full video. Every event is tied to a sentence id and a spoken word,
and every event also writes its line of the shot list, so script.md always matches the video.

Page layout (world units = screen px at zoom 1), one region per chapter, toured in a loop:
    A (0,0) opening + ch1   B (3000,0) legs   C (6000,0) sugar   D (9000,0) heart
    H (0,2700) steps        G (3000,2700) speed  F (6000,2700) mood  E (9000,2700) brain
The ending travels from H back up to A, where the video began.
"""
import json, re, importlib.util
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("paths", ROOT / "scripts/full/paths.py")
_paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_paths)
PATHS = _paths.PATHS

WORDS = json.loads((ROOT / "public/full/words.json").read_text())["words"]
BY_SID = defaultdict(list)
for w in WORDS:
    BY_SID[w["sid"]].append(w)
clean = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


# ---------- time cues ----------
def cue(sid, say=None, nth=1, off=0.0, edge=None):
    c = {"s": sid}
    if say:
        c["say"] = say
        if nth != 1:
            c["nth"] = nth
    if off:
        c["offset"] = round(off, 3)
    if edge:
        c["edge"] = edge
    return c


def t(c):
    """Seconds for a cue (same rules as the template)."""
    if isinstance(c, (int, float)):
        return c
    ws = BY_SID[c["s"]]
    if c.get("say"):
        hits = [w for w in ws if clean(w["text"]) == clean(c["say"])]
        w = hits[c.get("nth", 1) - 1]
    else:
        w = ws[-1] if c.get("edge") == "end" else ws[0]
    return (w["end"] if c.get("edge") == "end" else w["start"]) + c.get("offset", 0)


def at(sid, say=None, off=0.0, nth=1):
    return cue(sid, say, nth, off)


def end(sid, off=0.0):
    return cue(sid, None, 1, off, "end")


# ---------- pictures ----------
_bbox = {}


def bbox(img):
    if img not in _bbox:
        im = Image.open(ROOT / "public/images" / f"{img}.png")
        W, H = im.size
        a = np.asarray(im.resize((W // 4, H // 4)))[..., 3] > 40
        ys, xs = np.where(a)
        _bbox[img] = (W, H, [round(xs.min() / a.shape[1], 4), round(ys.min() / a.shape[0], 4),
                             round((xs.max() + 1) / a.shape[1], 4), round((ys.max() + 1) / a.shape[0], 4)])
    return _bbox[img]


S = {"pictures": [], "magnifiers": [], "lights": [], "labels": [], "diagrams": [], "moves": []}
PIC = {}
SHOTS = defaultdict(lambda: {"screen": [], "camera": []})


def shot(sid, screen=None, camera=None):
    if screen:
        SHOTS[sid]["screen"].append(screen)
    if camera:
        SHOTS[sid]["camera"].append(camera)


def win(a, b, ind=None, outd=None, outscale=None):
    w = {"in": a, "out": b}
    if ind:
        w["inDur"] = ind
    if outd:
        w["outDur"] = outd
    if outscale:
        w["outScale"] = outscale
    return w


def pic(id, img, cx, cy, h=None, w=None, show=(), small=False, **kw):
    """Place a picture so its drawn content is centred on (cx, cy) with content height h or width w."""
    W, H, cb = bbox(img)
    cw, ch = cb[2] - cb[0], cb[3] - cb[1]
    if h is not None:
        scale = h / (ch * H)
    else:
        scale = w / (cw * W)
    pw, ph = W * scale, H * scale
    x = cx - (cb[0] + cb[2]) / 2 * pw
    y = cy - (cb[1] + cb[3]) / 2 * ph
    p = {"id": id, "src": f"images/{'small/' if small else ''}{img}.png", "x": round(x, 1), "y": round(y, 1),
         "w": round(pw, 1), "h": round(ph, 1), "content": cb, "show": list(show), **kw}
    S["pictures"].append(p)
    PIC[id] = (p, img)
    return p


def pt(id, nx, ny):
    p, _ = PIC[id]
    return [round(p["x"] + nx * p["w"], 1), round(p["y"] + ny * p["h"], 1)]


def cbox(id):
    p, _ = PIC[id]
    c = p["content"]
    return (p["x"] + c[0] * p["w"], p["y"] + c[1] * p["h"], p["x"] + c[2] * p["w"], p["y"] + c[3] * p["h"])


def light(on, path, a, dur, size=32, trail=None, repeat=None, note=None):
    if isinstance(path, str):
        img = PIC[on][1] if not on.startswith("lens:") else LENS_IMG[on[5:]]
        path = PATHS[img][path]
    l = {"on": on, "path": [list(map(lambda v: round(v, 4), p)) for p in path], "at": a, "dur": dur, "size": size}
    if trail:
        l["trail"] = trail
    if repeat:
        l["repeat"] = {"count": repeat[0], "every": repeat[1]}
    S["lights"].append(l)


def label(text, anchor, a, b, off=None, size=None, count=None, sub=None):
    l = {"text": text, "anchor": [round(anchor[0], 1), round(anchor[1], 1)], "in": a, "out": b}
    if off:
        l["offset"] = off
    if size:
        l["size"] = size
    if count:
        l["count"] = count
    if sub:
        l["sub"] = sub
    S["labels"].append(l)


def count(frm, to, a, dur=1.0, decimals=None):
    c = {"from": frm, "to": to, "at": a, "dur": dur}
    if decimals:
        c["decimals"] = decimals
    return c


def stroke(points, a, dur, px=None, width=None, opacity=None, smooth=False, cap=None):
    s = {"points": [[round(x, 1), round(y, 1)] for x, y in points], "at": a, "dur": dur}
    if px:
        s["px"] = px
    if width:
        s["width"] = width
    if opacity:
        s["opacity"] = opacity
    if smooth:
        s["smooth"] = True
    if cap:
        s["cap"] = cap
    return s


def diagram(id, x, y, show, strokes, dots=None):
    d = {"id": id, "x": x, "y": y, "show": list(show), "strokes": strokes}
    if dots:
        d["dots"] = dots
    S["diagrams"].append(d)
    return d


def bar(x, base, height, a, dur=1.0, width=46):
    """A vertical bar growing up from `base` (local coords)."""
    return stroke([(x, base), (x, base - height)], a, dur, width=width, cap="butt", opacity=0.75)


LENS_IMG = {}


def lens(id, source, src_r, center, r, img, focus, inner_w, ring, grow, links_out, out, grow_dur=0.8):
    """Magnifier: `img` placed so its normalized point `focus` sits at the lens centre, width inner_w."""
    W, H, _ = bbox(img)
    w = inner_w
    h = w * H / W
    S["magnifiers"].append({"id": id, "source": source, "sourceRadius": src_r, "center": center, "radius": r,
                            "inside": {"src": f"images/{img}.png", "x": round(center[0] - focus[0] * w, 1),
                                       "y": round(center[1] - focus[1] * h, 1), "w": round(w, 1), "h": round(h, 1)},
                            "ringAt": ring, "growAt": grow, "growDur": grow_dur, "linksOut": links_out, "out": out})
    LENS_IMG[id] = img


def shift(c, off):
    """The same cue, `off` seconds later."""
    c = dict(c)
    c["offset"] = round(c.get("offset", 0) + off, 3)
    return c


def cam(a, dur, x, y, z, note=None, sid=None):
    m = {"at": a, "dur": dur, "to": {"x": round(x, 1), "y": round(y, 1), "zoom": round(z, 3)}}
    if note:
        m["note"] = note
    S["moves"].append(m)
    if sid and note:
        shot(sid, camera=note)


def trail(prefix, spacing=300, h=130, opacity=0.5, clear=420):
    """Footprints walking along the camera's last move (a long trip between parts of the page), each one
    fading in just before the camera passes over it and out just after, so the trip is never an empty page."""
    m1, m0 = S["moves"][-1], S["moves"][-2]
    a, dur = m1["at"], m1["dur"]
    p0 = np.array([m0["to"]["x"], m0["to"]["y"]], float)
    p1 = np.array([m1["to"]["x"], m1["to"]["y"]], float)
    L = float(np.linalg.norm(p1 - p0))
    d = (p1 - p0) / L
    side = np.array([-d[1], d[0]])
    ang = float(np.degrees(np.arctan2(d[1], d[0])))
    n = int(L // spacing)
    u = np.linspace(0, 1, 2001)
    e = u ** 3 * (u * (u * 6 - 15) + 10)
    k = 0
    for i in range(1, n):
        dist = i * L / n
        if dist < clear or dist > L - clear:
            continue
        tk = float(np.interp(dist / L, e, u)) * dur
        c = p0 + d * dist + side * (32 if i % 2 else -32)
        pic(f"{prefix}{k}", "21_footprint", float(c[0]), float(c[1]), h=h, small=True, rotate=round(90 + ang, 1),
            flip=bool(i % 2), opacity=opacity, decor=True, show=[win(shift(a, tk - 0.6), shift(a, tk + 0.5), ind=0.3, outd=0.7)])
        k += 1


def footprints(prefix, x0, y0, n, step, h, show_fn, small=True, rotate=90, gap=40):
    """A walking trail: alternating left/right prints along +x."""
    ids = []
    for k in range(n):
        id = f"{prefix}{k}"
        pic(id, "21_footprint", x0 + k * step, y0 + (gap if k % 2 else -gap), h=h, show=show_fn(k), small=small,
            rotate=rotate, flip=bool(k % 2))
        ids.append(id)
    return ids


# =====================================================================
# Region A — opening and chapter 1 (the step counter)
# =====================================================================
A = (0, 0)
pic("pedo", "08_pedometer", 0, 0, h=560,
    show=[win(0, at("S024", off=0.9), ind=0.9), win(at("S139", "counter", -0.5), None, ind=0.8)])
pb = cbox("pedo")
cam(0, 10.5, 0, 0, 1.05, "slow push in on the step counter", "S001")
S["start"] = {"x": 0, "y": 0, "zoom": 0.86}
shot("S001", "The step counter fades in on the dotted page; “10,000 STEPS A DAY” fades in above it.")
label("10,000 STEPS A DAY", (0, pb[1] - 60), at("S001", "ten"), at("S002", off=-0.3))
light("pedo", "rim", at("S002", "step"), 1.8, size=34)
shot("S002", "A soft light travels once around the dial; “1965” counts up under it.")
label("{n}", (0, pb[3] + 70), at("S002", "Japan"), at("S004", off=-0.3), count=count(1900, 1965, at("S002", "1965"), 1.0))
label("“10,000-STEP METER”", (0, pb[1] - 60), at("S003", "meant"), at("S004", off=-0.35))
shot("S003", "“10,000-STEP METER” fades in above the counter.")
label("NEVER TESTED", (0, pb[1] - 60), at("S004", "tested"), at("S006", off=-0.3))
shot("S004", "“NEVER TESTED” replaces it.")
cam(at("S005"), 2.6, 420, 60, 0.82, "eases back and right, making room", "S005")
foot_A = footprints("footA", -300, 380, 5, 300, 150,
                    lambda k: [win(at("S005", "easy", 0.3 * k), at("S009", "come", -0.2)),
                               win(at("S145", "begin", 0.0) if k == 0 else at("S146", "first", 0.45 * (k - 1)), None)])
shot("S005", "Footprints appear one by one along the bottom of the page.")
pic("walkerA", "07_walking_figure", 1050, -40, h=640,
    show=[win(at("S006", "find"), at("S009", "come", -0.2)), win(at("S147", "Every"), None)])
shot("S006", "A walking figure fades in beside the counter.")
light("walkerA", "body", at("S007", "inside"), 1.8)
shot("S007", "A light rises through the walker from foot to head.")
label("HOW MANY STEPS?", (350, 540), at("S008", "steps"), at("S009", "come", -0.3))
shot("S008", "“HOW MANY STEPS?” fades in under the footprints.")
cam(at("S009", "come"), 2.2, 0, 0, 1.12, "pushes back in to the step counter", "S009")
light("pedo", "needle", at("S009", "close"), 1.1, size=30)
shot("S009", "Walker and footprints fade; a light runs along the needle on “close”.")

# --- chapter 1 ---
cam(at("S010"), 2.5, 0, -10, 1.3, "slow push closer", "S010")
label("THE STEP COUNTER", (0, pb[1] - 60), at("S010", "step"), at("S011", off=-0.25))
shot("S010", "“THE STEP COUNTER” fades in above it.")
cam(at("S011", off=-0.3), 1.6, -520, 0, 1.0, "drifts left onto open page", "S011")
label("JAPAN · 1960s", (-830, -40), at("S011", "Japan"), at("S012", off=-0.3))
shot("S011", "“JAPAN · 1960s” fades in to the left of the counter.")
label("TOKYO 1964", (-830, -40), at("S012", "Tokyo"), at("S013", off=-0.25), sub="OLYMPIC GAMES")
shot("S012", "“TOKYO 1964 / OLYMPIC GAMES” replaces it.")
cam(at("S013", off=-0.3), 1.5, 0, -30, 1.22, "back onto the counter", "S013")
label("YAMASA", (-340, 0), at("S013", "Yamasa"), at("S014", off=-0.25))
light("pedo", "clip", at("S013", "clipped"), 1.0, size=30)
shot("S013", "“YAMASA” to the left of the counter; a light slides down the belt clip on “clipped”.")
lens("pedoLens", pt("pedo", 0.56, 0.48), 46, [560, -30], 245, "08_pedometer", (0.545, 0.495), 1000,
     ring=at("S014", "Inside"), grow=at("S014", "weight"), links_out=at("S015", off=-0.35), out=at("S015", off=-0.3))
cam(at("S014", off=-0.2), 1.4, 280, -20, 1.08, "widens to hold the counter and the lens", "S014")
light("lens:pedoLens", "needle", at("S014", "moved"), 1.1, size=34)
label("+1", (560, 300), at("S014", "one", -0.2), at("S015", off=-0.3))
shot("S014", "A ring circles the needle and a magnifying circle grows out of it to the right, joined by two thin lines; "
             "inside, the needle glows as it moves; “+1” fades in under the lens.")
label("MANPO-KEI", (620, -230), at("S015", "manpo-kei"), at("S019", off=-0.3))
shot("S015", "“MANPO-KEI” fades in to the right of the counter.")
label("MAN", (420, -40), at("S016", "Man"), at("S019", off=-0.3), sub="10,000")
shot("S016", "“MAN / 10,000” appears under it.")
label("PO", (620, -40), at("S017", "Po"), at("S019", off=-0.3), sub="STEP")
shot("S017", "“PO / STEP” appears next to it.")
label("KEI", (820, -40), at("S018", "Kei"), at("S019", off=-0.3), sub="METER")
shot("S018", "“KEI / METER” completes the row.")
label("= 10,000-STEP METER", (620, 120), at("S019", "together", 0.3), at("S021", off=-0.3))
light("pedo", "rim", at("S019", "meter"), 1.6, size=34)
shot("S019", "The three words fade; “= 10,000-STEP METER” appears; light circles the dial.")
cam(at("S020"), 3.0, 0, 150, 0.9, "eases back and down", "S020")
light("pedo", "needle", at("S020", "good"), 1.0, size=30)
shot("S020", "Light runs up the needle.")
label("A NAME, NOT A FINDING", (580, 0), at("S021", "finding"), at("S022", "researcher"), size=34)
shot("S021", "“A NAME, NOT A FINDING” fades in beside the counter.")
tl_y = 430
diagram("timelineA", 0, tl_y, [win(at("S022"), at("S024", off=0.6))], [
    stroke([(-700, 0), (700, 0)], at("S022", "Years"), 1.6, px=2.6),
    stroke([(-700, -22), (-700, 22)], at("S022", "Years", 0.2), 0.4, px=2.6),
    stroke([(700, -22), (700, 22)], at("S022", "Harvard"), 0.4, px=2.6),
])
label("1965", (-700, tl_y + 60), at("S022", "Years", 0.3), at("S024", off=-0.1), size=34)
label("2019", (700, tl_y + 60), at("S022", "Harvard"), at("S024", off=-0.1), size=34)
label("I-MIN LEE", (700, tl_y - 130), at("S022", "Lee"), at("S024", off=-0.1), sub="HARVARD")
light("diagram:timelineA", [(700, 0), (0, 0), (-700, 0)], at("S022", "looking"), 1.8, size=30)
shot("S022", "A timeline draws itself under the counter from “1965” to “2019”; “I-MIN LEE / HARVARD” at the 2019 end; "
             "a light travels back along it to 1965.")
label("BRAND NAME", (-700, tl_y - 110), at("S023", "brand"), at("S024", off=-0.1))
light("pedo", "rim", at("S023", "name"), 1.4, size=34)
shot("S023", "“BRAND NAME” at the 1965 end; light circles the dial.")
cam(at("S024"), 2.4, 1950, 0, 1.0, "glides right along the page", "S024")
for k in range(6):
    pic(f"people{k}", "07_walking_figure", 1500 + k * 180, 0, h=300, small=True,
        show=[win(at("S024", off=0.5 + 0.2 * k), at("S026") if k < 5 else at("S027", "step", 0.9))])
label("REAL PEOPLE", (1950, 260), at("S024", "people"), at("S025", "found", 0.6), sub="WEARING STEP COUNTERS")
shot("S024", "Counter and timeline fade; a row of six small walkers appears one by one; “REAL PEOPLE / WEARING STEP COUNTERS”.")
light("people1", "body", at("S025", "found"), 1.4, size=24)
light("people3", "body", at("S025", "found", 0.25), 1.4, size=24)
shot("S025", "Lights rise through two of the walkers.")
cam(at("S026"), 2.0, 2400, 0, 1.6, "pushes toward the last walker", "S026")
light("people5", "legs", at("S026", "simpler"), 1.2, size=26)
shot("S026", "The other walkers fade; a light runs down the last walker's legs.")
cam(at("S027", "step"), 2.3, 3000, 0, 0.95, "carries on right to the next part of the page", "S027")
shot("S027", "The last walker fades as the camera travels on; the legs fade in ahead.")

# =====================================================================
# Region B — chapter 2 (legs, calf pump)
# =====================================================================
B = 3000
pic("legs", "02_legs_striding", B, 0, h=760,
    show=[win(at("S027", "step", 0.5), at("S034", "veins")), win(at("S039", off=-0.2), at("S041", off=0.9))])
lb = cbox("legs")
label("ONE STEP", (B, lb[1] - 60), at("S028", "step"), at("S029", off=-0.2))
light("legs", "front_leg_down", at("S028", "step", 0.2), 1.6)
shot("S028", "The striding legs fade in; “ONE STEP” above them; a light runs down the front leg.")
label("BIG MUSCLES", (B - 640, 0), at("S029", "biggest"), at("S030", off=-0.2))
light("legs", "front_thigh", at("S029", "biggest"), 1.3)
light("legs", "back_thigh", at("S029", "biggest", 0.1), 1.3)
shot("S029", "“BIG MUSCLES” to the left; lights travel down both thighs.")
lens("thighLens", pt("legs", 0.60, 0.38), 42, [B + 640, -150], 225, "03_thigh_muscle", (0.49, 0.40), 600,
     ring=at("S030", "front"), grow=at("S030", "thigh"), links_out=end("S030", 0.25), out=end("S030", 0.3))
cam(at("S030", off=-0.2), 1.6, B + 200, -20, 0.95, "shifts right to make room for a lens", "S030")
light("lens:thighLens", "fiber_mid", at("S030", "tighten"), 1.2)
light("lens:thighLens", "fiber_left", at("S030", "tighten", 0.12), 1.2, size=28)
light("legs", "knee", at("S030", "knee"), 1.0, size=28)
label("FRONT OF THIGH", (B + 640, 160), at("S030", "thigh", 0.4), end("S030", 0.3))
shot("S030", "A ring circles the front thigh; a magnifying circle grows out to the right showing the thigh muscle; "
             "lights run down its fibers on “tighten”; a light circles the knee on “steady”.")
light("legs", "back_hip", at("S031", "back"), 1.4)
label("BACK OF HIP & THIGH", (B + 760, -80), at("S031", "hip"), at("S032", off=-0.2))
diagram("forward", B, lb[3] + 30, [win(at("S031", "push"), at("S032", off=-0.2))], [
    stroke([(-170, 0), (170, 0)], at("S031", "forward", -0.3), 0.8, px=2.6),
    stroke([(140, -18), (172, 0), (140, 18)], at("S031", "forward", 0.3), 0.4, px=2.6),
])
shot("S031", "A light runs down the back of the hip and thigh; “BACK OF HIP & THIGH”; a thin arrow draws itself forward under the legs.")
lens("calfLens", pt("legs", 0.25, 0.50), 40, [B - 690, -140], 215, "09_calf_muscle", (0.5, 0.40), 760,
     ring=at("S032", "calf"), grow=at("S032", "muscle"), links_out=at("S034", off=-0.25), out=at("S034", off=-0.2))
cam(at("S032", off=-0.25), 1.5, B - 170, -20, 0.95, "shifts left toward the calf", "S032")
light("lens:calfLens", "up_inner", at("S032", "squeezes"), 1.2)
light("lens:calfLens", "up_outer", at("S032", "squeezes", 0.12), 1.2, size=28)
label("CALF", (B - 690, 130), at("S032", "calf", 0.6), at("S034", off=-0.25))
shot("S032", "A ring circles the back calf; a magnifying circle grows out to the left with the calf muscle; lights squeeze up it.")
light("lens:calfLens", "up_inner", at("S033", "squeeze"), 1.2)
shot("S033", "The calf lights up again.")
cam(at("S034", off=-0.3), 1.6, B, 0, 1.0, "recentres", "S034")
pic("vein", "10_vein_valves", B + 150, 0, h=700, show=[win(at("S034", "veins"), at("S039", off=-0.3))])
vb = cbox("vein")
label("ONE-WAY VALVES", (B + 600, -120), at("S034", "valves"), at("S035", off=-0.2))
light("vein", "valve_high", at("S034", "doors"), 0.9, size=30)
light("vein", "valve_low", at("S034", "doors", 0.25), 0.9, size=30)
shot("S034", "Legs and lens fade; a cut-open vein with two valves fades in; “ONE-WAY VALVES”; both valves glow softly.")
pic("calf2", "09_calf_muscle", B - 250, 0, h=700, show=[win(at("S035", "calf"), at("S039", off=-0.3))],
    grow=[{"at": at("S035", "tightens"), "dur": 0.35, "to": 0.95}, {"at": at("S035", "tightens", 0.35), "dur": 0.5, "to": 1.0526}])
light("vein", "up", at("S035", "pushes"), 1.6, repeat=(3, 0.5))
label("UP TO THE HEART", (B + 150, vb[1] - 60), at("S035", "heart"), at("S036", off=-0.2))
shot("S035", "The calf muscle fades in beside the vein and gives a small squeeze; lights flow up through the vein; “UP TO THE HEART”.")
cam(at("S036", off=-0.2), 1.6, B + 150, 0, 1.18, "pushes in on the vein", "S036")
light("vein", "valve_high", at("S036", "close"), 0.8, size=30)
light("vein", "slide_back", at("S036", "slide"), 0.9, size=28)
shot("S036", "The upper valve glows as it closes; a light slips down and stops at the valve.")
cam(at("S037", off=-0.1), 1.6, B, 0, 1.0, "eases back out", "S037")
label("CALF MUSCLE PUMP", (B, vb[3] + 60), at("S037", "calf"), at("S038", off=-0.2))
light("calf2", "up_inner", at("S037", "pump"), 1.2)
light("vein", "up", at("S037", "pump", 0.3), 1.4)
shot("S037", "“CALF MUSCLE PUMP” under both; lights rise through the calf and the vein.")
label("SITTING STILL", (B + 640, 0), at("S038", "sit"), at("S039", off=-0.3), sub="ON A LONG FLIGHT")
light("vein", "pool", at("S038", "swell", -0.4), 2.2, size=30)
shot("S038", "“SITTING STILL / ON A LONG FLIGHT”; a slow light settles at the bottom of the vein.")
light("legs", "front_leg_up", at("S039", "moves"), 1.6)
light("legs", "back_leg_up", at("S039", "moves", 0.15), 1.6)
shot("S039", "Vein and calf fade; the legs return; lights travel up both legs.")
label("FUEL?", (B + 620, -40), at("S040", "fuel"), at("S041", off=-0.05))
light("legs", "front_thigh", at("S040", "working"), 1.2)
shot("S040", "Lights in both thighs; “FUEL?” above.")
cam(at("S041"), 2.4, 5800, -50, 1.05, "travels right to the next part of the page", "S041")
trail("trBC")
shot("S041", "The camera travels right; footprints walk along the page under it as the legs fade behind.")

# =====================================================================
# Region C — chapter 3 (sugar)
# =====================================================================
C = 6000
pic("plate", "12_meal_plate", C - 750, -60, w=470, show=[win(at("S041", off=1.6), at("S044", off=-0.3))])
pic("cube", "11_sugar_cube", C - 370, -60, h=170, show=[win(at("S042", "sugar"), at("S044", off=-0.3))])
pic("vesselC", "04_blood_vessel", C + 250, -60, w=540,
    show=[win(at("S042", "blood", -0.1), at("S046", "insulin")), win(at("S050", "legs"), at("S051", off=0.6)),
          win(at("S059", off=-0.3), at("S060", off=0.6))])
light("vesselC", "lane_mid", at("S042", "blood"), 1.6, repeat=(3, 0.6))
shot("S042", "A plate of food fades in, then a sugar cube beside it, then a blood vessel; lights start flowing through the vessel.")
label("WHERE DOES IT GO?", (C - 300, 230), at("S043", "store"), at("S044", off=-0.25))
light("vesselC", "lane_top", at("S043", "clear"), 1.6, repeat=(2, 0.7))
shot("S043", "More lights in the vessel; “WHERE DOES IT GO?”.")
cam(at("S044", off=-0.3), 1.6, C + 350, -60, 1.0, "glides right past the vessel", "S044")
pic("muscleC", "03_thigh_muscle", C + 900, -60, h=600, show=[win(at("S044", "muscles"), at("S046", "insulin"))])
light("muscleC", "fiber_mid", at("S044", "muscles", 0.4), 1.4)
shot("S044", "Plate and cube fade; a thigh muscle fades in beside the vessel; a light runs down its fibers.")
diagram("pct80", C + 350, 340, [win(at("S045", "measured"), at("S046", "insulin"))], [
    stroke([(-500, 0), (500, 0)], at("S045", "measured"), 0.8, px=2.0, opacity=0.35),
    stroke([(-500, 0), (300, 0)], at("S045", "eighty"), 1.4, width=40, cap="butt", opacity=0.75),
])
label("{n}%", (C + 350, 225), at("S045", "eighty"), at("S046", "insulin"), count=count(0, 80, at("S045", "eighty"), 1.4),
      sub="OF IT WENT INTO MUSCLE")
light("muscleC", "fiber_left", at("S045", "muscle"), 1.2, size=28)
shot("S045", "A thin 100% line draws under them, then a bar fills to 80%; “80% / OF IT WENT INTO MUSCLE” counts up; light in the muscle.")
pic("key", "14_key", C - 200, -60, w=560, show=[win(at("S046", "insulin"), at("S048", "working", 0.6))])
label("INSULIN", (C - 200, 140), at("S046", "insulin"), at("S048", off=-0.3))
shot("S046", "Vessel, muscle and bar fade; an old key fades in; “INSULIN”.")
light("key", "shaft", at("S047", "key"), 1.2)
shot("S047", "A light slides along the key.")
pic("fiber", "13_muscle_fiber", C + 560, -60, w=600, show=[win(at("S048", "working"), at("S051", off=0.6))],
    grow=[{"at": at("S049", "contracts"), "dur": 0.35, "to": 0.96}, {"at": at("S049", "contracts", 0.35), "dur": 0.6, "to": 1.0417}])
shot("S048", "A bundle of muscle fibers fades in to the right; the key fades.")
cam(at("S049", off=-0.3), 1.6, C + 560, -60, 1.25, "pushes in on the fibers", "S049")
fiber_dots = [pt("fiber", x, y) for x, y in [(0.72, 0.25), (0.62, 0.29), (0.52, 0.33), (0.66, 0.40), (0.55, 0.45)]]
diagram("doors", 0, 0, [win(at("S049", "doors", -0.1), at("S050", off=-0.3))], [],
        dots=[{"at": d, "time": at("S049", "doors", 0.12 * k), "r": 7} for k, d in enumerate(fiber_dots)])
label("SUGAR DOORS", (C + 560, 190), at("S049", "doors"), at("S050", off=-0.3), sub="GLUT4")
light("fiber", "in_top", at("S049", "pulls"), 1.5)
light("fiber", "in_low", at("S049", "pulls", 0.15), 1.5, size=28)
shot("S049", "The fiber bundle gives a small squeeze; dots appear along its surface; “SUGAR DOORS / GLUT4”; lights flow into the bundle.")
cam(at("S050", off=-0.2), 1.6, C + 420, -60, 0.98, "eases back", "S050")
light("vesselC", "lane_mid", at("S050", "soak"), 1.5, repeat=(2, 0.5))
light("fiber", "in_top", at("S050", "soak", 0.5), 1.4)
label("WHILE YOU MOVE", (C + 420, 230), at("S050", "moving"), at("S051", off=-0.3))
shot("S050", "The vessel returns beside the fibers; lights flow from blood into muscle; “WHILE YOU MOVE”.")

C2 = (C, 980)
cam(at("S051", off=-0.3), 2.0, C, 980, 1.0, "moves down the page to a comparison", "S051")
label("TIMING", (C, C2[1] - 330), at("S051", "timing"), at("S052", "Zealand", -0.35))
shot("S051", "“TIMING” fades in over an empty part of the page.")
boxL, boxR = -420, 420
diagram("plans", C, C2[1], [win(at("S052", "two", -0.1), at("S059", off=0.6))], [
    stroke([(boxL - 320, -200), (boxL + 320, -200), (boxL + 320, 220), (boxL - 320, 220), (boxL - 320, -200)], at("S052", "two"), 1.0, px=2.2, opacity=0.6),
    stroke([(boxR - 320, -200), (boxR + 320, -200), (boxR + 320, 220), (boxR - 320, 220), (boxR - 320, -200)], at("S052", "plans"), 1.0, px=2.2, opacity=0.6),
])
label("NEW ZEALAND STUDY", (C, C2[1] - 330), at("S052", "Zealand"), at("S053", off=-0.2), sub="TYPE 2 DIABETES")
shot("S052", "“NEW ZEALAND STUDY / TYPE 2 DIABETES”; two empty boxes draw themselves side by side.")
pic("walkerP1", "07_walking_figure", C + boxL, C2[1] + 5, h=200, small=True, show=[win(at("S053", "walk"), at("S056", off=-0.2))])
diagram("plan1bar", C + boxL, C2[1] + 150, [win(at("S053", "day"), at("S056", off=-0.2))], [
    stroke([(-240, 0), (240, 0)], at("S053", "day"), 1.2, width=22, cap="butt", opacity=0.7)])
label("30 MIN", (C + boxL, C2[1] - 165), at("S053", "thirty-minute"), at("S056", off=-0.2), size=36, sub="ONCE A DAY")
shot("S053", "Left box: “30 MIN / ONCE A DAY”, a small walker, and one long bar.")
for k in range(3):
    pic(f"plateP{k}", "12_meal_plate", C + boxR - 170 + k * 170, C2[1] - 10, w=140, small=True,
        show=[win(at("S054", "each", 0.2 * k), at("S056", off=-0.2))])
diagram("plan2bars", C + boxR, C2[1] + 150, [win(at("S054", "meal"), at("S056", off=-0.2))], [
    stroke([(-240 + k * 170, 0), (-100 + k * 170, 0)], at("S054", "meal", 0.15 * k), 0.6, width=22, cap="butt", opacity=0.7) for k in range(3)])
label("10 MIN × 3", (C + boxR, C2[1] - 165), at("S054", "ten-minute"), at("S056", off=-0.2), size=36, sub="AFTER EACH MEAL")
shot("S054", "Right box: three small plates appear, each followed by a short bar; “10 MIN × 3 / AFTER EACH MEAL”.")
light("diagram:plan1bar", [(-240, 0), (240, 0)], at("S055", "Same"), 1.0, size=26)
light("diagram:plan2bars", [(-240, 0), (240, 0)], at("S055", "Same", 0.1), 1.0, size=26)
label("SAME 30 MINUTES", (C, C2[1] + 300), at("S055", "total"), at("S056", off=-0.2), size=34)
shot("S055", "Lights run along both bars; “SAME 30 MINUTES” under the boxes.")
barM, barD = boxR - 80, boxR + 130
diagram("sugarBars", C, C2[1] + 190, [win(at("S056", "lowered", -0.1), at("S059", off=0.6))], [
    bar(boxL, 0, 300, at("S056", "lowered"), 1.2, width=90),
    bar(barM, 0, 264, at("S056", "lowered", 0.4), 1.2, width=90),
])
label("BLOOD SUGAR AFTER MEALS", (C, C2[1] - 330), at("S056", "lowered", -0.2), at("S059", off=-0.5), size=34)
label("ONCE A DAY", (C + boxL, C2[1] + 260), at("S056", "lowered"), at("S059", off=-0.5), size=30)
label("AFTER MEALS", (C + boxR, C2[1] + 260), at("S056", "lowered", 0.4), at("S059", off=-0.5), size=30)
label("−{n}%", (C + barM, C2[1] + 190 - 264 - 55), at("S056", "twelve", -0.3), at("S059", off=-0.5), size=34,
      count=count(0, 12, at("S056", "twelve"), 0.8))
shot("S056", "Boxes empty; “BLOOD SUGAR AFTER MEALS”; two bars grow — after-meal walking ends about 12% lower; “−12%” counts in.")
diagram("dinnerBar", C, C2[1] + 190, [win(at("S057", "dinner"), at("S059", off=0.6))], [
    bar(barD, 0, 234, at("S057", "dinner"), 1.0, width=60)])
label("DINNER −{n}%", (C + barD + 20, C2[1] + 190 - 234 - 45), at("S057", "twenty-two", -0.3), at("S059", off=-0.5), size=26,
      count=count(0, 22, at("S057", "twenty-two"), 0.8))
shot("S057", "A thinner third bar grows for dinner; “DINNER −22%”.")
light("diagram:sugarBars", [(boxL, 0), (boxL, -300)], at("S058", "works"), 1.0, size=26)
light("diagram:sugarBars", [(barM, 0), (barM, -264)], at("S058", "works", 0.15), 1.0, size=26)
shot("S058", "Lights rise up both bars.")
cam(at("S059", off=-0.3), 1.8, C + 250, -60, 1.1, "rises back up to the blood vessel", "S059")
light("vesselC", [list(p) for p in reversed(PATHS["04_blood_vessel"]["lane_mid"])], at("S059", "blood"), 1.5, repeat=(3, 0.5))
shot("S059", "Charts fade; the blood vessel returns; lights flow through it toward the right.")
cam(at("S060", off=-0.4), 2.6, 8800, -20, 0.95, "travels right to the heart", "S060")
trail("trCD")
shot("S060", "The camera travels right with footprints walking under it; the vessel fades behind and the heart fades in ahead.")

# =====================================================================
# Region D — chapter 4 (heart)
# =====================================================================
D = 9000
pic("heart", "05_heart", D - 300, -20, h=620, show=[win(at("S060", off=0.9), at("S067", off=0.5))],
    pulse={"from": at("S061"), "to": at("S063", "faster"), "bpm": 70, "amount": 0.022})
hb = cbox("heart")
light("heart", "aorta", at("S061", "walking"), 1.0, size=28)
shot("S061", "The heart starts a slow, gentle beat; a light flows up the aorta.")
cam(at("S062", off=-0.3), 1.5, D + 50, -20, 0.95, "shifts right", "S062")


def ecg(n, width=700, amp=110):
    pts, step = [], width / n
    for k in range(n):
        x0 = k * step
        pts += [(x0, 0), (x0 + step * 0.35, 0), (x0 + step * 0.42, -amp * 0.18), (x0 + step * 0.48, 0),
                (x0 + step * 0.52, amp * 0.25), (x0 + step * 0.56, -amp), (x0 + step * 0.60, amp * 0.35), (x0 + step * 0.64, 0),
                (x0 + step * 0.78, -amp * 0.22), (x0 + step * 0.88, 0)]
    pts.append((width, 0))
    return pts


diagram("ecg1", D + 180, -150, [win(at("S062", "beats"), at("S064", off=-0.3))], [stroke(ecg(4), at("S062", "beats"), 2.4, px=2.6)])
label("60–100", (D + 530, -330), at("S062", "sixty"), at("S064", off=-0.3), sub="BEATS A MINUTE AT REST")
light("diagram:ecg1", ecg(4), at("S062", "minute"), 1.8, size=26)
shot("S062", "A heartbeat trace draws itself beside the heart; “60–100 / BEATS A MINUTE AT REST”; a light runs along the trace.")
diagram("ecg2", D + 180, 150, [win(at("S063", "faster", -0.2), at("S064", off=-0.3))], [stroke(ecg(7), at("S063", "faster"), 1.6, px=2.6)])
label("WALKING", (D + 530, 280), at("S063", "faster"), at("S064", off=-0.3), size=34)
S["pictures"][-1 if False else [i for i, p in enumerate(S["pictures"]) if p["id"] == "heart"][0]]["pulse"] = {
    "from": at("S061"), "to": end("S066", 0.5), "bpm": 70, "amount": 0.022}
pic("heartFast", "05_heart", D - 300, -20, h=620, show=[], opacity=0)  # placeholder removed below
S["pictures"].pop()
shot("S063", "A second, quicker trace draws itself below the first; “WALKING”.")
cam(at("S064", off=-0.3), 1.6, D - 520, 60, 0.85, "pans left and eases back", "S064")
pic("muscleD", "03_thigh_muscle", D - 1180, -120, h=430, show=[win(at("S064", "muscles", -0.3), at("S066", off=-0.3))])
flow_pts = [(hb[0] + 60, -150), (D - 820, -260), (D - 1060, -260)]
diagram("flowD", 0, 0, [win(at("S064", "sends", -0.1), at("S066", off=-0.3))], [stroke(flow_pts, at("S064", "sends"), 1.0, px=2.4, smooth=True)])
light("diagram:flowD", flow_pts, at("S064", "blood"), 1.0, size=28, repeat=(2, 0.5))
shot("S064", "Traces fade; a thigh muscle fades in to the left; a thin line draws from the heart to it and lights travel along it.")
pic("vesselD", "04_blood_vessel", D - 1180, 330, w=440, show=[win(at("S065", "vessels"), at("S066", off=-0.3))],
    grow=[{"at": at("S065", "widen"), "dur": 1.2, "to": 1.12}])
light("vesselD", "lane_mid", at("S065", "through"), 1.2, repeat=(2, 0.4))
label("VESSELS WIDEN", (D - 1180, 520), at("S065", "widen"), at("S066", off=-0.3), size=34)
shot("S065", "A blood vessel fades in under the muscle and slowly widens; lights pass through; “VESSELS WIDEN”.")
cam(at("S066", off=-0.3), 1.5, D - 300, -20, 1.0, "back onto the heart", "S066")
light("heart", "aorta", at("S066", "heart"), 1.0, size=28)
light("heart", "left_artery", at("S066", "heart", 0.1), 1.0, size=26)
label("THE HEART ADAPTS", (D - 300, hb[3] + 60), at("S066", "adapts"), at("S067", off=-0.3))
shot("S066", "Muscle and vessel fade; lights run through the heart; “THE HEART ADAPTS”.")

D2 = (D, 980)
cam(at("S067", off=-0.3), 1.8, D - 150, 980, 1.0, "moves down the page", "S067")
pic("steth", "15_stethoscope", D - 760, 980, h=500, show=[win(at("S067", off=0.3), at("S072", off=0.4))])
diagram("bpAxes", D + 150, 980, [win(at("S067", "after"), at("S072", off=0.4))], [
    stroke([(-430, 200), (430, 200)], at("S067", "after"), 0.8, px=2.2, opacity=0.6),
    stroke([(-430, 200), (-430, -220)], at("S067", "after", 0.2), 0.8, px=2.2, opacity=0.6),
])
shot("S067", "Heart fades; a stethoscope and the empty axes of a chart fade in further down the page.")
bp1 = [(-410, -100), (-250, -100), (-185, -150), (-120, -150), (-60, -40), (0, -10), (150, -15), (300, -25), (420, -45)]
diagram("bpLine", D + 150, 980, [win(at("S068", "blood"), at("S071", off=-0.3))],
        [stroke(bp1, at("S068", "blood"), 2.6, px=2.8, smooth=True)],
        dots=[{"at": [0, -10], "time": at("S070", "dip", -0.2), "r": 8}])
label("BLOOD PRESSURE", (D + 150, 980 - 300), at("S068", "blood"), at("S069", off=-0.25))
label("BEFORE", (D + 150 - 330, 980 + 255), at("S068", "before"), at("S072", off=0.2), size=28)
label("FOR HOURS", (D + 150 + 230, 980 + 255), at("S068", "hours"), at("S072", off=0.2), size=28)
shot("S068", "A blood-pressure line draws itself: steady, a bump during the walk, then lower for a long stretch; "
             "“BLOOD PRESSURE”, “BEFORE”, “FOR HOURS”.")
label("POST-EXERCISE HYPOTENSION", (D + 150, 980 - 300), at("S069", "post-exercise"), at("S070", off=-0.25), size=34)
light("diagram:bpLine", bp1[4:], at("S069", "hypotension"), 1.4, size=28)
shot("S069", "“POST-EXERCISE HYPOTENSION”; a light runs along the low part of the line.")
label("ONE WALK, A SMALL DIP", (D + 150, 980 - 300), at("S070", "One"), at("S071", off=-0.25), size=34)
shot("S070", "A dot marks the dip; “ONE WALK, A SMALL DIP”.")
bp2 = [(-410, -100)]
for k in range(3):
    x0 = -380 + k * 270
    bp2 += [(x0 + 40, -100), (x0 + 80, -130), (x0 + 120, -40), (x0 + 200, -45)]
bp2 += [(420, -55)]
diagram("bpLine2", D + 150, 980, [win(at("S071", "most", -0.1), at("S072", off=0.4))], [stroke(bp2, at("S071", "days"), 1.6, px=2.8, smooth=True)])
label("MOST DAYS", (D + 150, 980 - 300), at("S071", "days"), at("S072", off=0.2), size=34)
shot("S071", "The first line fades; a new one draws three days of walks, each followed by a dip; “MOST DAYS”.")
D3 = (D + 1150, 980)
cam(at("S072", off=-0.3), 1.6, D3[0], 980, 1.0, "glides right", "S072")
label("HOW MUCH?", (D3[0], 980 - 300), at("S072", "much"), at("S073", "150", -0.6))
shot("S072", "Chart fades; “HOW MUCH?” over open page.")
sq = [(-540 + k * 180, 0) for k in range(7)]
diagram("week", D3[0], 980, [win(at("S073", off=-0.2), at("S078", off=0.5))], [
    stroke([(x - 70, -70), (x + 70, -70), (x + 70, 70), (x - 70, 70), (x - 70, -70)], at("S073", off=0.15 * k), 0.6, px=2.2, opacity=0.6)
    for k, (x, _) in enumerate(sq)])
label("{n} MIN", (D3[0], 980 - 300), at("S073", "150"), at("S074", off=-0.2), count=count(0, 150, at("S073", "150"), 1.2), sub="A WEEK · WHO")
shot("S073", "Seven squares (the days of a week) draw in a row; “150 MIN / A WEEK · WHO” counts up.")
diagram("weekFill", D3[0], 980, [win(at("S074", "twenty", -0.1), at("S076", "once", -0.1))], [
    stroke([(x - 50, 0), (x + 50, 0)], at("S074", "day", 0.08 * k), 0.4, width=90, cap="butt", opacity=0.5) for k, (x, _) in enumerate(sq)])
label("≈ 20 MIN A DAY", (D3[0], 980 + 200), at("S074", "twenty"), at("S076", off=-0.3))
shot("S074", "Each day fills in; “≈ 20 MIN A DAY”.")
pic("walkerD", "07_walking_figure", D3[0] + 760, 960, h=330, small=True, show=[win(at("S075", "brisk"), at("S078", off=0.5))])
light("walkerD", "body", at("S075", "counts"), 1.2, size=24)
shot("S075", "A small walker fades in at the end of the week; a light rises through it.")
diagram("weekSplit", D3[0], 980, [win(at("S076", "once", -0.2), at("S078", off=0.5))], [
    stroke([(x - 52 + j * 40, 0), (x - 32 + j * 40, 0)], at("S076", "once", 0.05 * k + 0.1 * j), 0.3, width=90, cap="butt", opacity=0.5)
    for k, (x, _) in enumerate(sq) for j in range(3)])
shot("S076", "Each day's block re-draws as three short pieces.")
light("diagram:weekSplit", [(-560, 0), (560, 0)], at("S077", "add"), 1.4, size=30)
label("SHORT WALKS ADD UP", (D3[0], 980 + 200), at("S077", "Short"), at("S078", off=-0.3))
shot("S077", "A light runs across the whole week; “SHORT WALKS ADD UP”.")
cam(at("S078"), 2.2, D - 300, 2650, 1.0, "travels down the page to the brain", "S078")
trail("trDE")
shot("S078", "The camera travels down the page with footprints walking under it; the week fades behind.")

# =====================================================================
# Region E — chapter 5 (brain)
# =====================================================================
E = (D, 2700)
pic("brain", "06_brain", D - 300, 2650, w=640,
    show=[win(at("S078", off=1.3), at("S083", off=0.5)), win(at("S093", off=0.0), at("S096", "feel", 0.6))])
light("brain", "fold_high", at("S079", "thinking"), 1.2)
shot("S079", "The brain fades in; a light runs along its upper folds.")
lens("hippoLens", pt("brain", 0.50, 0.55), 40, [D + 420, 2600], 235, "16_hippocampus", (0.51, 0.50), 640,
     ring=at("S080", "Deep"), grow=at("S080", "curled-up"), links_out=at("S083", off=-0.35), out=at("S083", off=-0.3))
cam(at("S080", off=-0.2), 1.6, D + 50, 2650, 1.0, "shifts right for a lens", "S080")
label("HIPPOCAMPUS", (D + 420, 2600 + 300), at("S080", "hippocampus"), at("S082", off=-0.3))
shot("S080", "A ring circles a spot deep in the brain; a magnifying circle grows out to the right showing the curled hippocampus; “HIPPOCAMPUS”.")
cam(at("S081", off=-0.2), 1.3, D + 320, 2650, 0.95, "drifts further right", "S081")
pic("seahorse", "17_seahorse", D + 960, 2620, h=480, show=[win(at("S081", "seahorse"), at("S082", off=-0.2))])
light("lens:hippoLens", "curve", at("S081", "shape"), 1.3)
shot("S081", "A seahorse fades in beside the lens; a light traces the hippocampus's curl.")
label("NEW MEMORIES", (D + 420, 2600 + 300), at("S082", "memories"), at("S083", off=-0.3))
light("lens:hippoLens", "curve", at("S082", "form"), 1.3, repeat=(2, 0.6))
shot("S082", "Seahorse fades; lights travel along the hippocampus; “NEW MEMORIES”.")
E2 = (D, 3520)
cam(at("S083", off=-0.3), 1.8, D, 3480, 1.0, "moves down the page", "S083")
pic("hippoC", "16_hippocampus", D, 3440, w=420, show=[win(at("S083", off=0.3), at("S084", "walked", -0.1))],
    grow=[{"at": at("S083", "shrinks"), "dur": 2.0, "to": 0.88}])
label("SHRINKS WITH AGE", (D, 3440 + 285), at("S083", "shrinks"), at("S084", "walked", -0.1))
shot("S083", "Brain and lens fade; a single hippocampus fades in and slowly shrinks; “SHRINKS WITH AGE”.")
pic("walkerE", "07_walking_figure", D - 450, 3270, h=280, small=True, show=[win(at("S084", "walked"), at("S090", off=0.6))])
label("40 MIN · 3× A WEEK", (D - 450, 3270 - 200), at("S084", "forty"), at("S089", off=-0.3), size=32, sub="FOR A YEAR")
shot("S084", "Left side: a small walker; “40 MIN · 3× A WEEK / FOR A YEAR”.")
label("STRETCHING ONLY", (D + 450, 3270 - 200), at("S085", "stretching"), at("S089", off=-0.3), size=32)
shot("S085", "Right side: “STRETCHING ONLY”.")
pic("hipL", "16_hippocampus", D - 450, 3600, w=300, show=[win(at("S086", "scanned"), at("S090", off=0.6))],
    grow=[{"at": at("S087", "grew"), "dur": 1.2, "to": 1.06}])
pic("hipR", "16_hippocampus", D + 450, 3600, w=300, show=[win(at("S086", "scanned", 0.2), at("S090", off=0.6))],
    grow=[{"at": at("S088", "shrinking"), "dur": 1.4, "to": 0.95}])
light("hipL", "curve", at("S086", "brains"), 1.2, size=26)
light("hipR", "curve", at("S086", "brains", 0.15), 1.2, size=26)
shot("S086", "A hippocampus appears under each group; a light scans along each one.")
label("+{n}%", (D - 450, 3600 + 220), at("S087", "two", -0.3), at("S090", off=-0.3), count=count(0, 2, at("S087", "two"), 0.8))
shot("S087", "The walkers' hippocampus grows a little; “+2%”.")
label("≈ −{n}%", (D + 450, 3600 + 220), at("S088", "shrinking", -0.3), at("S090", off=-0.3), count=count(0, 1.4, at("S088", "shrinking"), 0.8, 1))
shot("S088", "The stretching group's shrinks a little; “≈ −1.4%”.")
label("1–2 YEARS TURNED BACK", (D, 3270 - 200), at("S089", "years"), at("S090", off=-0.3), size=36)
diagram("turnBack", D - 450, 3600, [win(at("S089", "turning", -0.1), at("S090", off=-0.3))], [
    stroke([(150, -150), (40, -205), (-90, -190), (-160, -120)], at("S089", "turning"), 1.0, px=2.4, smooth=True),
    stroke([(-175, -150), (-160, -120), (-128, -133)], at("S089", "turning", 0.9), 0.3, px=2.4),
])
shot("S089", "Top labels fade; “1–2 YEARS TURNED BACK”; a curved arrow draws back over the walkers' hippocampus.")
E3x = D - 1150
cam(at("S090", off=-0.3), 1.8, E3x, 2760, 1.0, "glides left along the page", "S090")
label("{n} ADULTS", (E3x, 2760 - 330), at("S090", "seventy-eight"), at("S091", off=-0.2),
      count=count(0, 78000, at("S090", "seventy-eight"), 1.2), sub="UNITED KINGDOM")
for k in range(5):
    pic(f"pedoE{k}", "08_pedometer", E3x - 400 + k * 200, 2640, h=150, small=True,
        show=[win(at("S090", off=0.7 + 0.15 * k), at("S091", "nine", -0.2))])
shot("S090", "Five small step counters appear in a row; “78,000 ADULTS / UNITED KINGDOM” counts up.")
dem_base = 3050
diagram("dementia", E3x, dem_base, [win(at("S091", "nine", -0.2), at("S093", off=-0.3))], [
    stroke([(-480, 0), (480, 0)], at("S091", "nine", -0.2), 0.8, px=2.0, opacity=0.5),
    bar(-300, 0, 300, at("S091", "nine"), 1.0, width=110),
    bar(300, 0, 150, at("S091", "half", -0.3), 1.0, width=110),
    bar(0, 0, 225, at("S092", "three"), 1.0, width=110),
])
label("FEW STEPS", (E3x - 300, dem_base + 50), at("S091", "nine"), at("S093", off=-0.3), size=26)
label("9,800", (E3x + 300, dem_base + 50), at("S091", "nine"), at("S093", off=-0.3), size=26)
label("−50%", (E3x + 300, dem_base - 200), at("S091", "half"), at("S093", off=-0.3), size=34, sub="DEMENTIA RISK")
shot("S091", "Step counters fade; two bars grow — the 9,800-step group's bar is half as tall; “−50% / DEMENTIA RISK”.")
label("3,800", (E3x, dem_base + 50), at("S092", "three"), at("S093", off=-0.3), size=26)
label("−25%", (E3x, dem_base - 275), at("S092", "quarter"), at("S093", off=-0.3), size=34)
shot("S092", "A middle bar for 3,800 steps grows to three quarters; “−25%”.")
cam(at("S093", off=-0.3), 1.8, D + 50, 2650, 1.0, "glides back right to the brain", "S093")
pic("bulb", "19_light_bulb", D + 450, 2630, h=520, show=[win(at("S093", off=0.3), at("S096", off=-0.2))])
light("bulb", "filament", at("S093", "moment"), 1.2, size=30)
shot("S093", "Bars fade; the brain returns with an old light bulb beside it; a light runs along the filament.")
label("{n}%", (D + 450, 2630 + 330), at("S094", "eighty-one"), at("S096", off=-0.2), count=count(0, 81, at("S094", "eighty-one"), 1.2),
      sub="MORE CREATIVE WHILE WALKING")
light("bulb", "filament", at("S094", "walking"), 1.2, size=30)
shot("S094", "“81% / MORE CREATIVE WHILE WALKING” counts up; the filament glows again.")
cam(at("S095", off=-0.3), 1.4, D + 300, 2650, 0.95, "drifts right", "S095")
diagram("wall", D + 960, 2630, [win(at("S095", "blank", -0.2), at("S096", off=-0.2))], [
    stroke([(-130, -210), (130, -210), (130, 210), (-130, 210), (-130, -210)], at("S095", "blank"), 1.0, px=2.4, opacity=0.7)])
label("BLANK WALL", (D + 960, 2630 + 270), at("S095", "wall"), at("S096", off=-0.2), size=30)
shot("S095", "An empty rectangle draws itself — the blank wall; “BLANK WALL”.")
light("brain", "fold_low", at("S096", "brain"), 1.1)
light("brain", "fold_high", at("S096", "brain", 0.12), 1.1)
cam(at("S096", "feel", -0.6), 2.6, 6000, 2620, 0.9, "travels left to the next part of the page", "S096")
trail("trEF")
shot("S096", "Bulb and wall fade; lights run through the brain; the camera travels left with footprints walking under it.")

# =====================================================================
# Region F — chapter 6 (mood)
# =====================================================================
F = 6000
pic("neuron", "18_neuron", F, 2560, w=900, show=[win(at("S096", "feel", 1.1), at("S101", off=-0.3))])
label("DEPRESSION IS COMMON", (F, 2560 - 365), at("S097", "Depression"), at("S098", off=-0.2))
shot("S097", "A nerve cell fades in; “DEPRESSION IS COMMON”.")
label("A LEADING CAUSE OF DISABILITY", (F, 2560 - 365), at("S098", "leading"), at("S099", off=-0.2), size=38, sub="WORLD HEALTH ORGANIZATION")
light("neuron", "signal", at("S098", "world"), 1.6)
shot("S098", "“A LEADING CAUSE OF DISABILITY / WORLD HEALTH ORGANIZATION”; a light travels along the nerve cell.")
cam(at("S099", off=-0.3), 1.6, F, 2760, 0.9, "eases down", "S099")
diagram("studies", F, 3080, [win(at("S099", "fifteen", -0.1), at("S100", off=-0.2))], [
    stroke([(-420 + k * 60 - 20, 0), (-420 + k * 60 + 20, 0)], at("S099", "fifteen", 0.07 * k), 0.3, width=40, cap="butt", opacity=0.6)
    for k in range(15)])
label("15 STUDIES", (F, 3080 - 80), at("S099", "fifteen"), at("S100", off=-0.2), size=32)
label("{n} PEOPLE", (F, 3080 + 90), at("S099", "two", -0.3), at("S100", off=-0.2), size=32,
      count=count(0, 191130, at("S099", "two"), 1.2))
shot("S099", "Fifteen small blocks appear in a row; “15 STUDIES”; “191,130 PEOPLE” counts up.")
light("neuron", "top_in", at("S100", "depression", -0.6), 1.0, size=28)
light("neuron", "signal", at("S100", "depression", -0.2), 1.4)
shot("S100", "Blocks fade; lights travel through the nerve cell.")
cam(at("S101", off=-0.3), 1.6, F, 2980, 1.0, "settles on a chart", "S101")
dep_base = 3240
diagram("depBars", F, dep_base, [win(at("S101", off=-0.3), at("S104", "zero", -0.2))], [
    stroke([(-470, 0), (470, 0)], at("S101", off=-0.2), 0.8, px=2.0, opacity=0.5),
    bar(-320, 0, 260, at("S101", "twenty-five", -0.4), 1.0, width=120),
    bar(320, 0, 195, at("S101", "twenty-five"), 1.0, width=120),
    bar(0, 0, 213, at("S102", "half"), 1.0, width=120),
])
label("2.5 HOURS A WEEK", (F, 2700), at("S101", off=0.1), at("S102", off=-0.2), sub="BRISK WALKING")
label("NONE", (F - 320, dep_base + 45), at("S101", "twenty-five", -0.4), at("S104", "zero", -0.2), size=26)
label("RECOMMENDED", (F + 320, dep_base + 45), at("S101", "twenty-five"), at("S104", "zero", -0.2), size=26)
label("−{n}%", (F + 320, dep_base - 250), at("S101", "twenty-five"), at("S104", "zero", -0.2), size=34,
      count=count(0, 25, at("S101", "twenty-five"), 0.8))
light("diagram:depBars", [(-470, 0), (470, 0)], at("S101", "brisk"), 1.4, size=26)
shot("S101", "Neuron fades; a baseline draws and a light runs along it; “2.5 HOURS A WEEK / BRISK WALKING”; two bars grow — none vs recommended; “−25%”.")
label("HALF", (F, dep_base + 45), at("S102", "half"), at("S104", "zero", -0.2), size=26)
label("−{n}%", (F, dep_base - 268), at("S102", "eighteen", -0.3), at("S104", "zero", -0.2), size=34, count=count(0, 18, at("S102", "eighteen"), 0.8))
shot("S102", "A middle bar for half the activity; “−18%”.")
jump = [(-320, -260), (0, -213)]
diagram("jump", F, dep_base, [win(at("S103", "jump", -0.1), at("S104", "zero", -0.2))], [stroke(jump, at("S103", "nothing"), 0.9, px=2.6)])
light("diagram:jump", jump, at("S103", "something"), 0.9, size=28)
label("BIGGEST JUMP", (F - 160, dep_base - 360), at("S103", "biggest"), at("S104", "zero", -0.2), size=32)
shot("S103", "A line draws from the “none” bar to the “half” bar; a light runs down it; “BIGGEST JUMP”.")
foot_F = footprints("footF", F - 550, 2980, 6, 220, 190,
                    lambda k: [win(at("S104", "zero") if k == 0 else (at("S105", "lot", 0.35 * (k - 1)) if k < 3 else at("S106", "walk", 0.3 * (k - 3))),
                                   at("S108", "fast", 0.5))])
shot("S104", "“STARTING FROM ZERO”; on “zero” the chart fades and a single footprint appears.")
shot("S105", "“THE FIRST STEPS COUNT MOST”; two more footprints follow.")
block = [(-470, -200), (470, -200), (470, 200), (-470, 200), (-470, -200)]
diagram("block", F, 2980, [win(at("S106", "short", -0.2), at("S108", "fast", 0.5))], [stroke(block, at("S106", "walk"), 1.6, px=2.2, opacity=0.5)])
light("diagram:block", block, at("S106", "around"), 2.4, size=30)
label("STARTING FROM ZERO", (F, 2980 - 300), at("S104", "starting"), at("S105", off=-0.45), size=36)
label("THE FIRST STEPS COUNT MOST", (F, 2980 - 300), at("S105", "need"), at("S106", "begin", -0.45), size=36)
label("A FINE PLACE TO BEGIN", (F, 2980 - 300), at("S106", "begin"), at("S108", off=-0.2), size=36)
shot("S106", "A loop (the block) draws itself around the footprints; a light travels around it; “A FINE PLACE TO BEGIN”.")
cam(at("S107"), 2.0, F, 2960, 0.88, "eases back", "S107")
light("diagram:block", block, at("S107", "practical"), 2.0, size=30)
shot("S107", "The light goes round the block again.")
pic("metroTease", "20_metronome", F + 700, 2980, h=340, show=[win(at("S108", "walk"), at("S108", "fast", 0.5))])
cam(at("S108", "fast", -0.4), 2.6, 3000, 2600, 0.9, "travels left to the next part of the page", "S108")
trail("trFG")
shot("S108", "A metronome appears at the edge of the loop; then the camera travels left with footprints walking under it.")

# =====================================================================
# Region G — chapter 7 (speed)
# =====================================================================
G = 3000
for k in range(7):
    pic(f"crowd{k}", "07_walking_figure", G - 720 + k * 240, 2620, h=260, small=True,
        show=[win(at("S108", "fast", 1.5 + 0.12 * (6 - k)), at("S111", "Slow", -0.3))])
label("{n} WALKERS", (G, 2620 - 260), at("S109", "Britain"), at("S110", off=-0.2), count=count(0, 50225, at("S109", "fifty"), 1.3), sub="BRITAIN")
shot("S109", "A row of seven small walkers has appeared one by one; “50,225 WALKERS / BRITAIN” counts up.")
label("HOW FAST DO YOU WALK?", (G, 2620 + 230), at("S110", "how"), at("S111", off=-0.3))
for k, idx in enumerate([1, 3, 5]):
    light(f"crowd{idx}", "body", at("S110", "usually", 0.2 * k), 1.2, size=22)
shot("S110", "“HOW FAST DO YOU WALK?”; lights rise through three of the walkers.")
cam(at("S111", off=-0.3), 1.4, G, 2760, 0.86, "eases back to hold three walkers and a chart", "S111")
for name, xo, word in [("Slow", -560, "Slow"), ("Average", 0, "average"), ("Brisk", 560, "brisk")]:
    pic(f"pace{name}", "07_walking_figure", G + xo, 2520, h=380, show=[win(at("S111", word), at("S115", off=0.5))])
    label(name.upper(), (G + xo, 2760), at("S111", word, 0.3), at("S115", off=0.2), size=32)
shot("S111", "The crowd fades; three walkers appear one by one with “SLOW”, “AVERAGE”, “BRISK”.")
diagram("years", G, 2830, [win(at("S112", "followed", -0.2), at("S115", off=0.5))], [
    stroke([(-760, 0), (760, 0)], at("S112", "years"), 1.0, px=2.2, opacity=0.5)])
shot("S112", "A long thin line draws under all three — the years of follow-up.")
pace_base = 3200
diagram("paceBars", G, pace_base, [win(at("S113", "slow", -0.2), at("S115", off=0.5))], [
    bar(-560, 0, 260, at("S113", "slow"), 1.0, width=110),
    bar(0, 0, 208, at("S113", "average"), 1.0, width=110),
    bar(560, 0, 198, at("S114", "Brisk"), 1.0, width=110),
])
label("−{n}%", (G, pace_base - 260), at("S113", "twenty", -0.3), at("S115", off=-0.3), size=34, count=count(0, 20, at("S113", "twenty"), 0.8))
shot("S113", "Risk bars grow under the slow and average walkers; the average one is shorter; “−20%”.")
label("−{n}%", (G + 560, pace_base - 250), at("S114", "twenty-four", -0.3), at("S115", off=-0.3), size=34, count=count(0, 24, at("S114", "twenty-four"), 0.8))
shot("S114", "The brisk walker's bar grows, shortest of the three; “−24%”.")
G2 = (G, 3750)
cam(at("S115", off=-0.3), 1.8, G, 3700, 1.0, "moves down the page", "S115")
pic("metro", "20_metronome", G, 3700, h=560, show=[win(at("S115", off=0.4), at("S122", "two"))])
shot("S115", "Walkers and bars fade; a metronome fades in.")
light("metro", "arm_up", at("S116", "steps"), 0.55, size=30, repeat=(4, 1.2))
light("metro", "arm_down", at("S116", "steps", 0.6), 0.55, size=30, repeat=(4, 1.2))
label("{n} STEPS A MINUTE", (G + 620, 3540), at("S116", "hundred", -0.2), at("S118", off=-0.2), size=36,
      count=count(0, 100, at("S116", "hundred"), 1.0))
shot("S116", "A light swings up and down the metronome arm at walking pace; “100 STEPS A MINUTE” counts up.")
label("MODERATE EXERCISE", (G + 620, 3800), at("S117", "moderate"), at("S118", off=-0.2), size=34)
shot("S117", "“MODERATE EXERCISE”.")
pic("footG", "21_footprint", G - 620, 3830, h=240, show=[win(at("S118", "check"), at("S122", off=-0.3))])
shot("S118", "A footprint appears to the left of the metronome.")
watch = _paths.circle(0, 0, 105, n=40)
diagram("watch", G - 620, 3480, [win(at("S119", "fifteen", -0.2), at("S121", off=-0.2))], [
    stroke([(x, y) for x, y in watch], at("S119", "fifteen"), 0.9, px=2.2, opacity=0.6),
    stroke([(x * 0.78, y * 0.78) for x, y in _paths.circle(0, 0, 105, n=40)[:11]], at("S119", "seconds"), 1.0, width=16, opacity=0.6, smooth=True),
])
label("15 SECONDS", (G - 620, 3480 - 160), at("S119", "fifteen"), at("S121", off=-0.2), size=30)
label("× 4", (G - 400, 3480), at("S119", "four"), at("S121", off=-0.2), size=40)
shot("S119", "A round dial draws above the footprint and a quarter of it fills — fifteen seconds; “× 4”.")
label("25 × 4 = 100", (G + 620, 3680), at("S120", "twenty-five"), at("S122", off=-0.3), size=40)
light("metro", "arm_up", at("S120", "hundred"), 0.6, size=30)
shot("S120", "“25 × 4 = 100” beside the metronome; the arm glows.")
light("metro", "arm_down", at("S121", "Pace"), 0.6, size=30)
shot("S121", "The metronome arm glows once more.")
docs = {"L": G - 330, "R": G + 330}
diagram("docs", G, 3700, [win(at("S122", "two", -0.1), at("S124", off=-0.3))], [
    stroke([(x - 160, -220), (x + 160, -220), (x + 160, 220), (x - 160, 220), (x - 160, -220)], at("S122", "two", 0.2 * k), 1.0, px=2.2, opacity=0.6)
    for k, x in enumerate([-330, 330])])
label("2019", (docs["L"], 3700 - 170), at("S122", "studies"), at("S124", off=-0.3), size=28)
label("2020", (docs["R"], 3700 - 170), at("S122", "studies", 0.2), at("S124", off=-0.3), size=28)
shot("S122", "Metronome, dial and footprint fade; two page outlines draw themselves, labelled “2019” and “2020”.")
diagram("docBars", G, 3700 + 150, [win(at("S123", "total", -0.1), at("S124", off=-0.3))], [
    bar(-380, 0, 240, at("S123", "total"), 0.9, width=60), bar(280, 0, 240, at("S123", "total", 0.15), 0.9, width=60),
    bar(-280, 0, 22, at("S123", "little"), 0.6, width=60), bar(380, 0, 22, at("S123", "little", 0.15), 0.6, width=60),
])
label("STEPS", (G, 3700 + 190), at("S123", "total"), at("S124", off=-0.6), size=26)
label("PACE, ONCE STEPS ARE COUNTED", (G, 3700 + 255), at("S123", "little"), at("S124", off=-0.6), size=24)
shot("S123", "In each page a tall bar grows for total steps and a tiny one for pace once steps are counted.")
pic("pedoG", "08_pedometer", G, 3700, h=420, show=[win(at("S124", off=-0.15), at("S125", off=0.7))])
light("pedoG", "rim", at("S124", "mattered"), 1.2)
shot("S124", "Pages fade; the step counter returns; light circles its dial.")
H = 0
cam(at("S125"), 2.4, 0, 2700, 0.85, "travels left to the last part of the page", "S125")
trail("trGH")
shot("S125", "The camera travels left with footprints walking under it; the counter fades behind.")

# =====================================================================
# Region H — chapter 8 (how many steps)
# =====================================================================
chart = (0, 2700)
x_of = lambda steps: -650 + steps * 1300 / 12000
y_of = lambda pct: -260 + (100 - pct) * 6.5
base_y = 200
label("HOW MANY STEPS?", (0, 2700 - 400), at("S126", off=-0.2), at("S127", "Lee", -0.45))
shot("S126", "“HOW MANY STEPS?”; a small step counter fades in to the left.")
pic("pedoH", "08_pedometer", -760, 2620, h=300, small=True, show=[win(at("S126", "steps"), at("S130", "least", -0.1))])
label("I-MIN LEE", (0, 2700 - 400), at("S127", "Lee"), at("S128", off=-0.2), sub="HARVARD")
light("pedoH", "rim", at("S127", "counter"), 1.2, size=26)
shot("S127", "“I-MIN LEE / HARVARD”; light circles the small counter.")
label("{n} WOMEN", (0, 2700 - 400), at("S128", "sixteen", -0.3), at("S130", "least", -0.1), count=count(0, 16741, at("S128", "sixteen"), 1.2))
label("AVERAGE AGE 72", (0, 2700 - 320), at("S128", "seventy-two"), at("S130", "least", -0.1), size=30)
label("2019", (-760, 2620 + 210), at("S128", "2019"), at("S130", "least", -0.1), size=30)
shot("S128", "“2019” under the counter; “16,741 WOMEN” counts up; “AVERAGE AGE 72”.")
diagram("followUp", 0, 2700 - 120, [win(at("S129", "week", -0.1), at("S130", "least", -0.1))], [
    stroke([(-450, 0), (-430, 0)], at("S129", "week"), 0.4, width=36, cap="butt", opacity=0.7),
    stroke([(-450, 80), (450, 80)], at("S129", "four"), 1.4, width=36, cap="butt", opacity=0.5),
])
label("1 WEEK", (-250, 2700 - 120), at("S129", "week"), at("S130", "least", -0.1), size=26)
label("OVER 4 YEARS", (0, 2700 - 120 + 150), at("S129", "four"), at("S130", "least", -0.1), size=26)
shot("S129", "A tiny bar for one week of wearing the counter, then a long bar for over four years of follow-up.")
P1, P2, P3, PE = (x_of(2700), y_of(100)), (x_of(4400), y_of(59)), (x_of(7500), y_of(45)), (x_of(12000), y_of(44))
cam(at("S130", off=-0.3), 1.6, 0, 2730, 0.95, "settles on the chart", "S130")
CURVE_SHOW = [win(at("S130", off=-0.2), at("S133", off=0.2)), win(at("S135", off=-0.3), at("S139", off=0.4))]
diagram("axes", 0, 2700, CURVE_SHOW, [
    stroke([(-650, base_y), (650, base_y)], at("S130", "least"), 1.0, px=2.2, opacity=0.6),
    stroke([(-650, base_y), (-650, -300)], at("S130", "least", 0.2), 1.0, px=2.2, opacity=0.6),
])
diagram("curve", 0, 2700, CURVE_SHOW, [
    stroke([P1, (x_of(3500), y_of(78)), P2], at("S131", "four", -0.2), 1.3, px=3.0, smooth=True),
    stroke([P2, (x_of(5800), y_of(51)), P3], at("S132", "kept"), 1.6, px=3.0, smooth=True),
    stroke([P3, (x_of(9500), y_of(44.4)), PE], at("S132", "leveled"), 1.4, px=3.0, smooth=True),
], dots=[{"at": list(P1), "time": at("S130", "two"), "r": 9}, {"at": list(P2), "time": at("S131", "four", 1.0), "r": 9},
         {"at": list(P3), "time": at("S132", "seven"), "r": 9}])
for a_, b_ in [(at("S130", "least", 0.3), at("S133", off=-0.3)), (at("S135", off=0.9), at("S139", off=-0.5))]:
    label("RISK OF DYING", (-650 + 60, 2700 - 360), a_, b_, size=24, sub="SIMPLIFIED CURVE")
    label("STEPS A DAY", (560, 2700 + base_y + 50), a_, b_, size=24)
label("2,700", (P1[0], 2700 + base_y + 50), at("S130", "two"), at("S133", off=-0.3), size=26)
shot("S130", "Counter fades; the axes of a chart draw — risk of dying against steps a day; a dot marks 2,700 steps.")
label("4,400", (P2[0], 2700 + base_y + 50), at("S131", "four"), at("S133", off=-0.3), size=26)
label("−{n}%", (P2[0] + 120, 2700 + P2[1] - 80), at("S131", "forty-one", -0.3), at("S133", off=-0.3), size=36,
      count=count(0, 41, at("S131", "forty-one"), 0.9))
light("diagram:curve", [P1, (x_of(3500), y_of(78)), P2], at("S131", "dying"), 1.3, size=28)
shot("S131", "The curve draws down to 4,400 steps; a dot; “−41%”; a light runs down the first part of the curve.")
label("7,500", (P3[0], 2700 + base_y + 50), at("S132", "seven"), at("S133", off=-0.3), size=26)
label("LEVELS OFF", (P3[0] + 60, 2700 + P3[1] - 90), at("S132", "leveled"), at("S133", off=-0.3), size=30)
light("diagram:curve", [P2, (x_of(5800), y_of(51)), P3, PE], at("S132", "leveled", 0.3), 1.8, size=30)
shot("S132", "The curve keeps falling, then flattens; a dot at 7,500; “LEVELS OFF”; a light runs along the curve.")
SMx = 1250
cam(at("S133", off=-0.3), 1.6, SMx, 2700, 1.0, "glides right to a second chart", "S133")
label("≈ 4,800 ADULTS", (SMx, 2700 - 360), at("S133", "five"), at("S135", off=-0.3), sub="UNITED STATES")
shot("S133", "The curve steps aside; a baseline for a second chart; “≈ 4,800 ADULTS / UNITED STATES”.")
diagram("smBars", SMx, 2700 + 230, [win(at("S133", off=-0.3), at("S135", off=-0.3))], [
    stroke([(-300, 0), (300, 0)], at("S133", off=-0.2), 0.8, px=2.0, opacity=0.5),
    bar(140, 0, 167, at("S134", "Eight"), 1.0, width=130),
    bar(-140, 0, 340, at("S134", "four"), 1.0, width=130),
])
label("8,000", (SMx + 140, 2700 + 280), at("S134", "Eight"), at("S135", off=-0.3), size=26)
label("4,000", (SMx - 140, 2700 + 280), at("S134", "four"), at("S135", off=-0.3), size=26)
label("≈ HALF THE RISK", (SMx + 140, 2700 + 230 - 230), at("S134", "half"), at("S135", off=-0.3), size=30)
shot("S134", "A bar for 8,000 steps grows, then a bar for 4,000 twice as tall; “≈ HALF THE RISK”.")
cam(at("S135", off=-0.3), 1.6, 0, 2730, 0.95, "glides back to the curve", "S135")
label("2022 · 15 STUDIES", (0, 2700 - 400), at("S135", "2022"), at("S136", off=-0.2))
label("{n} PEOPLE", (0, 2700 - 320), at("S135", "forty-eight", -0.3), at("S136", off=-0.2), size=32, count=count(0, 47471, at("S135", "forty-eight"), 1.2))
light("diagram:curve", [P1, (x_of(3500), y_of(78)), P2, (x_of(5800), y_of(51)), P3, (x_of(9500), y_of(44.4)), PE], at("S135", "pooled"), 2.2, size=30)
shot("S135", "Back at the curve, which returns with its axis labels; “2022 · 15 STUDIES”; a light runs the whole curve; “47,471 PEOPLE” counts up.")
br = lambda s1, s2, y: [(x_of(s1), y - 16), (x_of(s1), y), (x_of(s2), y), (x_of(s2), y - 16)]
diagram("ages", 0, 2700, [win(at("S136", "six", -0.2), at("S139", off=0.4))], [
    stroke(br(6000, 8000, base_y + 95), at("S136", "six"), 0.9, px=2.6),
    stroke(br(8000, 10000, base_y + 165), at("S137", "eight"), 0.9, px=2.6),
])
label("OVER 60: 6,000–8,000", (x_of(7000), 2700 + base_y + 128), at("S136", "six"), at("S139", off=-0.5), size=24)
light("diagram:curve", [P3, (x_of(9500), y_of(44.4)), PE], at("S136", "leveled"), 1.2, size=28)
shot("S136", "A light settles along the flat part of the curve; a bracket draws under the axis from 6,000 to 8,000; “OVER 60: 6,000–8,000”.")
label("UNDER 60: 8,000–10,000", (x_of(9000), 2700 + base_y + 198), at("S137", "eight"), at("S139", off=-0.5), size=24)
light("diagram:ages", br(6000, 8000, base_y + 95)[1:3], at("S137", "younger"), 1.0, size=26)
shot("S137", "A light slides along the first bracket; a second bracket from 8,000 to 10,000; “UNDER 60: 8,000–10,000”.")
light("diagram:curve", [P3, (x_of(9500), y_of(44.4)), PE], at("S138", "add"), 1.4, size=30)
label("MORE STEPS ADD LESS", (x_of(9500), 2700 + P3[1] - 160), at("S138", "point"), at("S139", off=-0.5), size=32)
shot("S138", "A light runs along the flat end of the curve; “MORE STEPS ADD LESS”.")

# =====================================================================
# Ending — back to the step counter
# =====================================================================
cam(at("S139", off=-0.6), 2.8, 0, 0, 1.1, "travels back up the page to the step counter", "S139")
label("1965", (0, pb[3] + 70), at("S139", "1965"), at("S140", off=-0.2))
trail("trHA")
shot("S139", "The camera travels back up the page with footprints walking under it, to where the video began; the step counter returns; “1965”.")
label("10,000", (0, pb[1] - 85), at("S140", "number"), at("S142", off=-0.25), sub="NOT FROM A STUDY")
shot("S140", "“10,000 / NOT FROM A STUDY” above the counter.")
light("pedo", "rim", at("S141", "name"), 1.4, size=34)
shot("S141", "A light circles the dial.")
label("A FAIR GUESS", (0, pb[1] - 60), at("S142", "fair"), at("S143", off=-0.25))
light("pedo", "needle", at("S142", "guess"), 1.0, size=30)
shot("S142", "“A FAIR GUESS”; the needle glows.")
cam(at("S143", off=-0.3), 1.8, 0, 140, 0.92, "eases down", "S143")
xe = lambda s: -650 + s * 1300 / 12000
diagram("axisEnd", 0, 430, [win(at("S143", "younger", -0.2), at("S144", off=-0.3))], [
    stroke([(-650, 0), (650, 0)], at("S143", "younger"), 1.0, px=2.4, opacity=0.6),
    stroke([(xe(8000), -16), (xe(8000), 0), (xe(10000), 0), (xe(10000), -16)], at("S143", "benefit"), 0.8, px=3.0),
    stroke([(xe(10000), -30), (xe(10000), 30)], at("S143", "ten", -0.2), 0.4, px=3.0),
])
label("10,000", (xe(10000), 430 + 70), at("S143", "ten"), at("S144", off=-0.3), size=30)
light("diagram:axisEnd", [(-650, 0), (xe(10000), 0)], at("S143", "run"), 1.4, size=30)
shot("S143", "A steps line draws under the counter with the 8,000–10,000 bracket; a light runs up to the “10,000” mark.")
cam(at("S144", off=-0.2), 2.4, 420, 60, 0.82, "eases back and right, as at the start", "S144")
light("pedo", "rim", at("S144", "number"), 1.2, size=34)
shot("S144", "Line fades; the camera eases back to the opening framing; light circles the dial.")
label("BEGIN", (350, 540), at("S145", "begin"), at("S146", off=-0.25))
shot("S145", "The first footprint of the opening reappears; “BEGIN”.")
label("THE FIRST FEW THOUSAND STEPS", (350, 540), at("S146", "first"), at("S147", off=-0.25), size=36)
shot("S146", "The rest of the footprints follow one by one; “THE FIRST FEW THOUSAND STEPS”.")
light("walkerA", "legs", at("S147", "blood"), 1.0, size=28)
light("walkerA", "thigh", at("S147", "muscles"), 0.9, size=28)
light("walkerA", "torso", at("S147", "sugar"), 0.9, size=28)
light("walkerA", "head", at("S147", "brain"), 0.9, size=28)
shot("S147", "The walker from the opening returns; on each phrase a light moves up through it — legs, thigh, body, head.")
label("A FEW MORE THAN YESTERDAY", (350, 540), at("S148", "few"), None)
cam(at("S148"), 5.2, 320, 50, 0.86, "a last slow push", "S148")
shot("S148", "“A FEW MORE THAN YESTERDAY”; a last slow push in as the video ends on the page it began on.")

# ---- faint background layers: big footprints far behind each region (move slower, blurred) ----
regions = [("A", 0, 0, 0.0, at("S027", "step")), ("B", 3000, 0, at("S027", "step"), at("S041", off=0.5)),
           ("C", 6000, 300, at("S041"), at("S060", off=0.5)), ("D", 9300, 300, at("S060"), at("S078", off=0.5)),
           ("E", 9000, 3000, at("S078"), at("S096", "feel")), ("F", 6000, 2800, at("S096", "feel"), at("S108", "fast")),
           ("G", 3000, 3100, at("S108", "fast"), at("S125")), ("H", 300, 2700, at("S125"), at("S139")),
           ("A2", 0, 0, at("S139"), None)]
for name, rx, ry, a, b in regions:
    for k, (dx, dy, flip) in enumerate([(-620, 260, False), (520, -240, True)]):
        pic(f"bg{name}{k}", "21_footprint", rx + dx, ry + dy, h=520, small=True, rotate=90, flip=flip, opacity=0.07, decor=True,
            depth={"parallax": 0.45, "blur": 2.5, "home": {"x": rx, "y": ry, "zoom": 1.0}},
            show=[win(a, b, ind=1.2, outd=1.2)])

# ---------- write ----------
settings = {
    "title": "What Really Happens When You Walk",
    "width": 1920, "height": 1080, "fps": 60,
    "audio": "full/narration.mp3", "words": "full/words.json", "tailSeconds": 2.0,
    "safeArea": {"top": 0.06, "bottom": 0.10},
    "focus": [960, 518],
    "style": {"background": "#ffffff", "ink": "#202429", "accent": "#5d9cdb", "font": "Inter",
              "fontFile": "fonts/inter-latin-700-normal.woff2", "labelSize": 42, "labelTracking": 0.26},
    "grid": {"spacing": 30, "dot": 1.6, "opacity": 0.16, "far": {"parallax": 0.5, "spacing": 48, "dot": 2.2, "opacity": 0.08, "blur": 1.4}},
    "fade": {"dur": 0.5, "scale": 0.96, "blur": 10},
    "drift": {"px": 9, "zoom": 0.01},
    "chapters": [{"id": "intro", "title": "Opening", "from": 0}] + [
        {"id": c, "title": tt, "from": at(s0)} for c, tt, s0 in [
            ("ch1", "Where did ten thousand come from?", "S010"), ("ch2", "What happens in your legs?", "S028"),
            ("ch3", "Where does the sugar go?", "S042"), ("ch4", "What does walking do to your heart?", "S062"),
            ("ch5", "What does walking do to your brain?", "S080"), ("ch6", "Can a walk change your mood?", "S097"),
            ("ch7", "Does speed matter?", "S109"), ("ch8", "How many steps do you really need?", "S127"),
            ("ending", "Back to the step counter", "S139")]],
    "camera": {"start": S["start"], "moves": sorted(S["moves"], key=lambda m: t(m["at"]))},
    "pictures": sorted(S["pictures"], key=lambda p: (0 if p.get("depth") else 1)),
    "magnifiers": S["magnifiers"], "lights": S["lights"], "labels": S["labels"], "diagrams": S["diagrams"],
}
(ROOT / "public/full/settings.json").write_text(json.dumps(settings, indent=1, ensure_ascii=False))
(ROOT / "public/full/shots.json").write_text(json.dumps(SHOTS, indent=1, ensure_ascii=False))
print(f"{len(settings['pictures'])} pictures, {len(S['labels'])} labels, {len(S['lights'])} lights, "
      f"{len(S['diagrams'])} diagrams, {len(S['magnifiers'])} lenses, {len(S['moves'])} camera moves, "
      f"{len(SHOTS)} sentences with shots")
missing = [w["sid"] for w in WORDS if w["sid"] not in SHOTS]
print("sentences without a shot:", sorted(set(missing)) or "none")
