// Settings schema for one explainer video. Everything that changes between videos lives in
// a settings JSON in public/ (see public/walking-10k.settings.json); the code never changes.

// A moment in the video: plain seconds, or a word from the narration timing file
// ("say" is checked against the transcript so a typo in the index fails loudly).
// For long videos a cue can name a sentence id from the script instead ({s: "S012", say: "sugar"});
// without "say" it is the start (or, with edge "end", the end) of that sentence.
export type Time =
	| number
	| {word: number; say: string; offset?: number; edge?: 'start' | 'end'}
	| {s: string; say?: string; nth?: number; offset?: number; edge?: 'start' | 'end'};

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
	// Maximum opacity (e.g. 0.15 for a faint background element).
	opacity?: number;
	// A background layer: moves slower than the page (parallax < 1) and is a little blurred.
	// It is drawn exactly where placed when the camera is at "home".
	depth?: {parallax: number; blur: number; home: CameraTarget};
	// Decoration (e.g. background footprints) is allowed to run off the frame edge.
	decor?: boolean;
	note?: string;
};

// A diagram that draws itself: strokes in local coordinates around (x, y) on the page.
export type Stroke = {
	points: Vec[];
	at: Time;
	dur: number;
	// Line width in world units (bars), or "px" for a hairline that stays thin at any zoom.
	width?: number;
	px?: number;
	opacity?: number;
	smooth?: boolean;
	cap?: 'round' | 'butt';
};

export type Diagram = {
	id: string;
	x: number;
	y: number;
	show: ShowWindow[];
	strokes: Stroke[];
	// Small filled dots that fade in (data points).
	dots?: {at: Vec; time: Time; r: number}[];
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
	// picture id, "lens:<magnifier id>" for the picture inside a lens, or "diagram:<id>"
	// (then the path is in the diagram's local coordinates, not 0..1).
	on: string;
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
	count?: {from: number; to: number; at: Time; dur: number; decimals?: number};
	size?: number;
	// Smaller, lighter second line under the main text.
	sub?: string;
};

export type Chapter = {id: string; title: string; from: Time};

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
	// The camera never holds perfectly still: a slow wander of this many screen px and zoom.
	drift?: {px: number; zoom: number};
	// Chapters become separately renderable "Part" compositions that join seamlessly.
	chapters?: Chapter[];
	pictures: Picture[];
	magnifiers: Magnifier[];
	lights: Light[];
	labels: Label[];
	diagrams?: Diagram[];
};

export type Word = {
	text: string;
	start: number;
	end: number;
	i: number;
	sentence: number;
	sid?: string;
	wi?: number;
	paragraph?: string;
	chapter?: string;
};
export type WordsFile = {audio: string; duration: number; words: Word[]};
