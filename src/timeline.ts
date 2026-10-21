// Pure timing / camera / geometry math. No React here, so the layout checker can reuse it.
import type {CameraTarget, Magnifier, Picture, Settings, Time, Vec, Word} from './types';

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

// Starts slowly, speeds up, settles slowly, with no jolt at either end.
export const smoother = (t: number) => {
	const x = clamp01(t);
	return x * x * x * (x * (x * 6 - 15) + 10);
};
export const easeOut = (t: number) => 1 - Math.pow(1 - clamp01(t), 3);
export const easeIn = (t: number) => Math.pow(clamp01(t), 3);
export const easeInOutSine = (t: number) => -(Math.cos(Math.PI * clamp01(t)) - 1) / 2;
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

const clean = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');

// Sentence id -> its words, built once per words array (long videos resolve thousands of cues).
const bySentence = new WeakMap<Word[], Map<string, Word[]>>();
const sentenceWords = (words: Word[], sid: string) => {
	let m = bySentence.get(words);
	if (!m) {
		m = new Map();
		for (const w of words) {
			if (w.sid) {
				if (!m.has(w.sid)) {
					m.set(w.sid, []);
				}
				m.get(w.sid)!.push(w);
			}
		}
		bySentence.set(words, m);
	}
	const ws = m.get(sid);
	if (!ws) {
		throw new Error(`No sentence ${sid} in the narration timing`);
	}
	return ws;
};

export const resolveTime = (t: Time, words: Word[]): number => {
	if (typeof t === 'number') {
		return t;
	}
	if ('s' in t) {
		const ws = sentenceWords(words, t.s);
		let w: Word;
		if (t.say) {
			const hits = ws.filter((x) => clean(x.text) === clean(t.say!));
			const hit = hits[(t.nth ?? 1) - 1];
			if (!hit) {
				throw new Error(`Sentence ${t.s} has no word "${t.say}" (#${t.nth ?? 1})`);
			}
			w = hit;
		} else {
			w = t.edge === 'end' ? ws[ws.length - 1] : ws[0];
		}
		return (t.edge === 'end' ? w.end : w.start) + (t.offset ?? 0);
	}
	const w = words[t.word];
	if (!w) {
		throw new Error(`No word #${t.word} in the narration timing`);
	}
	if (clean(w.text) !== clean(t.say)) {
		throw new Error(`Word #${t.word} is "${w.text}", settings expected "${t.say}"`);
	}
	return (t.edge === 'end' ? w.end : w.start) + (t.offset ?? 0);
};

// One camera for everything. Moves are blended as eased deltas, so an overlapping move
// picks up before the previous one has settled and the motion flows instead of stopping.
// Each move zooms about its subject: pushing in, the new subject slides straight to the
// focus point; pulling back, the old subject slides straight to where it ends up. Either
// way it stays in frame the whole time instead of swinging out while pan and zoom mix.
export const cameraAt = (time: number, s: Settings, words: Word[]): CameraTarget => {
	const [fx, fy] = s.focus;
	let {x, y} = s.camera.start;
	let logZ = Math.log(s.camera.start.zoom);
	let prev = s.camera.start;
	for (const m of s.camera.moves) {
		const e = smoother((time - resolveTime(m.at, words)) / m.dur);
		if (e > 0) {
			const z0 = prev.zoom;
			const z1 = m.to.zoom;
			const z = Math.exp(lerp(Math.log(z0), Math.log(z1), e));
			const anchor = z1 >= z0 ? m.to : prev;
			const sx = lerp(fx + (anchor.x - prev.x) * z0, fx + (anchor.x - m.to.x) * z1, e);
			const sy = lerp(fy + (anchor.y - prev.y) * z0, fy + (anchor.y - m.to.y) * z1, e);
			x += anchor.x - (sx - fx) / z - prev.x;
			y += anchor.y - (sy - fy) / z - prev.y;
			logZ += Math.log(z) - Math.log(z0);
		}
		prev = m.to;
	}
	// A slow, uneven wander so the camera never holds perfectly still.
	if (s.drift) {
		const w = (a: number, b: number, c: number) =>
			0.55 * Math.sin((time / a) * Math.PI * 2 + 0.7) + 0.3 * Math.sin((time / b) * Math.PI * 2 + 2.1) +
			0.15 * Math.sin((time / c) * Math.PI * 2 + 4.0);
		const z = Math.exp(logZ);
		x += (s.drift.px * w(13.7, 7.3, 4.1)) / z;
		y += (s.drift.px * 0.7 * w(11.3, 6.1, 3.7)) / z;
		logZ += s.drift.zoom * w(17.9, 9.7, 5.3);
	}
	return {x, y, zoom: Math.exp(logZ)};
};

