// One character rig, many outfits (2D Documentary Skill 5.2): a large round head as wide as the torso, an egg torso
// with layered clothing and a darker hem band, straight dark stroke legs (22-25 % of height), single thin black arms
// with mitten hands, small oval eyes, floating brows, no nose / ears. Four views, nine expressions, eight poses,
// idle life (blink every ~3.2 s, breathing bob) and loudness-driven mouths for skit lines (5.4).
// Native units: feet at (0,0), about 420 tall. Line weight 2-3 % of head diameter.
import React from "react";
import type { CastMember, Expr, Pose } from "../types";
import { INK, hashStr, shade } from "../theme";

export type View = "front" | "three_quarter" | "side" | "back";

type Props = {
  who: CastMember;
  frame: number; // frame inside the shot
  expr: Expr;
  pose: Pose;
  view: View;
  mirror?: boolean; // facing left
  talkLevel?: number | null; // 0..1 loudness this frame, null = not speaking
  walkPhase?: number | null;
  holdKind?: string;
  renderHeld?: (kind: string) => React.ReactNode;
};

const LW = 4; // limb + outline width (2.7 % of the 150 head)
const HEAD_R = 74;
const HEAD_Y = -322;
const TORSO_Y = -178;
const TORSO_RX = 72;
const TORSO_RY = 82;
const HIP_Y = -104;
const SHOULDER_Y = -232;

function mouthPath(kind: string, dx: number, w: number) {
  const x = dx, y = HEAD_Y + 34;
  switch (kind) {
    case "closed": return { d: `M${x - w * 0.5} ${y} Q${x} ${y + 4} ${x + w * 0.5} ${y}`, fill: false };
    case "small_o": return { d: `M${x} ${y - 7} a6 7 0 1 0 0.1 0Z`, fill: true };
    case "tall_o": return { d: `M${x} ${y - 11} a8 12 0 1 0 0.1 0Z`, fill: true };
    case "wide": return { d: `M${x - w * 0.55} ${y - 4} Q${x} ${y + 22} ${x + w * 0.55} ${y - 4} Z`, fill: true };
    case "smile": return { d: `M${x - w * 0.6} ${y - 4} Q${x} ${y + 14} ${x + w * 0.6} ${y - 4}`, fill: false };
    case "grin": return { d: `M${x - w * 0.7} ${y - 6} Q${x} ${y + 20} ${x + w * 0.7} ${y - 6} Z`, fill: true };
    case "frown": return { d: `M${x - w * 0.5} ${y + 6} Q${x} ${y - 6} ${x + w * 0.5} ${y + 6}`, fill: false };
    case "flat": return { d: `M${x - w * 0.5} ${y + 2} L${x + w * 0.5} ${y + 2}`, fill: false };
    case "teeth": return { d: `M${x - w * 0.6} ${y - 6} h${w * 1.2} v14 h${-w * 1.2} Z`, fill: true };
    default: return { d: `M${x - w * 0.5} ${y} Q${x} ${y + 8} ${x + w * 0.5} ${y}`, fill: false };
  }
}

const EXPR: Record<Expr, { mouth: string; brow: [number, number]; eye: "dot" | "wide" | "lid" | "up" | "sad" }> = {
  // brow: [lift, inner tilt]; positive tilt = inner end lower (angry)
  neutral: { mouth: "smile", brow: [0, 0], eye: "dot" },
  happy: { mouth: "grin", brow: [6, -2], eye: "dot" },
  surprised: { mouth: "small_o", brow: [14, -2], eye: "wide" },
  thinking: { mouth: "flat", brow: [8, 3], eye: "up" },
  concerned: { mouth: "frown", brow: [6, -8], eye: "dot" },
  angry: { mouth: "frown", brow: [-2, 9], eye: "dot" },
  sad: { mouth: "frown", brow: [4, -10], eye: "sad" },
  deadpan: { mouth: "flat", brow: [0, 0], eye: "lid" },
  panic: { mouth: "teeth", brow: [12, -9], eye: "wide" },
};

const TALK = ["closed", "small_o", "tall_o", "wide", "smile"];

