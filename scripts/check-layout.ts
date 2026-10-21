// Frame-by-frame layout check for a settings file, using the same math as the renderer.
// Usage: npx tsx scripts/check-layout.ts [public/<name>.settings.json] [frame step]
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {PNG} from 'pngjs';
import type {Picture, Settings, Time, Vec, WordsFile} from '../src/types';
import {
	appearance,
	buildPath,
	cameraAt,
	durationInSeconds,
	growScale,
	labelHalfWidth,
	lerp,
	magnifierAt,
	pictureMapper,
	pulseScale,
	resolveTime,
	smoother,
	worldToScreen,
} from '../src/timeline';

const file = process.argv[2] ?? 'public/walking-10k.settings.json';
const step = Number(process.argv[3] ?? 1);
const s: Settings = JSON.parse(readFileSync(file, 'utf8'));
// Paths in a settings file are relative to public/ (the settings may sit in a subfolder).
const pub = file.slice(0, file.indexOf('public/') + 'public/'.length) || path.dirname(file);
const words = (JSON.parse(readFileSync(path.join(pub, s.words), 'utf8')) as WordsFile).words;
const audioSeconds = Number(
	execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path.join(pub, s.audio)]).toString(),
);
const frames = Math.ceil(durationInSeconds(audioSeconds, s) * s.fps);
const W = s.width;
const H = s.height;
const safeTop = s.safeArea.top * H;
const safeBottom = (1 - s.safeArea.bottom) * H;
const safeName = `top ${Math.round(s.safeArea.top * 100)}% / bottom ${Math.round(s.safeArea.bottom * 100)}%`;
const EDGE = 6; // px a picture must stay clear of the frame edge
const diagrams = s.diagrams ?? [];

type Box = [number, number, number, number];

// Coarse map of where each picture actually has ink, so labels are tested against the
// drawing itself rather than its bounding box.
const G = 96;
const masks = new Map<string, Uint8Array>();
for (const p of s.pictures) {
	if (masks.has(p.src)) {
		continue;
	}
	const png = PNG.sync.read(readFileSync(path.join(pub, p.src)));
	const m = new Uint8Array(G * G);
	for (let y = 0; y < png.height; y += 2) {
		for (let x = 0; x < png.width; x += 2) {
			if (png.data[(y * png.width + x) * 4 + 3] > 40) {
				m[Math.floor((y / png.height) * G) * G + Math.floor((x / png.width) * G)] = 1;
			}
		}
	}
	masks.set(p.src, m);
}
const inkAt = (p: Picture, nx: number, ny: number) =>
	nx >= 0 && ny >= 0 && nx < 1 && ny < 1 && masks.get(p.src)![Math.floor(ny * G) * G + Math.floor(nx * G)] === 1;

// World point back to normalized picture coordinates (inverse of pictureMapper).
const pictureUnmapper = (p: Picture, scale: number) => {
	const cx = p.x + p.w / 2;
	const cy = p.y + p.h / 2;
	const r = (-(p.rotate ?? 0) * Math.PI) / 180;
	return ([wx, wy]: Vec): Vec => {
		const dx = wx - cx;
		const dy = wy - cy;
		const ux = (dx * Math.cos(r) - dy * Math.sin(r)) / scale / (p.flip ? -1 : 1);
		const uy = (dx * Math.sin(r) + dy * Math.cos(r)) / scale;
		return [(cx + ux - p.x) / p.w, (cy + uy - p.y) / p.h];
	};
};

// Distance from q to a stroke segment; a butt-capped stroke stops flat at its ends.
const segDist = (q: Vec, a: Vec, b: Vec, butt = false) => {
	const dx = b[0] - a[0];
	const dy = b[1] - a[1];
	const L = dx * dx + dy * dy || 1;
	const raw = ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L;
	const k = Math.max(0, Math.min(1, raw));
	if (butt && raw !== k) {
		return Infinity;
	}
	return Math.hypot(q[0] - a[0] - k * dx, q[1] - a[1] - k * dy);
};

