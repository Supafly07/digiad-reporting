import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Audio, continueRender, delayRender, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/fonts';
import type {CameraTarget, Diagram, Light, Magnifier, Picture, Settings, Vec, Word} from './types';
import {
	appearance,
	buildPath,
	cameraAt,
	clamp01,
	depthCamera,
	easeInOutSine,
	growScale,
	labelHalfWidth,
	lerp,
	magnifierAt,
	outerTangents,
	pictureMapper,
	pulseScale,
	resolveTime,
	smoother,
	worldToScreen,
} from './timeline';

// offsetFrames: a "Part" renders the slice of the global timeline that starts there.
export type ExplainerProps = {settingsFile: string; part?: number; settings?: Settings; words?: Word[]; offsetFrames?: number};

// Faint dot grid. parallax < 1 puts it further away: it moves and zooms less than the page.
const DotGrid: React.FC<{
	cam: CameraTarget;
	focus: Vec;
	spacing: number;
	dot: number;
	opacity: number;
	parallax: number;
	blur: number;
	ink: string;
}> = ({cam, focus, spacing, dot, opacity, parallax, blur, ink}) => {
	const z = Math.pow(cam.zoom, parallax);
	const size = spacing * z;
	const ox = (((focus[0] - cam.x * parallax * z) % size) + size) % size;
	const oy = (((focus[1] - cam.y * parallax * z) % size) + size) % size;
	return (
		<AbsoluteFill
			style={{
				opacity,
				filter: blur ? `blur(${blur}px)` : undefined,
				backgroundImage: `radial-gradient(circle, ${ink} ${dot}px, transparent ${dot + 0.9}px)`,
				backgroundSize: `${size}px ${size}px`,
				backgroundPosition: `${ox - size / 2}px ${oy - size / 2}px`,
			}}
		/>
	);
};

// A soft light with a fading tail, drawn in world units (screen sizes divided by zoom):
// a wide accent-coloured halo, then a pale core that lightens the drawing under it.
const Glow: React.FC<{points: Vec[]; zoom: number; size: number; accent: string; opacity: number}> = ({
	points,
	zoom,
	size,
	accent,
	opacity,
}) => {
	const [hx, hy] = points[0];
	const halo = (size * 3.4) / zoom;
	return (
		<>
			<div
				style={{
					position: 'absolute',
					left: hx - halo / 2,
					top: hy - halo / 2,
					width: halo,
					height: halo,
					borderRadius: '50%',
					opacity: opacity * 0.85,
					filter: `blur(${12 / zoom}px)`,
					background: `radial-gradient(circle, ${accent}b0 0%, ${accent}55 35%, ${accent}18 60%, transparent 72%)`,
				}}
			/>
			{points.map(([x, y], k) => {
				const fall = 1 - k / points.length;
				const d = (size * lerp(0.4, 1.15, fall)) / zoom;
				return (
					<div
						key={k}
						style={{
							position: 'absolute',
							left: x - d / 2,
							top: y - d / 2,
							width: d,
							height: d,
							borderRadius: '50%',
							opacity: opacity * Math.pow(fall, 1.8),
							mixBlendMode: 'screen',
							filter: `blur(${4 / zoom}px)`,
							background: `radial-gradient(circle, #ffffff 0%, #dcecfc 30%, ${accent}aa 55%, transparent 72%)`,
						}}
					/>
				);
			})}
		</>
	);
};

const lightPoints = (light: Light, time: number, start: number, mapPt: (p: Vec) => Vec) => {
	const p = (time - start) / light.dur;
	if (p <= 0 || p >= 1) {
		return null;
	}
	const path = buildPath(light.path);
	const head = easeInOutSine(p);
	const trail = light.trail ?? 0.22;
	const pts: Vec[] = [];
	for (let k = 0; k < 16; k++) {
		pts.push(mapPt(path.at(head - (trail * k) / 15)));
	}
	// Fade in at the start, settle out at the end.
	const opacity = Math.min(smoother(p / 0.18), 1 - smoother((p - 0.72) / 0.28));
	return {pts, opacity};
};

const lightStarts = (light: Light, words: Word[]) => {
	const t0 = resolveTime(light.at, words);
	const n = light.repeat?.count ?? 1;
	return Array.from({length: n}, (_, i) => t0 + i * (light.repeat?.every ?? 0));
};

