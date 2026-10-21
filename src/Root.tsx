import React from 'react';
import {Composition, staticFile, type CalculateMetadataFunction} from 'remotion';
import {getAudioDurationInSeconds} from '@remotion/media-utils';
import {Explainer, type ExplainerProps} from './Explainer';
import {chapterSpans, durationInSeconds} from './timeline';
import type {Settings, WordsFile} from './types';

const load = async (settingsFile: string) => {
	const settings: Settings = await (await fetch(staticFile(settingsFile))).json();
	const words: WordsFile = await (await fetch(staticFile(settings.words))).json();
	const total = durationInSeconds(await getAudioDurationInSeconds(staticFile(settings.audio)), settings);
	return {settings, words: words.words, total};
};

// The whole video.
const wholeVideo: CalculateMetadataFunction<ExplainerProps> = async ({props}) => {
	const {settings, words, total} = await load(props.settingsFile);
	return {
		fps: settings.fps,
		width: settings.width,
		height: settings.height,
		durationInFrames: Math.ceil(total * settings.fps),
		props: {...props, settings, words, offsetFrames: 0},
	};
};

// One chapter: the slice of the same global timeline, so rendered parts join seamlessly.
const oneChapter: CalculateMetadataFunction<ExplainerProps> = async ({props}) => {
	const {settings, words, total} = await load(props.settingsFile);
	const spans = chapterSpans(settings, words, total);
	const span = spans[props.part ?? 0];
	if (!span) {
		throw new Error(`No chapter #${props.part}; this video has ${spans.length}`);
	}
	const lastFrame = Math.ceil(total * settings.fps);
	const from = Math.round(span.start * settings.fps);
	const to = props.part === spans.length - 1 ? lastFrame : Math.round(span.end * settings.fps);
	return {
		fps: settings.fps,
		width: settings.width,
		height: settings.height,
		durationInFrames: to - from,
		props: {...props, settings, words, offsetFrames: from},
	};
};

// Pick the video with --props='{"settingsFile":"full/settings.json"}' (and "part": n for one chapter).
export const RemotionRoot: React.FC = () => (
	<>
		<Composition
			id="Explainer"
			component={Explainer}
			width={1080}
			height={1920}
			fps={60}
			durationInFrames={60}
			defaultProps={{settingsFile: 'walking-10k.settings.json'} as ExplainerProps}
			calculateMetadata={wholeVideo}
		/>
		<Composition
			id="Part"
			component={Explainer}
			width={1920}
			height={1080}
			fps={60}
			durationInFrames={60}
			defaultProps={{settingsFile: 'full/settings.json', part: 0} as ExplainerProps}
			calculateMetadata={oneChapter}
		/>
	</>
);