// Drawn part of each stroke, in world coordinates (smooth strokes resampled like the renderer).
const strokePoints = diagrams.map((d) =>
	d.strokes.map((st) => {
		let pts = st.points;
		if (st.smooth) {
			const bp = buildPath(st.points);
			pts = Array.from({length: 60}, (_, k) => bp.at(k / 59));
		}
		return pts.map(([x, y]) => [d.x + x, d.y + y] as Vec);
	}),
);
const partial = (pts: Vec[], e: number): Vec[] => {
	if (e >= 1) {
		return pts;
	}
	const lens = pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
	let left = lens.reduce((a, b) => a + b, 0) * e;
	const out: Vec[] = [pts[0]];
	for (let i = 0; i < lens.length && left > 0; i++) {
		const k = Math.min(1, left / (lens[i] || 1));
		out.push([lerp(pts[i][0], pts[i + 1][0], k), lerp(pts[i][1], pts[i + 1][1], k)]);
		left -= lens[i];
	}
	return out;
};

const issues = new Map<string, number[]>();
const flag = (key: string, f: number) => {
	if (!issues.has(key)) {
		issues.set(key, []);
	}
	issues.get(key)!.push(f);
};

for (let f = 0; f < frames; f += step) {
	const t = f / s.fps;
	const cam = cameraAt(t, s, words);
	// While the camera is moving, things may slide out past the edge; resting framings must keep them in.
	const next = cameraAt(t + 1 / s.fps, s, words);
	const travelling = Math.hypot(next.x - cam.x, next.y - cam.y) * cam.zoom * s.fps > 300;
	const toWorld = (sx: number, sy: number): Vec => [cam.x + (sx - s.focus[0]) / cam.zoom, cam.y + (sy - s.focus[1]) / cam.zoom];
	// Each visible thing gets a test: does it have ink at this screen point?
	const visible: [string, (sx: number, sy: number) => boolean][] = [];
	// Is anything (other than decoration) clearly on screen? Empty frames are not allowed.
	let present = false;
	const seen = (box: Box, opacity: number) => {
		const iw = Math.max(0, Math.min(W, box[2]) - Math.max(0, box[0]));
		const ih = Math.max(0, Math.min(H, box[3]) - Math.max(0, box[1]));
		const area = (box[2] - box[0]) * (box[3] - box[1]);
		if (opacity > 0.5 && iw * ih >= 0.5 * area && iw * ih > 80 * 80) {
			present = true;
		}
	};
	for (const p of s.pictures) {
		const a = appearance(p.show, t, s, words);
		if (a.opacity <= 0.02 || p.depth) {
			continue;
		}
		const sc = a.scale * pulseScale(p, t, words) * growScale(p, t, words);
		const map = pictureMapper(p, sc);
		const unmap = pictureUnmapper(p, sc);
		const [c0, c1, c2, c3] = p.content;
		const corners = ([[c0, c1], [c2, c1], [c2, c3], [c0, c3]] as Vec[]).map((n) => worldToScreen(map(n), cam, s.focus));
		const xs = corners.map((c) => c[0]);
		const ys = corners.map((c) => c[1]);
		const [x0, y0, x1, y1] = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
		if (p.decor) {
			seen([x0, y0, x1, y1], a.opacity * Math.min(1, (p.opacity ?? 1) * 2));
			continue;
		}
		visible.push([
			p.id,
			(sx, sy) => {
				const [nx, ny] = unmap(toWorld(sx, sy));
				return inkAt(p, nx, ny);
			},
		]);
		seen([x0, y0, x1, y1], a.opacity * Math.min(1, (p.opacity ?? 1) * 2));
		if (!travelling && (x0 < EDGE || y0 < EDGE || x1 > W - EDGE || y1 > H - EDGE)) {
			flag(`picture "${p.id}" cut off at the frame edge`, f);
		}
		if (!travelling && a.opacity > 0.6 && (y0 < safeTop || y1 > safeBottom)) {
			flag(`picture "${p.id}" reaches into the ${safeName}`, f);
		}
	}
	diagrams.forEach((d, di) => {
		const a = appearance(d.show, t, s, words);
		if (a.opacity <= 0.02) {
			return;
		}
		const drawn: {pts: Vec[]; half: number; butt?: boolean}[] = [];
		d.strokes.forEach((st, si) => {
			const e = smoother((t - resolveTime(st.at, words)) / st.dur);
			if (e > 0) {
				const half = st.width ? (st.width * cam.zoom) / 2 : (st.px ?? 2.2) / 2;
				drawn.push({pts: partial(strokePoints[di][si], e).map((p) => worldToScreen(p, cam, s.focus)), half, butt: st.cap === 'butt'});
			}
		});
		for (const dot of d.dots ?? []) {
			if (t >= resolveTime(dot.time, words)) {
				const c = worldToScreen([d.x + dot.at[0], d.y + dot.at[1]], cam, s.focus);
				drawn.push({pts: [c, c], half: dot.r});
			}
		}
		if (!drawn.length) {
			return;
		}
		let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
		for (const {pts, half} of drawn) {
			for (const [x, y] of pts) {
				[x0, y0, x1, y1] = [Math.min(x0, x - half), Math.min(y0, y - half), Math.max(x1, x + half), Math.max(y1, y + half)];
			}
		}
		seen([x0, y0, Math.max(x1, x0 + 80), Math.max(y1, y0 + 80)], a.opacity);
		if (!travelling && (x0 < EDGE || y0 < EDGE || x1 > W - EDGE || y1 > H - EDGE)) {
			flag(`diagram "${d.id}" cut off at the frame edge`, f);
		}
		if (!travelling && a.opacity > 0.6 && (y0 < safeTop || y1 > safeBottom)) {
			flag(`diagram "${d.id}" reaches into the ${safeName}`, f);
		}
		visible.push([
			`diagram ${d.id}`,
			(sx, sy) =>
				drawn.some(({pts, half, butt}) => pts.some((p, i) => i > 0 && segDist([sx, sy], pts[i - 1], p, butt) <= half + 3)),
		]);
	});
	for (const m of s.magnifiers) {
		const st = magnifierAt(m, t, s, words);
		if (st.lensOpacity <= 0.02 || st.grow <= 0) {
			continue;
		}
		const [cx, cy] = worldToScreen(st.center, cam, s.focus);
		const r = st.radius * cam.zoom;
		const box: Box = [cx - r, cy - r, cx + r, cy + r];
		visible.push([`lens ${m.id}`, (sx, sy) => Math.hypot(sx - cx, sy - cy) <= r]);
		seen(box, st.lensOpacity);
		if (box[0] < EDGE || box[1] < EDGE || box[2] > W - EDGE || box[3] > H - EDGE) {
			flag(`lens "${m.id}" cut off at the frame edge`, f);
		}
		if (st.lensOpacity > 0.6 && (box[1] < safeTop || box[3] > safeBottom)) {
			flag(`lens "${m.id}" reaches into the ${safeName}`, f);
		}
	}
	const labelBoxes: [string, Box][] = [];
	const endLabels = () => {
		if (!present) {
			flag('nothing clearly on screen (empty frame)', f);
		}
	};
	for (const l of s.labels) {
		const a = appearance([{in: l.in, out: l.out}], t, s, words);
		if (a.opacity <= 0.3) {
			continue;
		}
		const size = l.size ?? s.style.labelSize;
		const [sx0, sy0] = worldToScreen(l.anchor, cam, s.focus);
		const sy = Math.min(safeBottom - size, Math.max(safeTop + size, sy0 + (l.offset?.[1] ?? 0)));
		const text = l.text.replace('{n}', (l.count?.to ?? 0).toLocaleString('en-US', {minimumFractionDigits: l.count?.decimals ?? 0, useGrouping: l.count?.grouping ?? true}));
		const half = Math.max(labelHalfWidth(text, size, s), l.sub ? labelHalfWidth(l.sub, size * 0.5, s) : 0);
		const sx = Math.min(W - 40 - half, Math.max(40 + half, sx0 + (l.offset?.[0] ?? 0)));
		const box: Box = [sx - half, sy - size / 2, sx + half, sy + size / 2 + (l.sub ? size * 0.85 : 0)];
		// Labels are clamped to the screen; one held far from its anchor has lost what it points at.
		const pinned = Math.hypot(sx - sx0 - (l.offset?.[0] ?? 0), sy - sy0 - (l.offset?.[1] ?? 0));
		if (pinned > 60) {
			flag(`label "${l.text}" held at the screen edge, far from its anchor`, f);
		} else if (a.opacity > 0.5) {
			present = true;
		}
		if (box[0] < 40 || box[2] > W - 40) {
			flag(`label "${l.text}" runs off the side`, f);
		}
		if (box[1] < safeTop || box[3] > safeBottom) {
			flag(`label "${l.text}" in the ${safeName}`, f);
		}
		for (const [id, hit] of visible) {
			let touches = false;
			for (let i = 0; i <= 16 && !touches; i++) {
				for (let j = 0; j <= 4 && !touches; j++) {
					const pad = id.startsWith('diagram ') ? 2 : 12;
					touches = hit(lerp(box[0], box[2], i / 16), lerp(box[1] - pad, box[3] + pad, j / 4));
				}
			}
			if (touches) {
				flag(`label "${l.text}" overlaps "${id}"`, f);
			}
		}
		for (const [other, ob] of labelBoxes) {
			if (box[0] < ob[2] + 16 && ob[0] < box[2] + 16 && box[1] < ob[3] + 10 && ob[1] < box[3] + 10) {
				flag(`label "${l.text}" overlaps label "${other}"`, f);
			}
		}
		labelBoxes.push([l.text, box]);
	}
	endLabels();
}