const PictureView: React.FC<{p: Picture; time: number; s: Settings; words: Word[]; zoom: number}> = ({
	p,
	time,
	s,
	words,
	zoom,
}) => {
	const a = appearance(p.show, time, s, words);
	if (a.opacity <= 0.001) {
		return null;
	}
	const scale = a.scale * pulseScale(p, time, words) * growScale(p, time, words);
	return (
		<Img
			src={staticFile(p.src)}
			style={{
				position: 'absolute',
				left: p.x,
				top: p.y,
				width: p.w,
				height: p.h,
				opacity: a.opacity * (p.opacity ?? 1),
				transform: `rotate(${p.rotate ?? 0}deg) scale(${p.flip ? -scale : scale}, ${scale})`,
				transformOrigin: `${p.w / 2}px ${p.h / 2}px`,
				filter: a.blur > 0.05 ? `blur(${a.blur / zoom}px)` : undefined,
			}}
		/>
	);
};

const MagnifierView: React.FC<{
	m: Magnifier;
	time: number;
	s: Settings;
	words: Word[];
	zoom: number;
	lights: Light[];
}> = ({m, time, s, words, zoom, lights}) => {
	const st = magnifierAt(m, time, s, words);
	if (st.ring <= 0 && st.grow <= 0) {
		return null;
	}
	const line = 2.2 / zoom;
	const k = st.radius / m.radius; // lens contents grow with the lens
	const local = (p: Vec): Vec => [
		st.radius + (m.inside.x + p[0] * m.inside.w - m.center[0]) * k,
		st.radius + (m.inside.y + p[1] * m.inside.h - m.center[1]) * k,
	];
	const tangents = st.grow > 0 ? outerTangents(m.source, m.sourceRadius, st.center, st.radius) : [];
	return (
		<>
			{st.grow > 0 && st.lensOpacity > 0.001 ? (
				<div
					style={{
						position: 'absolute',
						left: st.center[0] - st.radius,
						top: st.center[1] - st.radius,
						width: st.radius * 2,
						height: st.radius * 2,
						borderRadius: '50%',
						overflow: 'hidden',
						background: s.style.background,
						opacity: st.lensOpacity,
						filter: st.blur > 0.05 ? `blur(${st.blur / zoom}px)` : undefined,
					}}
				>
					<Img
						src={staticFile(m.inside.src)}
						style={{
							position: 'absolute',
							left: local([0, 0])[0],
							top: local([0, 0])[1],
							width: m.inside.w * k,
							height: m.inside.h * k,
						}}
					/>
					{lights.flatMap((light, li) =>
						lightStarts(light, words).map((t0, ri) => {
							const g = lightPoints(light, time, t0, local);
							return g ? (
								<Glow key={`${li}-${ri}`} points={g.pts} zoom={zoom} size={light.size ?? 30} accent={s.style.accent} opacity={g.opacity} />
							) : null;
						}),
					)}
				</div>
			) : null}
			<svg style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}} width={1} height={1}>
				<g opacity={st.linksOpacity} fill="none" stroke={s.style.ink} strokeWidth={line} strokeLinecap="round">
					<circle
						cx={m.source[0]}
						cy={m.source[1]}
						r={m.sourceRadius}
						pathLength={1}
						strokeDasharray={1}
						strokeDashoffset={1 - st.ring}
						transform={`rotate(-90 ${m.source[0]} ${m.source[1]})`}
					/>
					{tangents.map(([p1, p2], i) => (
						<line key={i} x1={p1[0]} y1={p1[1]} x2={lerp(p1[0], p2[0], st.links)} y2={lerp(p1[1], p2[1], st.links)} />
					))}
				</g>
				{st.grow > 0 ? (
					<circle
						cx={st.center[0]}
						cy={st.center[1]}
						r={st.radius}
						fill="none"
						stroke={s.style.ink}
						strokeWidth={line * 1.2}
						opacity={st.lensOpacity}
					/>
				) : null}
			</svg>
		</>
	);
};

