import React from 'react';
import {Composition, staticFile} from 'remotion';
import {getAudioDurationInSeconds} from '@remotion/media-utils';
import {Explainer, type ExplainerProps} from './Explainer';
import {durationInSeconds} from './timeline';
import type {Settings, WordsFile} from './types';

// Pick the video with --props='{"settingsFile":"my-video.settings.json"}'.
export const RemotionRoot: React.FC = () => (
	<Composition
		id="Explainer"
		component={Explainer}
		width={1080}
		height={1920}
		fps={60}
		durationInFrames={60}
		defaultProps={{settingsFile: 'walking-10k.settings.json'} as ExplainerProps}
		calculateMetadata={async ({props}) => {
			const settings: Settings = await (await fetch(staticFile(props.settingsFile))).json();
			const words: WordsFile = await (await fetch(staticFile(settings.words))).json();
			const audioSeconds = await getAudioDurationInSeconds(staticFile(settings.audio));
			return {
				fps: settings.fps,
				width: settings.width,
				height: settings.height,
				durationInFrames: Math.ceil(durationInSeconds(audioSeconds, settings) * settings.fps),
				props: {...props, settings, words: words.words},
			};
		}}
	/>
);
