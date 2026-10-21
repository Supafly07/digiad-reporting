"""Give every script word its exact time, using the transcript of the joined narration.

Script tokens like "1965" are spoken as several words ("nineteen sixty-five"), so they are
expanded before aligning and then take the span of all their spoken words.
Writes public/full/words.json and reports any word the narrator did not say as written.
"""
import json, re, difflib
from pathlib import Path

root = Path(__file__).resolve().parents[2]
script = json.loads((root / "public/full/script.json").read_text())
heard = json.loads((root / "voice/transcript_words.json").read_text())["words"]
heard = [w for w in heard if w.get("type", "word") == "word"]

SPOKEN = {"1965": "nineteen sixty-five", "1960s": "nineteen sixties", "150": "one hundred fifty",
          "2": "two", "2022": "twenty twenty-two", "2019": "twenty nineteen"}
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

tokens = []  # script words with where they belong
for ch in script:
    for par in ch["paragraphs"]:
        for si, sent in enumerate(par["sentences"]):
            for wi, word in enumerate(sent["text"].split()):
                core = re.sub(r"[^\w-]", "", word)
                spoken = SPOKEN.get(core, word).replace("-", " ").split()
                tokens.append({"text": word, "sid": sent["id"], "wi": wi, "paragraph": par["id"], "chapter": ch["id"],
                               "spoken": [norm(s) for s in spoken]})

flat, owner = [], []
for ti, t in enumerate(tokens):
    for s in t["spoken"]:
        flat.append(s)
        owner.append(ti)
heard_flat, heard_idx = [], []
for hi, h in enumerate(heard):
    for part in h["text"].replace("-", " ").split():
        heard_flat.append(norm(part))
        heard_idx.append(hi)

spans = {}
sm = difflib.SequenceMatcher(a=flat, b=heard_flat, autojunk=False)
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        ti, hw = owner[a + k], heard[heard_idx[b + k]]
        s, e = spans.get(ti, (hw["start"], hw["end"]))
        spans[ti] = (min(s, hw["start"]), max(e, hw["end"]))

missing = [i for i in range(len(tokens)) if i not in spans]
# Words the transcriber heard differently get times between their neighbours.
for i in missing:
    prev = max([j for j in spans if j < i], default=None)
    nxt = min([j for j in spans if j > i], default=None)
    s = spans[prev][1] if prev is not None else 0
    e = spans[nxt][0] if nxt is not None else s + 0.3
    spans[i] = (s, e)

words, sent_index, last_sid = [], -1, None
for i, t in enumerate(tokens):
    if t["sid"] != last_sid:
        sent_index += 1
        last_sid = t["sid"]
    s, e = spans[i]
    words.append({"text": t["text"], "start": round(s, 3), "end": round(e, 3), "i": i, "sentence": sent_index,
                  "sid": t["sid"], "wi": t["wi"], "paragraph": t["paragraph"], "chapter": t["chapter"]})

layout = json.loads((root / "public/full/voice_layout.json").read_text())
(root / "public/full/words.json").write_text(json.dumps(
    {"audio": "full/narration.mp3", "duration": layout["duration"], "words": words}, indent=0))
print(f"{len(words)} script words, {len(words) - len(missing)} matched exactly, {len(missing)} placed between neighbours")
for i in missing:
    print("  not heard as written:", tokens[i]["sid"], repr(tokens[i]["text"]))
