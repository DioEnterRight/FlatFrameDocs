// Drawn animals in the same hand as the cast: ink outline, flat fills, oval eyes, one highlight. Feet at (0,0),
// facing right. Goofy by design: the facts stay serious, the scenery can be absurd (brief, section 3).
import React from "react";
import type { Expr } from "../types";
import { INK, shade } from "../theme";

type P = { kind: string; frame: number; expr: Expr; walk: number | null; color?: string };

const eyeFor = (expr: Expr, x: number, y: number, r = 9) =>
  expr === "surprised" || expr === "panic" ? (
    <g><circle cx={x} cy={y} r={r * 1.5} fill="#fff" stroke={INK} strokeWidth={3} /><circle cx={x + 3} cy={y} r={r * 0.6} fill={INK} /></g>
  ) : expr === "deadpan" ? (
    <g><circle cx={x} cy={y} r={r} fill="#fff" stroke={INK} strokeWidth={3} /><circle cx={x + 2} cy={y + 2} r={r * 0.5} fill={INK} /><path d={`M${x - r} ${y - 1} h${2 * r}`} stroke={INK} strokeWidth={3} /></g>
  ) : expr === "angry" ? (
    <g><circle cx={x} cy={y} r={r} fill="#fff" stroke={INK} strokeWidth={3} /><circle cx={x + 2} cy={y + 1} r={r * 0.5} fill={INK} /><path d={`M${x - r - 2} ${y - r - 4} L${x + r} ${y - r + 4}`} stroke={INK} strokeWidth={4} /></g>
  ) : (
    <g><circle cx={x} cy={y} r={r} fill="#fff" stroke={INK} strokeWidth={3} /><circle cx={x + 2} cy={y} r={r * 0.5} fill={INK} /></g>
  );

function legs(walk: number | null, x1: number, x2: number, hip: number, len: number, w: number, knee = false) {
  const a = walk !== null ? Math.sin(walk * Math.PI * 2) * 0.45 : 0;
  const leg = (x: number, ph: number) => {
    const fx = x + Math.sin(ph) * len * 0.5;
    const kx = x + Math.sin(ph) * len * 0.18 + (knee ? -16 : 0);
    return <path d={`M${x} ${hip} L${kx} ${hip + len * 0.5} L${fx} ${-4}`} stroke={INK} strokeWidth={w} fill="none" strokeLinecap="round" strokeLinejoin="round" />;
  };
  return <g>{leg(x1, a)}{leg(x2, -a)}</g>;
}

