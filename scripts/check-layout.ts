// Frame-by-frame layout check for a settings file, using the same math as the renderer.
// Usage: npx tsx scripts/check-layout.ts [public/<name>.settings.json]
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {PNG} from 'pngjs';
import type {Picture, Settings, Vec, WordsFile} from '../src/types';
import {
	appearance,
	cameraAt,
	durationInSeconds,
	labelHalfWidth,
	lerp,
	magnifierAt,
	pulseScale,
	resolveTime,
	worldToScreen,
} from '../src/timeline';

const file = process.argv[2] ?? 'public/walking-10k.settings.json';
const s: Settings = JSON.parse(readFileSync(file, 'utf8'));
const pub = path.dirname(file);
const words = (JSON.parse(readFileSync(path.join(pub, s.words), 'utf8')) as WordsFile).words;
const audioSeconds = Number(
	execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path.join(pub, s.audio)]).toString(),
);
const frames = Math.ceil(durationInSeconds(audioSeconds, s) * s.fps);
const W = s.width;
const H = s.height;
const safeTop = s.safeArea.top * H;
const safeBottom = (1 - s.safeArea.bottom) * H;
const EDGE = 6; // px a picture must stay clear of the frame edge

type Box = [number, number, number, number];

// Coarse map of where each picture actually has ink, so labels are tested against the
// drawing itself rather than its bounding box.
const G = 96;
const masks = new Map<string, Uint8Array>();
for (const p of s.pictures) {
	const png = PNG.sync.read(readFileSync(path.join(pub, p.src)));
	const m = new Uint8Array(G * G);
	for (let y = 0; y < png.height; y += 2) {
		for (let x = 0; x < png.width; x += 2) {
			if (png.data[(y * png.width + x) * 4 + 3] > 40) {
				m[Math.floor((y / png.height) * G) * G + Math.floor((x / png.width) * G)] = 1;
			}
		}
	}
	masks.set(p.id, m);
}
const inkAt = (p: Picture, nx: number, ny: number) =>
	nx >= 0 && ny >= 0 && nx < 1 && ny < 1 && masks.get(p.id)![Math.floor(ny * G) * G + Math.floor(nx * G)] === 1;

const issues = new Map<string, number[]>();
const flag = (key: string, f: number) => {
	if (!issues.has(key)) {
		issues.set(key, []);
	}
	issues.get(key)!.push(f);
};

const labelBox = (text: string, size: number, cx: number, cy: number): Box => {
	const half = labelHalfWidth(text, size, s);
	return [cx - half, cy - size / 2, cx + half, cy + size / 2];
};

for (let f = 0; f < frames; f++) {
	const t = f / s.fps;
	const cam = cameraAt(t, s, words);
	// Each visible thing gets a test: does it have ink at this screen point?
	const visible: [string, (sx: number, sy: number) => boolean][] = [];
	for (const p of s.pictures) {
		const a = appearance(p.show, t, s, words);
		if (a.opacity <= 0.02) {
			continue;
		}
		const sc = a.scale * pulseScale(p, t, words);
		const cx = p.x + p.w / 2;
		const cy = p.y + p.h / 2;
		const corner = (nx: number, ny: number): Vec =>
			worldToScreen([cx + (p.x + nx * p.w - cx) * sc, cy + (p.y + ny * p.h - cy) * sc], cam, s.focus);
		const [x0, y0] = corner(p.content[0], p.content[1]);
		const [x1, y1] = corner(p.content[2], p.content[3]);
		visible.push([
			p.id,
			(sx, sy) => {
				const wx = cam.x + (sx - s.focus[0]) / cam.zoom;
				const wy = cam.y + (sy - s.focus[1]) / cam.zoom;
				return inkAt(p, (cx + (wx - cx) / sc - p.x) / p.w, (cy + (wy - cy) / sc - p.y) / p.h);
			},
		]);
		if (x0 < EDGE || y0 < EDGE || x1 > W - EDGE || y1 > H - EDGE) {
			flag(`picture "${p.id}" cut off at the frame edge`, f);
		}
		if (a.opacity > 0.6 && (y0 < safeTop || y1 > safeBottom)) {
			flag(`picture "${p.id}" reaches into the top 8% / bottom 18%`, f);
		}
	}
	for (const m of s.magnifiers) {
		const st = magnifierAt(m, t, s, words);
		if (st.lensOpacity <= 0.02 || st.grow <= 0) {
			continue;
		}
		const [cx, cy] = worldToScreen(st.center, cam, s.focus);
		const r = st.radius * cam.zoom;
		const box: Box = [cx - r, cy - r, cx + r, cy + r];
		visible.push([`lens ${m.id}`, (sx, sy) => Math.hypot(sx - cx, sy - cy) <= r]);
		if (box[0] < EDGE || box[1] < EDGE || box[2] > W - EDGE || box[3] > H - EDGE) {
			flag(`lens "${m.id}" cut off at the frame edge`, f);
		}
		if (st.lensOpacity > 0.6 && (box[1] < safeTop || box[3] > safeBottom)) {
			flag(`lens "${m.id}" reaches into the top 8% / bottom 18%`, f);
		}
	}
	for (const l of s.labels) {
		const a = appearance([{in: l.in, out: l.out}], t, s, words);
		if (a.opacity <= 0.02) {
			continue;
		}
		const size = l.size ?? s.style.labelSize;
		const [sx0, sy0] = worldToScreen(l.anchor, cam, s.focus);
		const sy = Math.min(safeBottom - size, Math.max(safeTop + size, sy0 + (l.offset?.[1] ?? 0)));
		const text = l.text.replace('{n}', (l.count?.to ?? 0).toLocaleString('en-US'));
		const half = labelHalfWidth(text, size, s);
		const sx = Math.min(W - 40 - half, Math.max(40 + half, sx0 + (l.offset?.[0] ?? 0)));
		const box = labelBox(text, size, sx, sy);
		if (box[0] < 40 || box[2] > W - 40) {
			flag(`label "${l.text}" runs off the side`, f);
		}
		if (box[1] < safeTop || box[3] > safeBottom) {
			flag(`label "${l.text}" in the top 8% / bottom 18%`, f);
		}
		for (const [id, hit] of visible) {
			let touches = false;
			for (let i = 0; i <= 16 && !touches; i++) {
				for (let j = 0; j <= 4 && !touches; j++) {
					touches = hit(lerp(box[0], box[2], i / 16), lerp(box[1] - 12, box[3] + 12, j / 4));
				}
			}
			if (a.opacity > 0.3 && touches) {
				flag(`label "${l.text}" overlaps "${id}"`, f);
			}
		}
	}
}

// Words referenced by the settings must exist and match (resolveTime throws otherwise).
for (const l of s.lights) resolveTime(l.at, words);

const fmt = (fs: number[]) => {
	const out: string[] = [];
	let a = fs[0];
	let b = fs[0];
	for (const f of [...fs.slice(1), Infinity]) {
		if (f === b + 1) {
			b = f;
			continue;
		}
		out.push(a === b ? `${(a / s.fps).toFixed(2)}s` : `${(a / s.fps).toFixed(2)}-${(b / s.fps).toFixed(2)}s`);
		a = b = f;
	}
	return out.join(', ');
};
console.log(`${file}: ${frames} frames (${(frames / s.fps).toFixed(2)}s, audio ${audioSeconds.toFixed(2)}s)`);
if (issues.size === 0) {
	console.log('OK: nothing cut off, safe areas clear, labels clear of pictures.');
} else {
	for (const [k, fs] of issues) console.log(`- ${k}: ${fmt(fs)}`);
	process.exitCode = 1;
}
