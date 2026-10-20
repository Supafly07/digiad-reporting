# Picture prompts

Model: **GPT Image 2.5 — Sunburst** (`gpt-image-2-5-sunburst-text-to-image`, the high-precision variant), `quality: high`, `resolution: 2K`.
Background removal: `recraft/remove-background` → transparent PNG cut-outs in this folder.

Every prompt is built the same way: **what it is + angle** → a black-and-white sentence → *“Lots of empty space around it, nothing touching the edges.”* → the style line word for word → *“Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.”*

**Why the extra black-and-white sentence:** the style line (kept word for word) mentions the soft blue the animation will add. On its own, the model painted that blue into the pictures, so every prompt says the picture itself is black, white and grey only. The organs still glowed blue, so their remakes use a firmer version that also rules out glow and light effects.

Prompts below are copied from what kie recorded for each task.

## `01_walking_shoe.png`

Aspect ratio: **3:2** · attempts: 2

**Attempt 1** — ❌ Rejected — soft blue painted on the sole and heel tab (the style line mentions blue). Fixed by adding the black-and-white sentence.

```text
A single lace-up walking shoe, seen from the side, sole flat as if pressing down on the ground. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

**Attempt 2** — ✅ Kept.

```text
A single lace-up walking shoe, seen from the side, sole flat as if pressing down on the ground. Drawn only in black, white and grey, with no blue or any other color. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

## `02_legs_striding.png`

Aspect ratio: **2:3** · attempts: 1

**Prompt** — ✅ Kept.

```text
A single pair of human legs mid-stride, from the hips down, wearing simple fitted shorts and lace-up walking shoes, seen from the side. Drawn only in black, white and grey, with no blue or any other color. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

## `03_thigh_muscle.png`

Aspect ratio: **2:3** · attempts: 2

**Attempt 1** — ❌ Rejected — blue streaks along the muscle.

```text
A single human thigh muscle (the quadriceps) on its own, without skin or bone, anatomical illustration seen from the front. Drawn only in black, white and grey, with no blue or any other color. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

**Attempt 2** — ✅ Kept.

```text
A single human thigh muscle (the quadriceps) on its own, without skin or bone, anatomical illustration seen from the front. Strictly monochrome graphite drawing in black, white and grey only: no blue, no glow, no light effects, no color of any kind. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

## `04_blood_vessel.png`

Aspect ratio: **3:2** · attempts: 1

**Prompt** — ✅ Kept.

```text
A single short segment of a human blood vessel, a horizontal tube cut open lengthwise to show its empty inside, seen from the side. Drawn only in black, white and grey, with no blue or any other color. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

## `05_heart.png`

Aspect ratio: **1:1** · attempts: 2

**Attempt 1** — ❌ Rejected — blue glow in the vessels.

```text
A single anatomical human heart, seen from the front. Drawn only in black, white and grey, with no blue or any other color. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

**Attempt 2** — ✅ Kept.

```text
A single anatomical human heart, seen from the front. Strictly monochrome graphite drawing in black, white and grey only: no blue, no glow, no light effects, no color of any kind. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

## `06_brain.png`

Aspect ratio: **1:1** · attempts: 2

**Attempt 1** — ❌ Rejected — blue glowing sparks.

```text
A single human brain, seen from the left side. Drawn only in black, white and grey, with no blue or any other color. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

**Attempt 2** — ✅ Kept.

```text
A single human brain, seen from the left side. Strictly monochrome graphite drawing in black, white and grey only: no blue, no glow, no light effects, no color of any kind. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

## `07_walking_figure.png`

Aspect ratio: **2:3** · attempts: 1

**Prompt** — ✅ Kept.

```text
A single full human figure walking, seen from the side in profile, wearing simple athletic clothes and lace-up walking shoes. Drawn only in black, white and grey, with no blue or any other color. Lots of empty space around it, nothing touching the edges. Black and white scientific illustration, fine ink lines and soft graphite shading, like an old textbook. One accent color, a soft blue, used only for light and movement, and added by the animation. Each picture is a single object, centered on a plain off-white background, no labels or text, framed vertically for 9:16. Plain white background, no text, no labels, no numbers, no arrows, no shadows, no frame.
```

## Not counted above

- A schema probe with the prompt `test` (6 credits) and one first shoe generation whose download was blocked by the network policy (10 credits, same prompt as shoe attempt 1). Both are included in the credit total.

## After generation

All seven cut-outs were later converted to pure grayscale (transparency kept), because the
accent blue must only come from the animation. The walking figure had a faint blue smear on
the back shin (0.16% of its pixels); the others had no visible colour.
