# Explainer video template (Remotion)

Calm, single-camera explainer shorts: 1080×1920, 60 fps, white page with a faint dot grid,
black-and-white textbook pictures, one soft-blue accent for light and movement.

Everything that changes between videos lives in **one settings file** in `public/`
(e.g. `public/walking-10k.settings.json`). The code in `src/` stays the same.

## Make a new video

1. Put the new pictures (transparent PNG cut-outs) in `public/images/`, the narration in
   `public/<name>.mp3`, and its word timings in `public/<name>.words.json`
   (same shape as `public/narration.words.json`).
2. Copy `public/walking-10k.settings.json` to `public/<name>.settings.json` and edit it:
   - `pictures`: where each picture sits on the page (world units = screen px at zoom 1),
     its drawn-pixel box (`content`) and when it fades in/out (`show`).
   - `camera`: the start framing and the moves. Each move zooms about its subject, so
     subjects stay in frame; overlap moves a little so they flow into each other.
   - `magnifiers`, `lights` (paths traced on a picture, 0–1 coordinates), `labels`.
   - Times are seconds or a spoken word: `{"word": 22, "say": "sugar"}`. The `say` text is
     checked against the transcript, so a wrong index fails instead of drifting.
3. Check the layout (every frame: nothing cut off, top 8% / bottom 18% clear, labels
   clear of the drawings):
   `npx tsx scripts/check-layout.ts public/<name>.settings.json`
4. Review stills (every 0.5 s and every sentence start):
   `node scripts/stills.mjs <name>.settings.json out/stills`
5. Render:
   `npx remotion render Explainer out/video.mp4 --props='{"settingsFile":"<name>.settings.json"}'`

The video is as long as the narration plus `tailSeconds`.

Without internet access to download Remotion's browser, point it at a local one:
`REMOTION_BROWSER_EXECUTABLE=/path/to/chrome-headless-shell`.

## This video

`public/walking-10k.settings.json` — "What Happens to Your Body When You Walk 10,000 Steps
Every Day for 30 Days". Script in `script.md`, picture prompts in `public/images/prompts.md`.
Voice: ElevenLabs "Quentin - Narrator and Educator" (`eleven_multilingual_v2`).