/** loudness band -> one of five mouth drawings, held 2-4 frames, never the same twice running (skill 5.4) */
export function talkMouth(level: number, frame: number) {
  const band = level < 0.12 ? 0 : level < 0.35 ? 1 : level < 0.6 ? 2 : level < 0.8 ? 3 : 4;
  const hold = Math.floor(frame / 3);
  const k = band === 0 ? 0 : (band + (hold % 2)) % 5 || 1;
  return TALK[k];
}

function blinking(seed: number, frame: number) {
  if (frame < 6) return false; // never on frame 0
  const period = 90 + (seed % 25); // ~3.2 s
  const phase = (frame + (seed % period)) % period;
  return phase < 3;
}

function hair(style: string, color: string, view: View, fxIn: number) {
  let fx = fxIn;
  const r = HEAD_R, cy = HEAD_Y, hl = shade(color, 0.28), dk = shade(color, -0.25);
  const strands = (n: number, y0: number) =>
    Array.from({ length: n }, (_, i) => {
      const x = -r * 0.6 + (i * r * 1.2) / Math.max(1, n - 1) + fx * 0.3;
      return <path key={i} d={`M${x} ${y0} q${6} ${14} ${2} ${26}`} stroke={dk} strokeWidth={2.4} fill="none" />;
    });
  const HATS = ["slouch_hat", "cap", "hard_hat", "top_hat", "bowler", "beanie"];
  if (view === "back" && !HATS.includes(style)) {
    if (style === "bald") return <path d={`M${-r} ${cy} a${r} ${r} 0 0 1 ${2 * r} 0`} fill="none" stroke={shade(color, 0.1)} strokeWidth={3} opacity={0.4} />;
    return <circle cx={0} cy={cy} r={r + 2} fill={color} stroke={INK} strokeWidth={LW} />;
  }
  if (view === "back") fx = 0;
  switch (style) {
    case "bald":
      return <path d={`M${-r * 0.8} ${cy - r * 0.55} q${r * 0.8} ${-r * 0.5} ${r * 1.6} 0`} fill="none" stroke="#fff" strokeOpacity={0.5} strokeWidth={5} />;
    case "beanie":
      return (
        <g>
          <path d={`M${-r - 4} ${cy - 14} Q${-r} ${cy - r - 34} ${0} ${cy - r - 30} Q${r} ${cy - r - 34} ${r + 4} ${cy - 14} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <rect x={-r - 6} y={cy - 26} width={2 * r + 12} height={20} rx={8} fill={dk} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r * 0.5} ${cy - r - 12} q${r * 0.5} ${-10} ${r} 0`} stroke={hl} strokeWidth={6} fill="none" />
        </g>
      );
    case "long":
      return (
        <g>
          <path d={`M${-r - 8} ${cy + 70} Q${-r - 20} ${cy - r - 20} ${fx * 0.4} ${cy - r - 10} Q${r + 20} ${cy - r - 20} ${r + 8} ${cy + 70} L${r - 10} ${cy + 70} Q${r - 14} ${cy - 30} ${fx} ${cy - r + 22} Q${-r + 14} ${cy - 30} ${-r + 10} ${cy + 70} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r * 0.45} ${cy - r + 2} q${r * 0.45} ${-12} ${r * 0.9} 0`} stroke={hl} strokeWidth={6} fill="none" />
          {strands(4, cy - r + 8)}
        </g>
      );
    case "bun":
      return (
        <g>
          <circle cx={fx * 0.2} cy={cy - r - 22} r={28} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r - 2} ${cy - 6} Q${-r} ${cy - r - 14} ${fx * 0.3} ${cy - r - 6} Q${r} ${cy - r - 14} ${r + 2} ${cy - 6} Q${r * 0.5} ${cy - r * 0.55} ${fx * 0.3} ${cy - r * 0.6} Q${-r * 0.5} ${cy - r * 0.55} ${-r - 2} ${cy - 6} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r * 0.5} ${cy - r + 2} q${r * 0.5} ${-10} ${r} 0`} stroke={hl} strokeWidth={6} fill="none" />
        </g>
      );
    case "curly":
      return (
        <g>
          {Array.from({ length: 9 }, (_, i) => {
            const a = Math.PI * (1.05 + (i / 8) * 0.9);
            return <circle key={i} cx={Math.cos(a) * (r - 6) + fx * 0.2} cy={cy + Math.sin(a) * (r - 6)} r={24} fill={color} stroke={INK} strokeWidth={LW} />;
          })}
          <path d={`M${-r * 0.4} ${cy - r - 8} q${r * 0.4} ${-10} ${r * 0.8} 0`} stroke={hl} strokeWidth={5} fill="none" />
        </g>
      );
    case "slouch_hat": // brim pinned up on one side (Australian army style)
      return (
        <g>
          <path d={`M${-r - 34} ${cy - 30} Q${0} ${cy - 48} ${r + 22} ${cy - 30} L${r + 10} ${cy - 42} Q${0} ${cy - 58} ${-r - 22} ${cy - 44} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r * 0.72} ${cy - 44} Q${-r * 0.6} ${cy - r - 46} ${0} ${cy - r - 44} Q${r * 0.6} ${cy - r - 46} ${r * 0.72} ${cy - 44} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <rect x={-r * 0.72} y={cy - 62} width={r * 1.44} height={14} fill={dk} stroke={INK} strokeWidth={3} />
          <path d={`M${r * 0.55} ${cy - 46} L${r + 18} ${cy - r - 10} L${r + 30} ${cy - 40} Z`} fill={shade(color, -0.1)} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r * 0.4} ${cy - r - 34} q${r * 0.4} ${-8} ${r * 0.8} 0`} stroke={hl} strokeWidth={5} fill="none" />
        </g>
      );
    case "cap": // peaked cap
      return (
        <g>
          <path d={`M${-r - 2} ${cy - 22} Q${-r} ${cy - r - 26} ${0} ${cy - r - 24} Q${r} ${cy - r - 26} ${r + 2} ${cy - 22} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r * 0.2} ${cy - 24} Q${r * 0.7} ${cy - 30} ${r + 40} ${cy - 16} Q${r * 0.6} ${cy - 10} ${-r * 0.2} ${cy - 14} Z`} fill={dk} stroke={INK} strokeWidth={LW} />
          <circle cx={0} cy={cy - r + 2} r={8} fill="#E8C547" stroke={INK} strokeWidth={2.5} />
        </g>
      );
    case "hard_hat":
      return (
        <g>
          <path d={`M${-r - 18} ${cy - 22} L${r + 18} ${cy - 22} L${r + 14} ${cy - 34} L${-r - 14} ${cy - 34} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r + 4} ${cy - 34} Q${-r + 4} ${cy - r - 34} ${0} ${cy - r - 34} Q${r - 4} ${cy - r - 34} ${r - 4} ${cy - 34} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M0 ${cy - r - 34} v${r - 2}`} stroke={dk} strokeWidth={6} />
        </g>
      );
    case "top_hat":
      return (
        <g>
          <rect x={-r - 14} y={cy - 46} width={2 * r + 28} height={14} rx={6} fill={color} stroke={INK} strokeWidth={LW} />
          <rect x={-r * 0.62} y={cy - 46 - 104} width={r * 1.24} height={106} fill={color} stroke={INK} strokeWidth={LW} />
          <rect x={-r * 0.62} y={cy - 64} width={r * 1.24} height={14} fill="#C33631" stroke={INK} strokeWidth={3} />
        </g>
      );
    case "bowler":
      return (
        <g>
          <ellipse cx={0} cy={cy - 40} rx={r + 16} ry={12} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r * 0.75} ${cy - 40} Q${-r * 0.75} ${cy - r - 52} ${0} ${cy - r - 52} Q${r * 0.75} ${cy - r - 52} ${r * 0.75} ${cy - 40} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r * 0.4} ${cy - r - 40} q${r * 0.4} ${-6} ${r * 0.8} 0`} stroke={hl} strokeWidth={5} fill="none" />
        </g>
      );
    default: // side_part
      return (
        <g>
          <path d={`M${-r - 3} ${cy - 2} Q${-r - 4} ${cy - r - 12} ${fx * 0.3 + 10} ${cy - r - 8} Q${r + 6} ${cy - r - 10} ${r + 3} ${cy - 2} Q${r * 0.8} ${cy - r * 0.5} ${r * 0.2} ${cy - r * 0.62} Q${-r * 0.3} ${cy - r * 0.42} ${-r * 0.75} ${cy - r * 0.38} Q${-r} ${cy - r * 0.2} ${-r - 3} ${cy - 2} Z`} fill={color} stroke={INK} strokeWidth={LW} />
          <path d={`M${-r * 0.55} ${cy - r + 4} q${r * 0.55} ${-12} ${r * 1.1} 0`} stroke={hl} strokeWidth={6} fill="none" />
          {strands(3, cy - r + 6)}
        </g>
      );
  }
}

