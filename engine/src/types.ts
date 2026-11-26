// The render plan written by flatframe/beats.py. Everything is in frames (30 fps) and 1080x1920 frame pixels.

export type Grade = "day" | "night" | "dinner" | "period" | "triumph" | "dark" | "dusk";
export type Expr = "neutral" | "happy" | "surprised" | "thinking" | "concerned" | "angry" | "sad" | "deadpan" | "panic";
export type Pose = "idle" | "talking" | "pointing" | "holding" | "walking" | "cheering" | "shrugging" | "running";
export type Facing = "left" | "right" | "front" | "back";

export type CastMember = {
  id: string;
  name?: string;
  skin: string;
  hair: { style: string; color: string };
  outfit: { kind: string; color: string; accent: string };
  glasses?: "none" | "round" | "square";
  creature?: string; // a drawn animal instead of a person
};

export type Actor = {
  id: string;
  x: number; // 0..1 across the set
  expr: Expr;
  pose: Pose;
  facing: Facing;
  scale?: number; // 1 = standard height in a wide shot
  enterAt?: number; // frame (relative to the shot) a walk-in starts
  enterFrom?: "left" | "right";
  exprAt?: { at: number; expr: Expr }[];
  talk?: { start: number; env: number[] }; // loudness envelope per frame from `start`
  hold?: string; // prop held in the hand
  layer?: "cast" | "fg";
  count?: number; // a crowd of identical extras/creatures spread around x
};

export type Entry = "slide" | "drop" | "grow" | "slam" | "switch" | "none";

export type PropItem = {
  kind: string;
  x: number; // 0..1 across the set
  y?: number; // 0..1 down the frame (default: standing on the floor line)
  scale?: number;
  entry?: Entry;
  at?: number; // frame of the entry, relative to the shot
  label?: string;
  glow?: boolean; // hero object halo (accent colour)
  layer?: "back" | "mid" | "cast" | "fg";
  flip?: boolean;
};

export type SetSpec = {
  kind: string;
  grade: Grade;
  variant: number;
  wall?: string;
  floor?: string;
  signs?: string[]; // hand-lettered in-world text
};

export type Camera = {
  move: "push" | "pull" | "pan" | "tilt" | "still" | "drift";
  timing: "creep" | "creep_punch" | "settle";
  framing: "wide" | "medium" | "close";
  focus: [number, number]; // 0..1 of the set width, 0..1 of the frame height
  amount?: number; // push/pull: extra zoom (0.10-0.20); pan/tilt: fraction of the frame
  dir?: 1 | -1;
  punchAt?: number; // frame of the punch-in (creep_punch)
  tiltDeg?: number; // the rare "slight tilt"
};

export type Build = {
  recipe: "stack" | "side_slide" | "slam_sticker" | "counter" | "compare" | "state_flip" | "glow_on" | "drop_puff" | "grow" | "tag_vanish" | "timeline";
  at: number[]; // frames (relative) when each item lands, tied to words
  items?: { label: string; value?: number; kind?: string; accent?: boolean }[];
  value?: number;
  from?: number;
  prefix?: string;
  suffix?: string;
  label?: string;
  x?: number;
  y?: number;
  scale?: number;
  hang?: boolean; // a sign hung in the upper frame (ropes) instead of standing on posts
};

export type OverlayText = { kind: "strip" | "stamp" | "quote" | "calendar"; text: string; at: number; who?: string };

export type MapSpec = {
  style: "light" | "dark";
  focus: string; // country name as in world-atlas, or "world"
  highlight?: string[];
  pins?: { lon: number; lat: number; label?: string; at: number }[];
  route?: { from: [number, number]; to: [number, number]; at: number };
  zoomFrom?: number;
};

export type Fx = { kind: string; strength?: number; purpose?: string };

export type Shot = {
  from: number;
  dur: number;
  kind: "scene" | "skit" | "card" | "title" | "insert" | "map" | "tabletop" | "triptych" | "outro";
  outro?: { text: string };
  set?: SetSpec;
  actors?: Actor[];
  props?: PropItem[];
  build?: Build;
  texts?: OverlayText[];
  card?: { text: string; typeFrom: number; cps: number };
  title?: { lines: string[]; accentWord?: string; at: number[] };
  map?: MapSpec;
  panels?: { label: string; prop: string; at: number }[];
  camera: Camera;
  fx?: { main?: Fx; bg?: Fx };
  transition?: "cut" | "whip" | "flash";
  ots?: { near: string; far: string }; // over-the-shoulder skit framing
  line?: string; // narration covered (for review sheets)
};

export type Plan = {
  id: string;
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  seed: number;
  accent: string;
  cast: CastMember[];
  hero: { kind: string; label?: string };
  shots: Shot[];
  captions?: { from: number; to: number; words: { w: string; s: number; e: number }[] }[];
  brand?: { corner: string };
};
