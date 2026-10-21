# Full video — "What Really Happens When You Walk" (~10 min)

Working checklist. Tick items as they are done so the work can resume from here.

## Decisions (made without asking)
- Topic: the long version of the walking short — where "10,000 steps" came from, what a walk
  does to legs, blood sugar, heart, brain and mood, and how many steps you really need.
- Pictures: Higgsfield is not connected to this session, so GPT Image 2.5 (Sunburst, 2K, high)
  is used through kie.ai — same model, same prompt format. 7 pictures reused from the short.
- Voice: ElevenLabs "Quentin - Narrator and Educator", eleven_multilingual_v2 (same as the short),
  one take per paragraph, checked against a transcript; bad paragraphs regenerated.
- Format: 1920x1080, 60 fps. One global timeline on one page; each chapter is a "Part"
  composition rendering its slice, so parts join seamlessly. Parts rendered muted, joined,
  then the narration is muxed once.

## Step 1 — plan and script
- [x] Research and verify facts -> facts.md (cut anything without a solid source)
- [x] Script ~1,500 words: hook (first 30 s), 8 chapters, ending returns to the opening
- [ ] Shot list for every sentence (something new on screen at least every 5 s)
- [ ] Picture list (~20) -> script.md

## Step 2 — pictures
- [x] Prompts for the 14 new pictures (neuron + light bulb remade once each)
- [x] Generate (GPT Image 2.5), remove backgrounds, grayscale -> public/images/
- [x] Inspect every picture; remake bad ones (max twice each)
- [x] public/images/prompts.md updated

## Step 3 — voice
- [x] Generate each paragraph (same voice/settings)
- [x] Join with natural pauses, even loudness -> public/full/narration.mp3
- [x] Transcribe, align to the script -> word timings; regenerate misread paragraphs

## Step 4 — animation
- [ ] Template: landscape, chapters/parts, diagrams that draw themselves, depth layers,
      ambient camera drift, lights on diagrams
- [ ] Trace light paths on new pictures
- [ ] Settings: page layout + camera + events for every chapter
- [ ] Layout checker passes on every frame

## Step 5 — check and render
- [ ] Stills every second per chapter, reviewed; fixes applied
- [ ] Render parts, join, mux narration -> out/full-video.mp4
- [ ] Verify duration, audio sync, no black frames
- [ ] Commit and push