// A background-layer picture, drawn in screen space with its own (slower) camera.
const DepthPictureView: React.FC<{p: Picture; time: number; s: Settings; words: Word[]; cam: CameraTarget}> = ({
	p,
	time,
	s,
	words,
	cam,
}) => {
	const a = appearance(p.show, time, s, words);
	if (a.opacity <= 0.001 || !p.depth) {
		return null;
	}
	const dc = depthCamera(cam, p.depth);
	const [left, top] = worldToScreen([p.x, p.y], dc, s.focus);
	return (
		<Img
			src={staticFile(p.src)}
			style={{
				position: 'absolute',
				left,
				top,
				width: p.w * dc.zoom,
				height: p.h * dc.zoom,
				opacity: a.opacity * (p.opacity ?? 1),
				transform: `rotate(${p.rotate ?? 0}deg) scale(${p.flip ? -a.scale : a.scale}, ${a.scale})`,
				filter: `blur(${p.depth.blur + a.blur}px)`,
			}}
		/>
	);
};

// Strokes draw themselves on (dash offset); bars are just thick strokes.
const DiagramView: React.FC<{d: Diagram; time: number; s: Settings; words: Word[]; zoom: number}> = ({d, time, s, words, zoom}) => {
	const a = appearance(d.show, time, s, words);
	if (a.opacity <= 0.001) {
		return null;
	}
	return (
		<svg
			style={{position: 'absolute', left: d.x, top: d.y, overflow: 'visible', opacity: a.opacity, filter: a.blur > 0.05 ? `blur(${a.blur / zoom}px)` : undefined}}
			width={1}
			height={1}
		>
			{d.strokes.map((st, i) => {
				const e = smoother((time - resolveTime(st.at, words)) / st.dur);
				if (e <= 0) {
					return null;
				}
				let pts = st.points;
				if (st.smooth) {
					const path = buildPath(st.points);
					pts = Array.from({length: 60}, (_, k) => path.at(k / 59));
				}
				const dPath = pts.map((p, k) => `${k ? 'L' : 'M'}${p[0]} ${p[1]}`).join(' ');
				return (
					<path
						key={i}
						d={dPath}
						fill="none"
						stroke={s.style.ink}
						strokeOpacity={st.opacity ?? 1}
						strokeWidth={st.width ?? (st.px ?? 2.2) / zoom}
						strokeLinecap={st.cap ?? 'round'}
						strokeLinejoin="round"
						pathLength={1}
						strokeDasharray="1 1"
						strokeDashoffset={1 - e}
					/>
				);
			})}
			{(d.dots ?? []).map((dot, i) => {
				const e = smoother((time - resolveTime(dot.time, words)) / 0.5);
				return e > 0 ? <circle key={i} cx={dot.at[0]} cy={dot.at[1]} r={(dot.r * lerp(0.6, 1, e)) / zoom} fill={s.style.ink} opacity={e} /> : null;
			})}
		</svg>
	);
};

const formatCount = (n: number, decimals = 0) =>
	n.toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals});