function torso(kind: string, color: string, accent: string, view: View, sx: number) {
  const rx = TORSO_RX * sx, ry = TORSO_RY, cy = TORSO_Y, dk = shade(color, -0.22), lt = shade(color, 0.2);
  const egg = `M0 ${cy - ry} C${rx * 1.05} ${cy - ry} ${rx * 1.02} ${cy + ry} 0 ${cy + ry} C${-rx * 1.02} ${cy + ry} ${-rx * 1.05} ${cy - ry} 0 ${cy - ry} Z`;
  const hem = <path d={`M${-rx * 0.86} ${cy + ry * 0.62} Q0 ${cy + ry * 0.74} ${rx * 0.86} ${cy + ry * 0.62} L${rx * 0.55} ${cy + ry * 0.94} Q0 ${cy + ry * 1.02} ${-rx * 0.55} ${cy + ry * 0.94} Z`} fill={dk} />;
  const back = view === "back";
  const layers: React.ReactNode[] = [];
  const top = cy - ry;
  if (!back) {
    if (kind === "suit" || kind === "labcoat") {
      layers.push(<path key="shirt" d={`M${-rx * 0.34} ${top + 6} L0 ${top + 74} L${rx * 0.34} ${top + 6} Z`} fill={kind === "labcoat" ? accent : "#F4F1EA"} stroke={INK} strokeWidth={3} />);
      if (kind === "suit") layers.push(<path key="tie" d={`M-7 ${top + 14} h14 l-3 10 l7 40 l-11 12 l-11 -12 l7 -40 Z`} fill={accent} stroke={INK} strokeWidth={2.5} />);
      layers.push(<path key="lapL" d={`M${-rx * 0.34} ${top + 6} L${-rx * 0.1} ${top + 70} L${-rx * 0.5} ${top + 40} Z`} fill={lt} stroke={INK} strokeWidth={3} />);
      layers.push(<path key="lapR" d={`M${rx * 0.34} ${top + 6} L${rx * 0.1} ${top + 70} L${rx * 0.5} ${top + 40} Z`} fill={lt} stroke={INK} strokeWidth={3} />);
      layers.push(<circle key="b1" cx={rx * 0.06} cy={top + 96} r={4.5} fill={INK} />, <circle key="b2" cx={rx * 0.06} cy={top + 120} r={4.5} fill={INK} />);
      if (kind === "labcoat") layers.push(<rect key="pk" x={rx * 0.3} y={top + 70} width={rx * 0.42} height={24} rx={3} fill="none" stroke={shade(color, -0.3)} strokeWidth={3} />);
    } else if (kind === "uniform") {
      layers.push(<path key="col" d={`M${-rx * 0.42} ${top + 4} L0 ${top + 34} L${rx * 0.42} ${top + 4}`} fill="none" stroke={dk} strokeWidth={8} />);
      layers.push(<rect key="pk1" x={-rx * 0.72} y={top + 44} width={rx * 0.5} height={30} rx={4} fill={lt} stroke={INK} strokeWidth={3} />);
      layers.push(<rect key="pk2" x={rx * 0.22} y={top + 44} width={rx * 0.5} height={30} rx={4} fill={lt} stroke={INK} strokeWidth={3} />);
      layers.push(<rect key="belt" x={-rx * 0.98} y={cy + ry * 0.28} width={rx * 1.96} height={16} fill={accent} stroke={INK} strokeWidth={3} />);
      layers.push(<rect key="bk" x={-12} y={cy + ry * 0.28 - 2} width={24} height={20} fill="#E8C547" stroke={INK} strokeWidth={3} />);
      [0, 1, 2].forEach((i) => layers.push(<circle key={"b" + i} cx={0} cy={top + 50 + i * 26} r={4} fill="#E8C547" stroke={INK} strokeWidth={1.5} />));
    } else if (kind === "overalls") {
      layers.push(<path key="bib" d={`M${-rx * 0.5} ${top + 46} h${rx} v${ry * 0.9} h${-rx} Z`} fill={accent} stroke={INK} strokeWidth={3} />);
      layers.push(<path key="st" d={`M${-rx * 0.5} ${top + 46} L${-rx * 0.62} ${top + 4} M${rx * 0.5} ${top + 46} L${rx * 0.62} ${top + 4}`} stroke={accent} strokeWidth={10} />);
      layers.push(<circle key="b1" cx={-rx * 0.38} cy={top + 56} r={5} fill="#E8C547" stroke={INK} strokeWidth={2} />, <circle key="b2" cx={rx * 0.38} cy={top + 56} r={5} fill="#E8C547" stroke={INK} strokeWidth={2} />);
    } else if (kind === "dress") {
      layers.push(<path key="col" d={`M${-rx * 0.35} ${top + 6} Q0 ${top + 34} ${rx * 0.35} ${top + 6}`} fill="#F4F1EA" stroke={INK} strokeWidth={3} />);
      layers.push(<path key="sash" d={`M${-rx * 0.96} ${cy + 6} Q0 ${cy + 20} ${rx * 0.96} ${cy + 6}`} stroke={accent} strokeWidth={12} fill="none" />);
    } else if (kind === "jacket") {
      layers.push(<path key="zip" d={`M0 ${top + 10} V${cy + ry * 0.9}`} stroke={shade(color, -0.4)} strokeWidth={3} strokeDasharray="5 4" />);
      layers.push(<path key="col" d={`M${-rx * 0.45} ${top + 2} L${-rx * 0.1} ${top + 26} M${rx * 0.45} ${top + 2} L${rx * 0.1} ${top + 26}`} stroke={INK} strokeWidth={3} />);
      layers.push(<path key="sh1" d={`M${-rx * 0.6} ${top + 40} q6 30 -2 60`} stroke="#fff" strokeOpacity={0.6} strokeWidth={3} fill="none" />);
      layers.push(<rect key="pk" x={-rx * 0.7} y={cy + 10} width={rx * 0.45} height={8} fill={dk} />);
    } else {
      // sweater (default): collar + soft fold lines
      layers.push(<path key="col" d={`M${-rx * 0.38} ${top + 6} Q0 ${top + 28} ${rx * 0.38} ${top + 6}`} fill={accent} stroke={INK} strokeWidth={3} />);
      layers.push(<path key="f1" d={`M${-rx * 0.5} ${cy - 10} q12 8 24 0 M${rx * 0.2} ${cy + 20} q12 8 24 0`} stroke={dk} strokeWidth={2.5} fill="none" />);
    }
  }
  return (
    <g>
      <path d={egg} fill={color} stroke={INK} strokeWidth={LW} />
      {hem}
      {layers}
      {/* soft shade on the side away from the key light, rim on the lit side */}
      <path d={`M${rx * 0.4} ${top + 10} C${rx * 1.0} ${top + 30} ${rx * 0.95} ${cy + ry * 0.7} ${rx * 0.3} ${cy + ry * 0.95}`} stroke={dk} strokeOpacity={0.45} strokeWidth={10} fill="none" />
      <path d={`M${-rx * 0.72} ${top + 26} Q${-rx * 0.95} ${cy} ${-rx * 0.7} ${cy + ry * 0.5}`} stroke="#fff" strokeOpacity={0.35} strokeWidth={4} fill="none" />
      <path d={egg} fill="none" stroke={INK} strokeWidth={LW} />
    </g>
  );
}

