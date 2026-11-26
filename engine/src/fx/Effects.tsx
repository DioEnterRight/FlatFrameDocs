// Environmental effects (skill 5.4a): selective, subtle, drawn in the same cartoon hand, seeded, frame-driven.
// At most one main and one quiet background effect per scene. Accent-coloured particles only near the hero object.
import React from "react";
import { H, INK, W, WORLD_W, rng } from "../theme";

type P = { kind: string; f: number; seed: number; strength?: number; inWorld?: boolean };

export const Effect: React.FC<P> = ({ kind, f, seed, strength = 1, inWorld }) => {
  const r = rng(seed);
  const width = inWorld ? WORLD_W : W;
  const fade = Math.min(1, f / 15); // fade in over half a second, never pop on
  const n = (k: number) => Math.round(k * strength);
  switch (kind) {
    case "dust": { // motes drifting through a light beam
      return <g opacity={0.75 * fade}>{Array.from({ length: n(26) }, (_, i) => {
        const x0 = 200 + r() * (width - 400), y0 = 300 + r() * 900, sp = 0.2 + r() * 0.4;
        const x = x0 + Math.sin((f + i * 20) / 40) * 30, y = ((y0 - f * sp) % 1000 + 1000) % 1000 + 250;
        return <circle key={i} cx={x} cy={y} r={2 + r() * 3} fill="#FFF6DA" opacity={0.5 + 0.5 * Math.sin((f + i * 11) / 9)} />;
      })}</g>;
    }
    case "rain":
      return <g opacity={0.55 * fade} stroke="#C7D6E6" strokeWidth={3} strokeLinecap="round">{Array.from({ length: n(70) }, (_, i) => {
        const x = (r() * (width + 200) + f * 6) % (width + 200) - 100, y = ((r() * H + f * 38) % (H + 100)) - 50;
        return <path key={i} d={`M${x} ${y} l-8 32`} />;
      })}</g>;
    case "snow":
      return <g opacity={0.85 * fade} fill="#fff">{Array.from({ length: n(50) }, (_, i) => {
        const x = (r() * width + Math.sin((f + i * 30) / 30) * 30), y = ((r() * H + f * (2 + r() * 2)) % H);
        return <circle key={i} cx={x} cy={y} r={3 + r() * 4} />;
      })}</g>;
    case "smoke": { // soft rounded puffs rising
      const x0 = 300 + r() * (width - 600);
      return <g opacity={0.55 * fade}>{Array.from({ length: n(9) }, (_, i) => {
        const age = ((f + i * 22) % 200) / 200;
        return <circle key={i} cx={x0 + Math.sin(age * 6 + i) * 40 + age * 120} cy={1250 - age * 900} r={40 + age * 90} fill="#BDB7AE" stroke={INK} strokeWidth={2} opacity={1 - age} />;
      })}</g>;
    }
    case "steam":
      return <g opacity={0.5 * fade}>{Array.from({ length: n(6) }, (_, i) => {
        const age = ((f + i * 25) % 150) / 150;
        return <ellipse key={i} cx={width / 2 + Math.sin(age * 8 + i) * 30} cy={1250 - age * 500} rx={30 + age * 50} ry={20 + age * 30} fill="#EDEDED" opacity={1 - age} />;
      })}</g>;
    case "mist":
      return <g opacity={0.45 * fade}>{[0, 1, 2].map((i) => <rect key={i} x={-200 + ((f * (0.6 + i * 0.3)) % 400)} y={1380 + i * 110} width={width + 400} height={70} rx={35} fill="#D9DEE3" opacity={0.6 - i * 0.15} />)}</g>;
    case "sparks":
      return <g fill="#F7C548" opacity={fade}>{Array.from({ length: n(18) }, (_, i) => {
        const age = ((f + i * 7) % 24) / 24, a = r() * Math.PI - Math.PI;
        const x = width / 2 + Math.cos(a) * age * 220, y = 1200 + Math.sin(a) * age * 200 + age * age * 160;
        return <rect key={i} x={x} y={y} width={8} height={3} transform={`rotate(${a * 57} ${x} ${y})`} opacity={1 - age} />;
      })}</g>;
    case "leaves":
      return <g opacity={0.9 * fade}>{Array.from({ length: n(12) }, (_, i) => {
        const x = ((r() * width + f * (3 + r() * 3)) % (width + 100)) - 50, y = 300 + ((r() * 900 + f * 2) % 1100);
        return <path key={i} d={`M${x} ${y} q10 -10 20 0 q-10 10 -20 0`} fill={i % 2 ? "#C9853A" : "#9DAA4A"} stroke={INK} strokeWidth={2} transform={`rotate(${(f * 4 + i * 40) % 360} ${x + 10} ${y})`} />;
      })}</g>;
    case "papers":
      return <g opacity={fade}>{Array.from({ length: n(7) }, (_, i) => {
        const x = ((r() * width + f * (4 + i)) % (width + 200)) - 100, y = 500 + r() * 700 + Math.sin((f + i * 30) / 12) * 40;
        return <rect key={i} x={x} y={y} width={60} height={44} fill="#F4F1EA" stroke={INK} strokeWidth={3} transform={`rotate(${Math.sin((f + i * 17) / 10) * 40} ${x + 30} ${y + 22})`} />;
      })}</g>;
    case "flicker": {
      const on = Math.sin(f * 1.7 + seed) + Math.sin(f * 0.37) > -0.6;
      return <rect x={0} y={0} width={width} height={H} fill="#000" opacity={on ? 0 : 0.18} />;
    }
    case "glow_particles": // accent particles around the hero object only
      return <g opacity={0.8 * fade}>{Array.from({ length: n(16) }, (_, i) => {
        const a = r() * Math.PI * 2, rad = 90 + r() * 120 + Math.sin((f + i * 9) / 14) * 12;
        return <circle key={i} cx={Math.cos(a + f / 90) * rad} cy={Math.sin(a + f / 90) * rad} r={4 + r() * 3} fill="#B8F07A" />;
      })}</g>;
    case "screen_glow":
      return <rect x={0} y={0} width={width} height={H} fill="#8FD3C9" opacity={0.06 + 0.03 * Math.sin(f / 5)} style={{ mixBlendMode: "screen" }} />;
    default:
      return null;
  }
};

export const FX_KINDS = ["dust", "rain", "snow", "smoke", "steam", "mist", "sparks", "leaves", "papers", "flicker", "screen_glow"];
