// Render review stills.
// Usage: npx tsx scripts/stills.mjs [settings file in public/] [out dir] [--every s] [--at t1,t2,...] [--scale k]
//   default: one every half second plus one at the start of every sentence (short videos)
//   --every 1: one every second, in a folder per chapter (long videos)
//   --at: just these times (seconds)
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import {mkdirSync, readFileSync} from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const opt = (name) => {
	const i = args.indexOf(name);
	return i < 0 ? null : args.splice(i, 2)[1];
};
const every = opt('--every');
const at = opt('--at');
const scale = Number(opt('--scale') ?? 1);
const settingsFile = args[0] ?? 'walking-10k.settings.json';
const outDir = args[1] ?? 'out/stills';

const settings = JSON.parse(readFileSync(path.join('public', settingsFile), 'utf8'));
const {words} = JSON.parse(readFileSync(path.join('public', settings.words), 'utf8'));

const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE ?? null;
const browser = await openBrowser('chrome', {browserExecutable});
const inputProps = {settingsFile};
const composition = await selectComposition({serveUrl, id: 'Explainer', inputProps, puppeteerInstance: browser, browserExecutable});
const fps = composition.fps;

// Chapter folders follow the same boundaries as the Part compositions.
const {chapterSpans} = await import('../src/timeline.ts');
const spans = chapterSpans(settings, words, composition.durationInFrames / fps);
const folder = (t) => {
	const i = spans.findIndex((c) => t < c.end);
	const c = spans[i < 0 ? spans.length - 1 : i];
	return `${String(spans.indexOf(c)).padStart(2, '0')}_${c.id}`;
};
const stamp = (t) => `t${t.toFixed(2).padStart(6, '0')}`;

const shots = new Map();
if (at) {
	for (const t of at.split(',').map(Number)) shots.set(Math.round(t * fps), stamp(t));
} else if (every) {
	for (let t = 0; t * fps < composition.durationInFrames; t += Number(every)) {
		shots.set(Math.round(t * fps), path.join(folder(t), stamp(t)));
	}
} else {
	for (let t = 0; t * fps < composition.durationInFrames; t += 0.5) {
		shots.set(Math.round(t * fps), `t${t.toFixed(1).padStart(4, '0')}`);
	}
	words.forEach((w, i) => {
		if (i === 0 || words[i - 1].sentence !== w.sentence) {
			shots.set(Math.round(w.start * fps), `s${w.sentence + 1}_t${w.start.toFixed(2)}`);
		}
	});
}

const queue = [...shots].sort((a, b) => a[0] - b[0]);
let done = 0;
const worker = async () => {
	while (queue.length) {
		const [frame, name] = queue.shift();
		const output = path.join(outDir, `${name}.jpg`);
		mkdirSync(path.dirname(output), {recursive: true});
		await renderStill({
			serveUrl,
			composition,
			frame: Math.min(frame, composition.durationInFrames - 1),
			output,
			imageFormat: 'jpeg',
			jpegQuality: 85,
			scale,
			inputProps,
			puppeteerInstance: browser,
		});
		if (++done % 25 === 0) process.stdout.write(`${done} `);
	}
};
await Promise.all(Array.from({length: 3}, worker));
await browser.close({silent: true});
console.log(`\n${shots.size} stills in ${outDir}`);