type Arm = { sx: number; sy: number; ex: number; ey: number; hx: number; hy: number };

function arms(pose: Pose, frame: number, talking: boolean, walk: number | null): Arm[] {
  const L = { sx: -TORSO_RX * 0.86, sy: SHOULDER_Y + 12 }, R = { sx: TORSO_RX * 0.86, sy: SHOULDER_Y + 12 };
  const wob = talking ? Math.sin(frame / 4.2) * 10 : 0;
  const mk = (s: { sx: number; sy: number }, ex: number, ey: number, hx: number, hy: number): Arm => ({ ...s, ex: s.sx + ex, ey: s.sy + ey, hx: s.sx + hx, hy: s.sy + hy });
  switch (pose) {
    case "pointing": return [mk(L, -16, 52, -20, 98), mk(R, 64, -14, 128, -40)];
    case "holding": return [mk(L, -10, 56, 40, 62), mk(R, 10, 56, -40, 62)];
    case "cheering": return [mk(L, -40, -60, -60, -124), mk(R, 40, -60, 60, -124)];
    case "shrugging": return [mk(L, -46, 34, -86, 0), mk(R, 46, 34, 86, 0)];
    case "talking": return [mk(L, -16, 52, -20, 98), mk(R, 44, 40, 82 + wob, -6 - wob)];
    case "walking":
    case "running": {
      const a = Math.sin((walk ?? 0) * Math.PI * 2) * (pose === "running" ? 48 : 30);
      return [mk(L, -10 + a * 0.6, 50, -8 + a, 96), mk(R, 10 - a * 0.6, 50, 8 - a, 96)];
    }
    default: return [mk(L, -14, 52, -16, 100), mk(R, 14, 52, 16, 100)];
  }
}