// Where a background layer sits on screen: relative to its home camera it moves `parallax`
// times as far and zooms `parallax` times as much (in log terms) as the page.
export const depthCamera = (cam: CameraTarget, depth: {parallax: number; home: CameraTarget}): CameraTarget => ({
	x: depth.home.x + (cam.x - depth.home.x) * depth.parallax,
	y: depth.home.y + (cam.y - depth.home.y) * depth.parallax,
	zoom: depth.home.zoom * Math.pow(cam.zoom / depth.home.zoom, depth.parallax),
});

export type ChapterSpan = {id: string; title: string; start: number; end: number};

// Chapters start halfway through the pause before their first word, so parts join in silence.
export const chapterSpans = (s: Settings, words: Word[], totalSeconds: number): ChapterSpan[] => {
	const chapters = s.chapters ?? [{id: 'all', title: s.title, from: 0}];
	const starts = chapters.map((c, i) => {
		if (i === 0) {
			return 0;
		}
		const t = resolveTime(c.from, words);
		const before = words.filter((w) => w.end <= t + 1e-6).pop();
		return before ? (before.end + t) / 2 : t;
	});
	return chapters.map((c, i) => ({id: c.id, title: c.title, start: starts[i], end: i + 1 < chapters.length ? starts[i + 1] : totalSeconds}));
};

export const worldToScreen = (p: Vec, cam: CameraTarget, focus: Vec): Vec => [
	focus[0] + (p[0] - cam.x) * cam.zoom,
	focus[1] + (p[1] - cam.y) * cam.zoom,
];

export type Appearance = {opacity: number; scale: number; blur: number};

// Fade in / out with a little scale and blur; never pops.
export const appearance = (
	windows: Picture['show'],
	time: number,
	s: Settings,
	words: Word[],
): Appearance => {
	let best: Appearance = {opacity: 0, scale: 1, blur: s.fade.blur};
	for (const w of windows) {
		const tin = w.in === null ? -Infinity : resolveTime(w.in, words);
		const tout = w.out === null ? Infinity : resolveTime(w.out, words);
		const pin = w.in === null ? 1 : easeOut((time - tin) / (w.inDur ?? s.fade.dur));
		const pout = w.out === null ? 0 : smoother((time - tout) / (w.outDur ?? s.fade.dur));
		const opacity = Math.min(pin, 1 - pout);
		if (opacity > best.opacity) {
			const scaleIn = lerp(s.fade.scale, 1, pin);
			const scaleOut = lerp(1, w.outScale ?? s.fade.scale, pout);
			best = {opacity, scale: scaleIn * scaleOut, blur: s.fade.blur * Math.max(1 - pin, pout)};
		}
	}
	return best;
};

export const pulseScale = (p: Picture, time: number, words: Word[]) => {
	if (!p.pulse) {
		return 1;
	}
	const from = resolveTime(p.pulse.from, words);
	const to = resolveTime(p.pulse.to, words);
	if (time < from || time > to) {
		return 1;
	}
	// Ramp the beat in and out so it never starts or stops abruptly.
	const env = Math.min(smoother((time - from) / 0.8), 1 - smoother((time - (to - 0.8)) / 0.8));
	const phase = ((time - from) * p.pulse.bpm) / 60;
	const beat = Math.pow(Math.max(0, Math.sin(phase * Math.PI * 2)), 6);
	return 1 + p.pulse.amount * beat * env;
};