export const Explainer: React.FC<ExplainerProps> = ({settings, words, offsetFrames = 0}) => {
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const [fontHandle] = useState(() => delayRender('Loading label font'));
	useEffect(() => {
		if (!settings) {
			return;
		}
		loadFont({family: settings.style.font, url: staticFile(settings.style.fontFile), weight: '700'})
			.then(() => continueRender(fontHandle))
			.catch((err) => {
				console.error(err);
				continueRender(fontHandle);
			});
	}, [settings, fontHandle]);

	if (!settings || !words) {
		return null;
	}
	const s = settings;
	const time = (frame + offsetFrames) / fps;
	const cam = cameraAt(time, s, words);
	const byId = new Map(s.pictures.map((p) => [p.id, p]));
	const diagrams = new Map((s.diagrams ?? []).map((d) => [d.id, d]));

	// Map a normalized point on a picture to world space, following its fade scale / pulse.
	const onPicture = (p: Picture) => {
		const a = appearance(p.show, time, s, words);
		return {
			opacity: a.opacity * (p.opacity ?? 1),
			map: pictureMapper(p, a.scale * pulseScale(p, time, words) * growScale(p, time, words)),
		};
	};

	const safeTop = s.safeArea.top * height;
	const safeBottom = (1 - s.safeArea.bottom) * height;

	return (
		<AbsoluteFill style={{background: s.style.background, overflow: 'hidden'}}>
			<Audio src={staticFile(s.audio)} startFrom={offsetFrames} />
			<DotGrid
				cam={cam}
				focus={s.focus}
				spacing={s.grid.far.spacing}
				dot={s.grid.far.dot}
				opacity={s.grid.far.opacity}
				parallax={s.grid.far.parallax}
				blur={s.grid.far.blur}
				ink={s.style.ink}
			/>
			{s.pictures
				.filter((p) => p.depth)
				.map((p) => (
					<DepthPictureView key={p.id} p={p} time={time} s={s} words={words} cam={cam} />
				))}
			<DotGrid cam={cam} focus={s.focus} spacing={s.grid.spacing} dot={s.grid.dot} opacity={s.grid.opacity} parallax={1} blur={0} ink={s.style.ink} />

			{/* The page: everything in world units, filmed by one camera. */}
			<div
				style={{
					position: 'absolute',
					left: 0,
					top: 0,
					transformOrigin: '0 0',
					transform: `translate(${s.focus[0] - cam.x * cam.zoom}px, ${s.focus[1] - cam.y * cam.zoom}px) scale(${cam.zoom})`,
				}}
			>
				{s.pictures
					.filter((p) => !p.depth)
					.map((p) => (
						<PictureView key={p.id} p={p} time={time} s={s} words={words} zoom={cam.zoom} />
					))}
				{(s.diagrams ?? []).map((d) => (
					<DiagramView key={d.id} d={d} time={time} s={s} words={words} zoom={cam.zoom} />
				))}
				{s.lights
					.filter((l) => !l.on.startsWith('lens:'))
					.flatMap((light, li) => {
						let opacity: number;
						let map: (n: Vec) => Vec;
						if (light.on.startsWith('diagram:')) {
							const d = diagrams.get(light.on.slice(8));
							if (!d) {
								throw new Error(`Light on unknown diagram "${light.on}"`);
							}
							opacity = appearance(d.show, time, s, words).opacity;
							map = (n) => [d.x + n[0], d.y + n[1]];
						} else {
							const pic = byId.get(light.on);
							if (!pic) {
								throw new Error(`Light on unknown picture "${light.on}"`);
							}
							({opacity, map} = onPicture(pic));
						}
						return lightStarts(light, words).map((t0, ri) => {
							const g = lightPoints(light, time, t0, map);
							return g && opacity > 0.01 ? (
								<Glow key={`${li}-${ri}`} points={g.pts} zoom={cam.zoom} size={light.size ?? 30} accent={s.style.accent} opacity={g.opacity * opacity} />
							) : null;
						});
					})}
				{s.magnifiers.map((m) => (
					<MagnifierView key={m.id} m={m} time={time} s={s} words={words} zoom={cam.zoom} lights={s.lights.filter((l) => l.on === `lens:${m.id}`)} />
				))}
			</div>

			{/* Labels: attached to a point on the page, but always the same size on screen. */}
			{s.labels.map((l, i) => {
				const a = appearance([{in: l.in, out: l.out}], time, s, words);
				if (a.opacity <= 0.001) {
					return null;
				}
				const size = l.size ?? s.style.labelSize;
				const [sx0, sy0] = worldToScreen(l.anchor, cam, s.focus);
				const sy = Math.min(safeBottom - size, Math.max(safeTop + size, sy0 + (l.offset?.[1] ?? 0)));
				let text = l.text;
				if (l.count) {
					const p = smoother((time - resolveTime(l.count.at, words)) / l.count.dur);
					text = text.replace('{n}', formatCount(lerp(l.count.from, l.count.to, clamp01(p)), l.count.decimals));
				}
				const half = labelHalfWidth(l.text.replace('{n}', formatCount(l.count?.to ?? 0, l.count?.decimals)), size, s);
				const sx = Math.min(width - 40 - half, Math.max(40 + half, sx0 + (l.offset?.[0] ?? 0)));
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: 0,
							width,
							top: sy - size / 2,
							transform: `translateX(${sx - width / 2}px) scale(${a.scale})`,
							textAlign: 'center',
							opacity: a.opacity,
							filter: a.blur > 0.05 ? `blur(${a.blur}px)` : undefined,
							fontFamily: s.style.font,
							fontWeight: 700,
							fontSize: size,
							lineHeight: 1,
							letterSpacing: `${s.style.labelTracking}em`,
							paddingLeft: `${s.style.labelTracking}em`,
							color: s.style.ink,
							whiteSpace: 'nowrap',
						}}
					>
						{text}
						{l.sub ? (
							<div style={{fontSize: size * 0.5, marginTop: size * 0.35, opacity: 0.62, letterSpacing: `${s.style.labelTracking * 0.9}em`}}>
								{l.sub}
							</div>
						) : null}
					</div>
				);
			})}
		</AbsoluteFill>
	);
};
