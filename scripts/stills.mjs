// Render review stills: one every half second plus one at the start of every sentence.
// Usage: node scripts/stills.mjs [settings file in public/] [out dir]
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import {mkdirSync, readFileSync} from 'node:fs';
import path from 'node:path';

const settingsFile = process.argv[2] ?? 'walking-10k.settings.json';
const outDir = process.argv[3] ?? 'out/stills';
mkdirSync(outDir, {recursive: true});

const settings = JSON.parse(readFileSync(path.join('public', settingsFile), 'utf8'));
const {words} = JSON.parse(readFileSync(path.join('public', settings.words), 'utf8'));

const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE ?? null;
const browser = await openBrowser('chrome', {browserExecutable});
const inputProps = {settingsFile};
const composition = await selectComposition({serveUrl, id: 'Explainer', inputProps, puppeteerInstance: browser, browserExecutable});

const shots = new Map();
for (let t = 0; t * composition.fps < composition.durationInFrames; t += 0.5) {
	shots.set(Math.round(t * composition.fps), `t${t.toFixed(1).padStart(4, '0')}`);
}
words.forEach((w, i) => {
	if (i === 0 || words[i - 1].sentence !== w.sentence) {
		shots.set(Math.round(w.start * composition.fps), `s${w.sentence + 1}_t${w.start.toFixed(2)}`);
	}
});

for (const [frame, name] of [...shots].sort((a, b) => a[0] - b[0])) {
	await renderStill({
		serveUrl,
		composition,
		frame: Math.min(frame, composition.durationInFrames - 1),
		output: path.join(outDir, `${name}.jpg`),
		imageFormat: 'jpeg',
		jpegQuality: 85,
		inputProps,
		puppeteerInstance: browser,
	});
	process.stdout.write('.');
}
await browser.close({silent: true});
console.log(`\n${shots.size} stills in ${outDir}`);