// Every cue must resolve (resolveTime throws on a missing sentence or word).
const at = (x: Time) => resolveTime(x, words);
const pics = new Set(s.pictures.map((p) => p.id));
for (const l of s.lights) {
	at(l.at);
	const on = l.on.replace(/^(lens|diagram):/, '');
	if (!pics.has(on) && !s.magnifiers.some((m) => m.id === on) && !diagrams.some((d) => d.id === on)) {
		flag(`light on unknown "${l.on}"`, 0);
	}
}

// Something new should arrive on screen at least every 5 seconds while the narrator speaks.
const events: number[] = [];
for (const p of s.pictures) {
	if (!p.decor) {
		p.show.forEach((w) => w.in !== null && events.push(at(w.in)));
		(p.grow ?? []).forEach((g) => events.push(at(g.at)));
		if (p.pulse) events.push(at(p.pulse.from));
	}
}
for (const l of s.labels) {
	events.push(at(l.in));
	if (l.count) events.push(at(l.count.at));
}
for (const l of s.lights) {
	const t0 = at(l.at);
	for (let i = 0; i < (l.repeat?.count ?? 1); i++) events.push(t0 + i * (l.repeat?.every ?? 0));
}
for (const d of diagrams) {
	d.strokes.forEach((st) => events.push(at(st.at)));
	(d.dots ?? []).forEach((dot) => events.push(at(dot.time)));
}
for (const m of s.magnifiers) events.push(at(m.ringAt), at(m.growAt));
for (const m of s.camera.moves) events.push(at(m.at));
events.sort((a, b) => a - b);
const speechEnd = words[words.length - 1].end;
let last = 0;
const gaps: string[] = [];
for (const e of [...events.filter((e) => e <= speechEnd), speechEnd]) {
	if (e - last > 5) {
		gaps.push(`${last.toFixed(1)}-${e.toFixed(1)}s (${(e - last).toFixed(1)}s)`);
	}
	last = Math.max(last, e);
}

const fmt = (all: number[]) => {
	const fs = [...new Set(all)];
	const out: string[] = [];
	let a = fs[0];
	let b = fs[0];
	for (const f of [...fs.slice(1), Infinity]) {
		if (f === b + step) {
			b = f;
			continue;
		}
		out.push(a === b ? `${(a / s.fps).toFixed(2)}s` : `${(a / s.fps).toFixed(2)}-${(b / s.fps).toFixed(2)}s`);
		a = b = f;
	}
	return out.join(', ');
};
console.log(`${file}: ${frames} frames (${(frames / s.fps).toFixed(2)}s, audio ${audioSeconds.toFixed(2)}s), checked every ${step} frame(s)`);
console.log(`${events.length} on-screen events; longest wait ${Math.max(...events.slice(1).map((e, i) => e - events[i])).toFixed(1)}s`);
if (issues.size === 0 && gaps.length === 0) {
	console.log('OK: nothing cut off, safe areas clear, labels clear of pictures, nothing static for over 5s.');
} else {
	for (const [k, fs] of issues) console.log(`- ${k}: ${fmt(fs)}`);
	for (const g of gaps) console.log(`- nothing new for ${g}`);
	process.exitCode = 1;
}