// Smooth curve through traced points (Catmull-Rom), sampled for constant-speed lookup.
export const buildPath = (pts: Vec[]) => {
	const out: Vec[] = [];
	const P = (i: number) => pts[Math.max(0, Math.min(pts.length - 1, i))];
	for (let i = 0; i < pts.length - 1; i++) {
		const [p0, p1, p2, p3] = [P(i - 1), P(i), P(i + 1), P(i + 2)];
		for (let k = 0; k < 24; k++) {
			const t = k / 24;
			const t2 = t * t;
			const t3 = t2 * t;
			const f = (a: number, b: number, c: number, d: number) =>
				0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
			out.push([f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])]);
		}
	}
	out.push(pts[pts.length - 1]);
	const cum = [0];
	for (let i = 1; i < out.length; i++) {
		cum.push(cum[i - 1] + Math.hypot(out[i][0] - out[i - 1][0], out[i][1] - out[i - 1][1]));
	}
	const total = cum[cum.length - 1];
	const at = (u: number): Vec => {
		const d = clamp01(u) * total;
		let i = 1;
		while (i < cum.length - 1 && cum[i] < d) {
			i++;
		}
		const seg = cum[i] - cum[i - 1] || 1;
		const k = (d - cum[i - 1]) / seg;
		return [lerp(out[i - 1][0], out[i][0], k), lerp(out[i - 1][1], out[i][1], k)];
	};
	return {at};
};

export type MagnifierState = {
	ring: number; // 0..1 how much of the source ring is drawn
	links: number; // 0..1 how much of the connecting lines are drawn
	linksOpacity: number;
	grow: number; // 0..1
	center: Vec;
	radius: number;
	lensOpacity: number;
	blur: number;
};

export const magnifierAt = (m: Magnifier, time: number, s: Settings, words: Word[]): MagnifierState => {
	const ringAt = resolveTime(m.ringAt, words);
	const growAt = resolveTime(m.growAt, words);
	const linksOut = resolveTime(m.linksOut, words);
	const out = resolveTime(m.out, words);
	const ring = smoother((time - ringAt) / 0.5);
	const grow = smoother((time - growAt) / m.growDur);
	const links = smoother((time - growAt + 0.15) / (m.growDur * 0.8));
	const fadeLinks = 1 - smoother((time - linksOut) / s.fade.dur);
	const fadeLens = 1 - smoother((time - out) / s.fade.dur);
	const center: Vec = [lerp(m.source[0], m.center[0], grow), lerp(m.source[1], m.center[1], grow)];
	return {
		ring,
		links,
		linksOpacity: Math.min(ring, fadeLinks),
		grow,
		center,
		radius: lerp(m.sourceRadius, m.radius, grow),
		lensOpacity: Math.min(easeOut(grow * 1.6), fadeLens),
		blur: s.fade.blur * Math.max(1 - grow, 1 - fadeLens),
	};
};

// The two outer tangent lines between a small circle and a big one.
export const outerTangents = (c1: Vec, r1: number, c2: Vec, r2: number): [Vec, Vec][] => {
	const dx = c2[0] - c1[0];
	const dy = c2[1] - c1[1];
	const d = Math.hypot(dx, dy);
	if (d <= Math.abs(r2 - r1) + 1e-3) {
		return [];
	}
	const base = Math.atan2(dy, dx);
	const off = Math.acos((r1 - r2) / d);
	return [base + off, base - off].map((a) => {
		const n: Vec = [Math.cos(a), Math.sin(a)];
		return [
			[c1[0] + n[0] * r1, c1[1] + n[1] * r1],
			[c2[0] + n[0] * r2, c2[1] + n[1] * r2],
		];
	});
};

// Approximate on-screen half width of a label (bold caps with wide tracking).
export const labelHalfWidth = (text: string, size: number, s: Settings) =>
	(text.length * size * (0.66 + s.style.labelTracking)) / 2;

export const durationInSeconds =(audioSeconds: number, s: Settings) => audioSeconds + s.tailSeconds;