export const Character: React.FC<Props> = ({ who, frame, expr, pose, view, mirror, talkLevel, walkPhase, holdKind, renderHeld }) => {
  const seed = hashStr(who.id);
  const breath = Math.sin(((frame + (seed % 60)) / 30) * Math.PI * 2 / 3.4) * 2.2;
  const blink = blinking(seed, frame);
  const e = EXPR[expr] ?? EXPR.neutral;
  const talking = talkLevel !== null && talkLevel !== undefined;
  const walk = walkPhase ?? null;
  const tilt = talking ? Math.sin(frame / 9) * 6 : 0;
  const fx = view === "front" || view === "back" ? 0 : view === "three_quarter" ? 20 : 40; // face shift toward facing
  const sx = view === "side" ? 0.78 : view === "three_quarter" ? 0.92 : 1;
  const lean = pose === "running" ? 8 : pose === "walking" ? 3 : 0;
  const legA = walk !== null ? Math.sin(walk * Math.PI * 2) * (pose === "running" ? 26 : 16) : 0;
  const mouthKind = talking ? talkMouth(talkLevel as number, frame) : e.mouth;
  const m = mouthPath(mouthKind, fx * 1.1, 34);
  const eyeY = HEAD_Y - 6 - (e.eye === "up" ? 4 : 0);
  const eyeGap = view === "front" ? 27 : view === "three_quarter" ? 22 : 0;
  const skin = who.skin;
  const outfit = who.outfit;

  const eye = (cx: number, key: string, small = false) => {
    if (blink) return <path key={key} d={`M${cx - 8} ${eyeY} h16`} stroke={INK} strokeWidth={4} strokeLinecap="round" />;
    if (e.eye === "wide") return <g key={key}><circle cx={cx} cy={eyeY} r={small ? 11 : 14} fill="#fff" stroke={INK} strokeWidth={3} /><circle cx={cx + 2} cy={eyeY} r={5} fill={INK} /></g>;
    if (e.eye === "lid") return <g key={key}><ellipse cx={cx} cy={eyeY + 2} rx={7} ry={7} fill={INK} /><rect x={cx - 10} y={eyeY - 9} width={20} height={9} fill={skin} /><path d={`M${cx - 10} ${eyeY} h20`} stroke={INK} strokeWidth={3} /></g>;
    if (e.eye === "sad") return <ellipse key={key} cx={cx} cy={eyeY + 3} rx={6.5} ry={9} fill={INK} />;
    return <ellipse key={key} cx={cx} cy={eyeY} rx={small ? 6 : 7.5} ry={small ? 9 : 11.5} fill={INK} />;
  };
  const brow = (cx: number, side: number, key: string) => {
    const [lift, t] = e.brow;
    const y = eyeY - 24 - lift;
    const inner = cx - side * 12, outer = cx + side * 12;
    return <path key={key} d={`M${outer} ${y - t * 0.3} L${inner} ${y + t}`} stroke={INK} strokeWidth={4} strokeLinecap="round" />;
  };

  const armList = arms(pose, frame, talking, walk);
  const armEls = armList.map((a, i) => (
    <g key={i}>
      <path d={`M${a.sx} ${a.sy} L${a.ex} ${a.ey} L${a.hx} ${a.hy}`} stroke={INK} strokeWidth={LW + 0.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={a.hx} cy={a.hy} r={11} fill={skin} stroke={INK} strokeWidth={LW - 0.5} />
    </g>
  ));
  const hidden = view === "back";

  return (
    <g transform={`${mirror ? "scale(-1,1)" : ""} translate(0 ${-Math.abs(breath) * 0.4}) rotate(${lean} 0 -100)`}>
      {/* legs: two straight dark strokes; shoes small dark ovals */}
      <path d={`M-22 ${HIP_Y} L${-22 - legA} -6 M22 ${HIP_Y} L${22 + legA} -6`} stroke={INK} strokeWidth={LW + 3} strokeLinecap="round" />
      <ellipse cx={-26 - legA} cy={-4} rx={16} ry={8} fill={INK} />
      <ellipse cx={26 + legA} cy={-4} rx={16} ry={8} fill={INK} />
      {hidden && armEls}
      <g transform={`translate(0 ${breath * 0.5})`}>{torso(outfit.kind, outfit.color, outfit.accent, view, sx)}</g>
      {!hidden && pose !== "holding" && armEls}
      <g transform={`translate(0 ${breath}) rotate(${tilt} 0 ${HEAD_Y + 60})`}>
        {who.hair.style === "long" && view !== "back" && <path d={`M${-HEAD_R - 6} ${HEAD_Y} Q${-HEAD_R - 14} ${HEAD_Y + 110} ${-HEAD_R + 10} ${HEAD_Y + 120} L${HEAD_R - 10} ${HEAD_Y + 120} Q${HEAD_R + 14} ${HEAD_Y + 110} ${HEAD_R + 6} ${HEAD_Y} Z`} fill={shade(who.hair.color, -0.15)} stroke={INK} strokeWidth={LW} />}
        <circle cx={0} cy={HEAD_Y} r={HEAD_R} fill={skin} stroke={INK} strokeWidth={LW} />
        <circle cx={0} cy={HEAD_Y} r={HEAD_R - 2} fill="url(#headVig)" />
        <path d={`M${HEAD_R * 0.35} ${HEAD_Y - HEAD_R * 0.9} A${HEAD_R} ${HEAD_R} 0 0 1 ${HEAD_R * 0.35} ${HEAD_Y + HEAD_R * 0.9} A${HEAD_R * 0.86} ${HEAD_R * 0.92} 0 0 0 ${HEAD_R * 0.35} ${HEAD_Y - HEAD_R * 0.9} Z`} fill={shade(skin, -0.16)} opacity={0.6} />
        <path d={`M${-HEAD_R * 0.86} ${HEAD_Y - HEAD_R * 0.3} A${HEAD_R * 0.9} ${HEAD_R * 0.9} 0 0 1 ${-HEAD_R * 0.3} ${HEAD_Y - HEAD_R * 0.84}`} stroke="#fff" strokeOpacity={0.7} strokeWidth={4} fill="none" strokeLinecap="round" />
        {!hidden && (
          <g>
            {view === "side" ? [eye(fx + 8, "e1")] : [eye(fx * 1.1 - eyeGap, "e1", view === "three_quarter"), eye(fx * 1.1 + eyeGap, "e2")]}
            {view === "side" ? [brow(fx + 8, 1, "b1")] : [brow(fx * 1.1 - eyeGap, -1, "b1"), brow(fx * 1.1 + eyeGap, 1, "b2")]}
            <path d={m.d} fill={m.fill ? "#3A1712" : "none"} stroke={INK} strokeWidth={3.5} strokeLinecap="round" strokeLinejoin="round" />
            {mouthKind === "teeth" && <path d={`M${fx * 1.1 - 18} ${HEAD_Y + 35} h40 M${fx * 1.1 - 6} ${HEAD_Y + 28} v14 M${fx * 1.1 + 8} ${HEAD_Y + 28} v14`} stroke="#fff" strokeWidth={2.5} />}
            {(expr === "happy" || expr === "surprised") && <g opacity={0.35}><ellipse cx={fx - 44} cy={HEAD_Y + 20} rx={13} ry={7} fill="#E0786A" /><ellipse cx={fx + 48} cy={HEAD_Y + 20} rx={13} ry={7} fill="#E0786A" /></g>}
            {who.glasses && who.glasses !== "none" && (
              who.glasses === "round"
                ? <g fill="none" stroke={INK} strokeWidth={3.5}><circle cx={fx * 1.1 - eyeGap} cy={eyeY} r={19} /><circle cx={fx * 1.1 + eyeGap} cy={eyeY} r={19} /><path d={`M${fx * 1.1 - eyeGap + 19} ${eyeY} h${2 * eyeGap - 38}`} /></g>
                : <g fill="none" stroke={INK} strokeWidth={3.5}><rect x={fx * 1.1 - eyeGap - 20} y={eyeY - 14} width={40} height={28} rx={4} /><rect x={fx * 1.1 + eyeGap - 20} y={eyeY - 14} width={40} height={28} rx={4} /></g>
            )}
          </g>
        )}
        {hair(who.hair.style, who.hair.color, view, fx)}
        {/* emotion symbols */}
        {(expr === "panic" || expr === "concerned") && <path d={`M${-HEAD_R - 8} ${HEAD_Y - 30} q-12 22 0 30 q12 -8 0 -30Z`} fill="#8FD3F0" stroke={INK} strokeWidth={3} transform={`translate(0 ${(frame % 30) * 0.6})`} />}
        {expr === "angry" && <g transform={`translate(${HEAD_R * 0.75} ${HEAD_Y - HEAD_R * 0.8})`} stroke="#C33631" strokeWidth={5} fill="none" strokeLinecap="round"><path d="M-14 -4 q10 0 10 -10 M4 -14 q0 10 10 10 M14 4 q-10 0 -10 10 M-4 14 q0 -10 -10 -10" /></g>}
        {expr === "happy" && frame % 40 < 24 && <g fill="#F7E26B" stroke={INK} strokeWidth={2}><path d={`M${HEAD_R + 16} ${HEAD_Y - 60} l5 12 l12 5 l-12 5 l-5 12 l-5 -12 l-12 -5 l12 -5 Z`} /></g>}
      </g>
      {!hidden && pose === "holding" && (
        <g>
          {holdKind && renderHeld && <g transform={`translate(0 ${SHOULDER_Y + 64})`}>{renderHeld(holdKind)}</g>}
          {armEls}
        </g>
      )}
    </g>
  );
};

/** defs every scene needs once (head vignette) */
export const RigDefs: React.FC = () => (
  <defs>
    <radialGradient id="headVig" cx="0.42" cy="0.4" r="0.62">
      <stop offset="0.6" stopColor="#000" stopOpacity={0} />
      <stop offset="1" stopColor="#000" stopOpacity={0.16} />
    </radialGradient>
  </defs>
);

export function viewFor(facing: string, profile: boolean): { view: View; mirror: boolean } {
  if (facing === "front") return { view: "front", mirror: false };
  if (facing === "back") return { view: "back", mirror: false };
  return { view: profile ? "side" : "three_quarter", mirror: facing === "left" };
}