export const Creature: React.FC<P> = ({ kind, frame, expr, walk, color }) => {
  const bob = walk !== null ? Math.abs(Math.sin(walk * Math.PI * 2)) * -10 : Math.sin(frame / 14) * 2;
  const peck = walk === null ? Math.sin(frame / 17) * 6 : 0;
  switch (kind) {
    case "big_bird": { // emu / ostrich style: shaggy body, long neck, tiny head, long legs
      const c = color ?? "#6B5E4E";
      const feathers = Array.from({ length: 9 }, (_, i) => <path key={i} d={`M${-70 + i * 18} ${-270 + (i % 2) * 10} q6 26 -4 52`} stroke={shade(c, -0.35)} strokeWidth={3} fill="none" />);
      return (
        <g transform={`translate(0 ${bob})`}>
          {legs(walk, -18, 18, -190, 190, 9, true)}
          <path d={`M30 -150 L30 -150`} />
          <ellipse cx={-10} cy={-250} rx={105} ry={78} fill={c} stroke={INK} strokeWidth={4.5} />
          {feathers}
          <path d={`M-110 -250 q-30 10 -30 50 q20 -14 40 -10`} fill={c} stroke={INK} strokeWidth={4} />
          <path d={`M60 -290 Q${96 + peck} -360 ${80 + peck} -430`} stroke={shade(c, 0.15)} strokeWidth={30} fill="none" strokeLinecap="round" />
          <path d={`M60 -290 Q${96 + peck} -360 ${80 + peck} -430`} stroke={INK} strokeWidth={4} fill="none" opacity={0.5} />
          <g transform={`translate(${80 + peck} -440)`}>
            <ellipse cx={0} cy={0} rx={34} ry={28} fill={shade(c, 0.2)} stroke={INK} strokeWidth={4} />
            <path d="M26 -2 L64 6 L26 14 Z" fill="#3B3A36" stroke={INK} strokeWidth={3} />
            {eyeFor(expr, 8, -6, 8)}
            <path d="M-20 -26 q4 -16 12 -6 q4 -14 12 -2" stroke={INK} strokeWidth={3} fill="none" />
          </g>
        </g>
      );
    }
    case "bird": {
      const c = color ?? "#4C7FA8";
      return (
        <g transform={`translate(0 ${bob})`}>
          {legs(walk, -8, 8, -40, 40, 4)}
          <ellipse cx={0} cy={-70} rx={46} ry={36} fill={c} stroke={INK} strokeWidth={4} />
          <path d="M-40 -72 l-30 -14 l8 22 Z" fill={shade(c, -0.2)} stroke={INK} strokeWidth={3} />
          <circle cx={30} cy={-104} r={26} fill={c} stroke={INK} strokeWidth={4} />
          <path d="M52 -106 l22 6 l-22 8 Z" fill="#E8A33D" stroke={INK} strokeWidth={3} />
          {eyeFor(expr, 36, -110, 6)}
        </g>
      );
    }
    case "dog": {
      const c = color ?? "#B07A45";
      return (
        <g transform={`translate(0 ${bob})`}>
          {legs(walk, -60, -30, -80, 80, 10)}
          {legs(walk === null ? null : walk + 0.5, 40, 66, -80, 80, 10)}
          <ellipse cx={0} cy={-112} rx={100} ry={50} fill={c} stroke={INK} strokeWidth={4.5} />
          <path d={`M-96 -120 q-40 ${-30 + Math.sin(frame / 4) * 10} -50 -60`} stroke={INK} strokeWidth={8} fill="none" strokeLinecap="round" />
          <circle cx={100} cy={-170} r={52} fill={c} stroke={INK} strokeWidth={4.5} />
          <ellipse cx={140} cy={-158} rx={30} ry={20} fill={shade(c, 0.25)} stroke={INK} strokeWidth={4} />
          <circle cx={166} cy={-162} r={8} fill={INK} />
          <path d="M70 -210 q-24 10 -18 60 q16 -20 30 -36 Z" fill={shade(c, -0.3)} stroke={INK} strokeWidth={4} />
          {eyeFor(expr, 112, -184, 8)}
        </g>
      );
    }
    case "cat": {
      const c = color ?? "#5B5550";
      return (
        <g transform={`translate(0 ${bob})`}>
          {legs(walk, -40, -20, -60, 60, 8)}
          {legs(walk === null ? null : walk + 0.5, 30, 48, -60, 60, 8)}
          <ellipse cx={0} cy={-88} rx={74} ry={40} fill={c} stroke={INK} strokeWidth={4} />
          <path d={`M-70 -96 Q-120 ${-130 + Math.sin(frame / 8) * 14} -100 -190`} stroke={c} strokeWidth={14} fill="none" strokeLinecap="round" />
          <circle cx={72} cy={-138} r={42} fill={c} stroke={INK} strokeWidth={4} />
          <path d="M44 -168 l8 -36 l22 26 Z M86 -170 l22 -30 l6 34 Z" fill={c} stroke={INK} strokeWidth={4} />
          {eyeFor(expr, 64, -142, 7)}{eyeFor(expr, 92, -142, 7)}
          <path d="M70 -122 q8 6 16 0" stroke={INK} strokeWidth={3} fill="none" />
        </g>
      );
    }
    case "rat": {
      const c = color ?? "#8A8580";
      return (
        <g transform={`translate(0 ${bob * 0.5})`}>
          <ellipse cx={0} cy={-34} rx={58} ry={30} fill={c} stroke={INK} strokeWidth={4} />
          <path d={`M-56 -30 q-60 ${Math.sin(frame / 6) * 12} -90 -6`} stroke="#D99A9A" strokeWidth={6} fill="none" strokeLinecap="round" />
          <path d="M44 -50 L92 -30 L44 -14 Z" fill={c} stroke={INK} strokeWidth={4} />
          <circle cx={40} cy={-60} r={16} fill="#D99A9A" stroke={INK} strokeWidth={3} />
          {eyeFor(expr, 58, -40, 5)}
          <circle cx={92} cy={-30} r={5} fill={INK} />
        </g>
      );
    }
    case "fish": {
      const c = color ?? "#E07A3C";
      const s = Math.sin(frame / 5) * 8;
      return (
        <g transform={`translate(0 ${-60 + Math.sin(frame / 12) * 6})`}>
          <path d={`M-70 0 l-50 ${-36 + s} v${72} Z`} fill={shade(c, -0.15)} stroke={INK} strokeWidth={4} />
          <ellipse cx={0} cy={0} rx={80} ry={44} fill={c} stroke={INK} strokeWidth={4} />
          <path d="M-10 -40 q20 -30 40 -2" fill={shade(c, -0.15)} stroke={INK} strokeWidth={3} />
          {eyeFor(expr, 44, -8, 8)}
          <path d="M70 12 q-8 6 -14 0" stroke={INK} strokeWidth={3} fill="none" />
        </g>
      );
    }
    default:
      return <circle cx={0} cy={-60} r={60} fill={color ?? "#999"} stroke={INK} strokeWidth={4} />;
  }
};

export const CREATURES = ["big_bird", "bird", "dog", "cat", "rat", "fish"];
export const creatureHeight: Record<string, number> = { big_bird: 470, bird: 130, dog: 230, cat: 210, rat: 80, fish: 120 };
