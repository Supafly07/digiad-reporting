// Settings schema for one explainer video. Everything that changes between videos lives in
// a settings JSON in public/ (see public/walking-10k.settings.json); the code never changes.

// A moment in the video: plain seconds, or a word from the narration timing file
// ("say" is checked against the transcript so a typo in the index fails loudly).
export type Time = number | {word: number; say: string; offset?: number; edge?: 'start' | 'end'};

export type Vec = [number, number];

export type CameraTarget = {x: number; y: number; zoom: number};

export type CameraMove = {
	at: Time;
	dur: number;
	to: CameraTarget;
	note?: string;
};

// When a picture is on screen. in: null = visible from the first frame; out: null = to the end.
export type ShowWindow = {
	in: Time | null;
	out: Time | null;
	inDur?: number;
	outDur?: number;
	// Scale the picture eases to while leaving (e.g. 0.55 to shrink into something).
	outScale?: number;
};

export type Picture = {
	id: string;
	src: string;
	// World placement of the whole image (world units = screen px at zoom 1).
	x: number;
	y: number;
	w: number;
	h: number;
	// Normalized bounding box of the drawn pixels, used for the in-frame check.
	content: [number, number, number, number];
	show: ShowWindow[];
	// Gentle repeating scale pulse (a heartbeat), between from and to.
	pulse?: {from: Time; to: Time; bpm: number; amount: number};
	note?: string;
};

export type Magnifier = {
	id: string;
	// Detail the lens grows out of, in world coordinates, and the small ring around it.
	source: Vec;
	sourceRadius: number;
	center: Vec;
	radius: number;
	// Picture shown inside the lens, placed in world coordinates (clipped to the lens).
	inside: {src: string; x: number; y: number; w: number; h: number};
	ringAt: Time;
	growAt: Time;
	growDur: number;
	// The ring and the two connecting lines fade here (the lens itself stays).
	linksOut: Time;
	out: Time;
	note?: string;
};

// A soft light travelling along a path traced on a picture (normalized picture coordinates).
export type Light = {
	on: string; // picture id, or "lens:<magnifier id>" for the picture inside a lens
	path: Vec[];
	at: Time;
	dur: number;
	size?: number; // screen px of the glow
	trail?: number; // 0..1 of the path length
	repeat?: {count: number; every: number};
	note?: string;
};

export type Label = {
	text: string;
	anchor: Vec; // world point the label is attached to
	offset?: Vec; // screen px from the anchor
	in: Time;
	out: Time;
	count?: {from: number; to: number; at: Time; dur: number};
	size?: number;
};

export type Settings = {
	title: string;
	width: number;
	height: number;
	fps: number;
	audio: string;
	words: string;
	tailSeconds: number;
	safeArea: {top: number; bottom: number};
	// Screen point the camera aims at: the middle of the safe area.
	focus: Vec;
	style: {
		background: string;
		ink: string;
		accent: string;
		font: string;
		fontFile: string;
		labelSize: number;
		labelTracking: number;
	};
	grid: {
		spacing: number;
		dot: number;
		opacity: number;
		far: {parallax: number; spacing: number; dot: number; opacity: number; blur: number};
	};
	fade: {dur: number; scale: number; blur: number};
	camera: {start: CameraTarget; moves: CameraMove[]};
	pictures: Picture[];
	magnifiers: Magnifier[];
	lights: Light[];
	labels: Label[];
};

export type Word = {text: string; start: number; end: number; i: number; sentence: number};
export type WordsFile = {audio: string; duration: number; words: Word[]};
