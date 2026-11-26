// Camera grammar from the 2D Documentary Skill (5.5): rarely still but always level and square to the back wall;
// depth comes from layers spreading apart (the foreground grows 1.3-2x faster than the wall on a push-in).
// One move per shot, three timings rotated (creep, creep + punch on the key word, settle), a slow hand-held drift so
// still moments stay alive. All motion is a pure function of the frame.
import type { Camera } from "../types";
import { H, W, WORLD_W, clamp01, easeInOut, easeOut } from "../theme";

export type CamState = { z: number; cx: number; cy: number; rot: number };

const BASE_ZOOM = { wide: 1, medium: 1.5, close: 2.8 }; // keep in sync with flatframe/beats.py ZOOM

function clampCenter(z: number, cx: number, cy: number) {
  const hw = W / (2 * z), hh = H / (2 * z);
  return [Math.min(Math.max(cx, hw), WORLD_W - hw), Math.min(Math.max(cy, hh), H - hh)];
}

export function camAt(cam: Camera, f: number, dur: number, seed: number): CamState {
  const t = clamp01(f / Math.max(1, dur - 1));
  const z0 = BASE_ZOOM[cam.framing] ?? 1;
  let z = z0;
  let cx = cam.focus[0] * WORLD_W;
  let cy = cam.focus[1] * H;
  const amt = cam.amount ?? 0.14;
  const dir = cam.dir ?? 1;
  const prog = cam.timing === "settle" ? easeOut(clamp01(t * 3)) : cam.timing === "creep_punch" ? t * 0.6 : t;
  switch (cam.move) {
    case "push":
      z = z0 * (1 + amt * prog);
      break;
    case "pull":
      z = z0 * (1 + amt * (1 - prog));
      break;
    case "pan":
      cx += dir * W * amt * (prog - 0.5) / z0;
      break;
    case "tilt":
      cy += dir * H * amt * (prog - 0.5) / z0;
      break;
    default:
      break;
  }
  if (cam.timing === "creep_punch" && cam.punchAt !== undefined && f >= cam.punchAt) {
    z *= 1 + 0.12 * easeInOut((f - cam.punchAt) / 12); // +8-15 % in 9-15 frames, landing on the word, then hold
  }
  // hand-held drift: a few pixels, two slow sines
  const dx = Math.sin((f + seed) / 47) * 3 + Math.sin((f + seed * 3) / 23) * 1.5;
  const dy = Math.cos((f + seed) / 53) * 2.5;
  const [ccx, ccy] = clampCenter(z, cx + dx / z, cy + dy / z);
  return { z, cx: ccx, cy: ccy, rot: cam.tiltDeg ?? 0 };
}

/** transform of one depth layer: depth 1 = the cast line, <1 further back, >1 nearer the lens */
export function layerTransform(c: CamState, depth: number) {
  const z = 1 + (c.z - 1) * depth;
  const cx = WORLD_W / 2 + (c.cx - WORLD_W / 2) * depth;
  const cy = H / 2 + (c.cy - H / 2) * depth;
  return `translate(${W / 2} ${H / 2}) rotate(${c.rot}) scale(${z}) translate(${-cx} ${-cy})`;
}

export const DEPTH = { sky: 0.35, back: 0.7, floor: 0.82, mid: 0.88, cast: 1, fg: 1.45 };
