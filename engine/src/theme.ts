// House style from the 2D Documentary Skill (5.1): muted editorial palette, ONE accent owned by the subject,
// red as the second colour, ink outlines that stay constant, drawn light, a grade per location.
import type { Grade } from "./types";

export const W = 1080;
export const H = 1920;
export const WORLD_W = 1404; // sets are 1.3x the frame width so pans have room
export const FLOOR_Y = 1240; // floor line at ~64.5 % of frame height (skill: 58-68 %)
export const CAST_Y = 1530; // where feet stand in a wide set
export const INK = "#111111";
export const OUTLINE = 4.5; // px at 1080 (skill: 3 px at 720p)

export const PAL = {
  teal: "#4A6B6E",
  wood: "#6E4726",
  slate: "#2C3E50",
  paper: "#F4F1EA",
  beige: "#CDBB9A",
  cream: "#F3E9D2",
  red: "#C33631",
  accent: "#8FD23F",
  accentBody: "#64A14B",
  yellow: "#E8C547",
  sky: "#9CC3D5",
  grass: "#7C8F4E",
  sand: "#D9B77E",
  stone: "#8C8577",
  night: "#13192B",
};

export type GradeSpec = { tint: string; tintOpacity: number; blend: "multiply" | "screen" | "soft-light"; vignette: number; sky: [string, string]; ambient: number };

// vignette = opacity at the corners (skill: 15 % bright, 35 % mid, 60 % dark scenes)
export const GRADES: Record<Grade, GradeSpec> = {
  day: { tint: "#D4D0BF", tintOpacity: 0.16, blend: "multiply", vignette: 0.22, sky: ["#8FB9CF", "#D9E6E3"], ambient: 1 },
  dusk: { tint: "#B9826A", tintOpacity: 0.22, blend: "multiply", vignette: 0.38, sky: ["#5B4A78", "#E39C7A"], ambient: 0.85 },
  night: { tint: "#1A2751", tintOpacity: 0.42, blend: "multiply", vignette: 0.55, sky: ["#0D1328", "#1A2751"], ambient: 0.55 },
  dinner: { tint: "#7B0B1A", tintOpacity: 0.28, blend: "multiply", vignette: 0.45, sky: ["#2A1410", "#45221D"], ambient: 0.7 },
  period: { tint: "#B9A580", tintOpacity: 0.4, blend: "multiply", vignette: 0.42, sky: ["#8C7A5C", "#D8C7A2"], ambient: 0.9 },
  triumph: { tint: "#DB747A", tintOpacity: 0.18, blend: "soft-light", vignette: 0.3, sky: ["#48296A", "#F0B789"], ambient: 1 },
  dark: { tint: "#0A0C18", tintOpacity: 0.55, blend: "multiply", vignette: 0.62, sky: ["#0A0C18", "#2A1D15"], ambient: 0.45 },
};

// ---------- colour helpers
const clamp = (v: number, a = 0, b = 255) => Math.max(a, Math.min(b, v));
export function hex(c: string): [number, number, number] {
  const h = c.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((x) => x + x).join("") : h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
export function rgb(r: number, g: number, b: number) {
  return "#" + [r, g, b].map((v) => Math.round(clamp(v)).toString(16).padStart(2, "0")).join("");
}
/** amt < 0 darker, > 0 lighter */
export function shade(c: string, amt: number) {
  const [r, g, b] = hex(c);
  return amt < 0 ? rgb(r * (1 + amt), g * (1 + amt), b * (1 + amt)) : rgb(r + (255 - r) * amt, g + (255 - g) * amt, b + (255 - b) * amt);
}
export function mix(a: string, b: string, t: number) {
  const A = hex(a), B = hex(b);
  return rgb(A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t);
}

// ---------- deterministic randomness (skill: any randomness uses a fixed seed so re-renders are identical)
export function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export function hashStr(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}

// ---------- easing
export const clamp01 = (t: number) => Math.max(0, Math.min(1, t));
export const easeOut = (t: number) => 1 - Math.pow(1 - clamp01(t), 3);
export const easeIn = (t: number) => Math.pow(clamp01(t), 3);
export const easeInOut = (t: number) => {
  t = clamp01(t);
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};
/** decelerating move with an overshoot capped at 2 % (skill 5.4) */
export const settle = (t: number) => {
  t = clamp01(t);
  const e = easeOut(t);
  return e + Math.sin(t * Math.PI) * 0.02 * (1 - t);
};
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
/** damped pendulum for hanging tags */
export const pendulum = (f: number, amp = 14, period = 26, decay = 0.06) => amp * Math.cos((f / period) * Math.PI * 2) * Math.exp(-decay * f);
