// Back layers of a set: wall or sky, windows with a view, wall items, drawn light (discs, pools, bands), far scenery.
import React from "react";
import type { SetSpec } from "../types";
import { FLOOR_Y, GRADES, H, INK, PAL, WORLD_W, rng, shade } from "../theme";
import { propDef, Lettering } from "../props/library";
import { Pattern } from "./patterns";
import type { Kit } from "./kits";

const Cloud: React.FC<{ x: number; y: number; s: number; c: string }> = ({ x, y, s, c }) => (
  <g transform={`translate(${x} ${y}) scale(${s})`} fill={c} stroke={INK} strokeWidth={3}>
    <path d="M-90 20 Q-100 -20 -60 -24 Q-50 -64 -6 -56 Q20 -86 56 -56 Q100 -60 96 -16 Q120 10 90 24 Z" />
  </g>
);

function windowView(view: string, w: number, h: number, f: number, night: boolean) {
  const sky = night ? "#1A2751" : view === "sea" ? "#9CC3D5" : "#A9CFE0";
  return (
    <g>
      <rect x={0} y={0} width={w} height={h} fill={sky} />
      {!night && <Cloud x={w * 0.3 + (f * 0.15) % (w * 0.6)} y={h * 0.25} s={0.45} c="#F4F1EA" />}
      {night && <circle cx={w * 0.72} cy={h * 0.24} r={26} fill="#F3EBC8" />}
      {(view === "city" || view === "night") && Array.from({ length: 5 }, (_, i) => (
        <g key={i}>
          <rect x={i * (w / 5) + 6} y={h * (0.42 + (i % 3) * 0.08)} width={w / 5 - 10} height={h} fill={night ? "#2A3558" : "#8C989A"} stroke={INK} strokeWidth={3} />
          {Array.from({ length: 4 }, (_, k) => <rect key={k} x={i * (w / 5) + 16} y={h * (0.5 + (i % 3) * 0.08) + k * 34} width={14} height={18} fill={night ? ((i + k + Math.floor(f / 45)) % 3 ? "#F3D36B" : "#2A3558") : "#D9E6E3"} />)}
        </g>
      ))}
      {view === "street" && <g><rect x={0} y={h * 0.7} width={w} height={h * 0.3} fill="#7C8F4E" /><circle cx={w * 0.3} cy={h * 0.62} r={h * 0.14} fill="#5E8A47" stroke={INK} strokeWidth={3} /></g>}
      {view === "field" && <path d={`M0 ${h * 0.65} Q${w * 0.5} ${h * 0.55} ${w} ${h * 0.68} V${h} H0 Z`} fill="#9DAA4A" stroke={INK} strokeWidth={3} />}
      {view === "sea" && <rect x={0} y={h * 0.62} width={w} height={h * 0.38} fill="#4F8CA8" />}
    </g>
  );
}

export const Backdrop: React.FC<{ set: SetSpec; kit: Kit; f: number; uid: string }> = ({ set, kit, f, uid }) => {
  const g = GRADES[set.grade] ?? GRADES.day;
  const r = rng(1000 + set.variant * 7919);
  const night = set.grade === "night" || set.grade === "dark";
  if (!kit.outdoor) {
    const wall = kit.wall ?? PAL.beige;
    const winX = 120 + r() * 380, winW = 360, winY = 300, winH = 520;
    const decor = [...kit.decor];
    if (set.variant % 2) decor.reverse();
    const slots = [[0.62, 520], [0.85, 760], [0.16, 640], [0.4, 980], [0.74, 1000]];
    return (
      <g>
        <defs><Pattern id={`wall${uid}`} kind={set.wall ?? kit.wallPattern ?? "panels"} fill={wall} /></defs>
        <rect x={-300} y={-300} width={WORLD_W + 600} height={FLOOR_Y + 600} fill={`url(#wall${uid})`} />
        <rect x={-300} y={-300} width={WORLD_W + 600} height={420} fill={shade(wall, -0.25)} />
        <rect x={-300} y={110} width={WORLD_W + 600} height={18} fill={shade(wall, 0.15)} stroke={INK} strokeWidth={4} />
        <rect x={-300} y={FLOOR_Y - 40} width={WORLD_W + 600} height={40} fill={shade(wall, -0.3)} stroke={INK} strokeWidth={4} />
        {kit.window && (
          <g transform={`translate(${winX} ${winY})`}>
            {windowView(night ? "night" : kit.window, winW, winH, f, night)}
            <rect x={0} y={0} width={winW} height={winH} fill="none" stroke={INK} strokeWidth={10} />
            <path d={`M${winW / 2} 0 V${winH} M0 ${winH / 2} H${winW}`} stroke={shade(wall, -0.4)} strokeWidth={9} />
            <path d={`M-30 -20 Q${-10 + Math.sin(f / 20) * 6} ${winH * 0.5} -30 ${winH + 30} L10 ${winH + 30} Q${24 + Math.sin(f / 20) * 6} ${winH * 0.5} 10 -20 Z`} fill={PAL.red} stroke={INK} strokeWidth={4} />
            <path d={`M${winW + 30} -20 Q${winW + 10 + Math.sin(f / 23) * 6} ${winH * 0.5} ${winW + 30} ${winH + 30} L${winW - 10} ${winH + 30} Q${winW - 24 + Math.sin(f / 23) * 6} ${winH * 0.5} ${winW - 10} -20 Z`} fill={PAL.red} stroke={INK} strokeWidth={4} />
          </g>
        )}
        {kit.light === "window_bands" && kit.window && !night && [0, 1, 2].map((i) => (
          <path key={i} d={`M${winX + winW + 40 + i * 120} ${winY + 40} l90 0 l220 ${FLOOR_Y - winY - 80} l-90 0 Z`} fill="#FFF3C9" opacity={0.16} />
        ))}
        {decor.slice(0, 5).map((k, i) => {
          const [fx, y] = slots[i];
          const x = fx * WORLD_W;
          if (kit.window && x > winX - 120 && x < winX + winW + 120 && y < winY + winH + 80) return null;
          const d = propDef(k);
          return <g key={i} transform={`translate(${x} ${y})`}>{d.draw({ f, label: set.signs?.[i] })}</g>;
        })}
        {kit.light === "lamp" && <circle cx={WORLD_W * 0.82} cy={900} r={260} fill="url(#lampDisc)" />}
        {kit.light === "ceiling" && (
          <g>
            <path d={`M${WORLD_W / 2} -100 V170`} stroke={INK} strokeWidth={5} />
            <path d={`M${WORLD_W / 2 - 70} 230 L${WORLD_W / 2 + 70} 230 L${WORLD_W / 2 + 40} 170 L${WORLD_W / 2 - 40} 170 Z`} fill={PAL.slate} stroke={INK} strokeWidth={4} />
            <path d={`M${WORLD_W / 2 - 70} 230 L${WORLD_W / 2 + 70} 230 L${WORLD_W / 2 + 420} ${FLOOR_Y + 300} L${WORLD_W / 2 - 420} ${FLOOR_Y + 300} Z`} fill="#FFF3C9" opacity={night ? 0.16 : 0.1} />
          </g>
        )}
        {set.signs?.[0] && kit.decor.length === 0 && <Lettering x={WORLD_W / 2} y={260} size={60} text={set.signs[0]} />}
      </g>
    );
  }
  // ---------------- exteriors
  const [s0, s1] = g.sky;
  const hazeC = shade(s1, 0.1);
  const far = kit.far;
  return (
    <g>
      <defs>
        <linearGradient id={`sky${uid}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={s0} /><stop offset="1" stopColor={s1} /></linearGradient>
      </defs>
      <rect x={-400} y={-400} width={WORLD_W + 800} height={FLOOR_Y + 700} fill={`url(#sky${uid})`} />
      {far === "stars" || night ? Array.from({ length: 60 }, (_, i) => <circle key={i} cx={r() * WORLD_W} cy={r() * FLOOR_Y * 0.8} r={1.5 + r() * 2.5} fill="#fff" opacity={0.4 + 0.6 * Math.abs(Math.sin((f + i * 13) / 30))} />) : null}
      {kit.light === "sun" && !night && <g><circle cx={WORLD_W * 0.75} cy={380} r={170} fill="#FFF3C9" opacity={0.35} /><circle cx={WORLD_W * 0.75} cy={380} r={80} fill="#FBE7A1" stroke={INK} strokeWidth={4} /></g>}
      {(kit.light === "moon" || night) && <g><circle cx={WORLD_W * 0.72} cy={360} r={150} fill="#F3EBC8" opacity={0.15} /><circle cx={WORLD_W * 0.72} cy={360} r={60} fill="#F3EBC8" stroke={INK} strokeWidth={4} /></g>}
      {!night && far !== "stars" && [0, 1, 2].map((i) => <Cloud key={i} x={((i * 520 + f * (0.4 + i * 0.15)) % (WORLD_W + 400)) - 200} y={200 + i * 130} s={0.9 - i * 0.15} c={shade("#F4F1EA", -0.02 * i)} />)}
      {far === "hills" && <g><path d={`M-300 ${FLOOR_Y - 120} Q200 ${FLOOR_Y - 420} 600 ${FLOOR_Y - 160} T1500 ${FLOOR_Y - 220} V${FLOOR_Y + 100} H-300 Z`} fill={shade("#8FA66A", 0.25)} stroke={INK} strokeWidth={3} /><path d={`M-300 ${FLOOR_Y - 40} Q400 ${FLOOR_Y - 260} 900 ${FLOOR_Y - 60} T1800 ${FLOOR_Y - 90} V${FLOOR_Y + 100} H-300 Z`} fill="#8FA66A" stroke={INK} strokeWidth={3} /></g>}
      {far === "forest" && Array.from({ length: 14 }, (_, i) => <path key={i} d={`M${-100 + i * 115} ${FLOOR_Y + 10} l60 -${220 + (i % 3) * 50} l60 ${220 + (i % 3) * 50} Z`} fill={shade("#4E7A44", 0.15 + (i % 2) * 0.08)} stroke={INK} strokeWidth={3} />)}
      {far === "flat" && <path d={`M-300 ${FLOOR_Y - 30} L200 ${FLOOR_Y - 90} L420 ${FLOOR_Y - 60} L700 ${FLOOR_Y - 110} L1000 ${FLOOR_Y - 50} L1700 ${FLOOR_Y - 70} V${FLOOR_Y + 100} H-300 Z`} fill={shade("#B9805A", 0.2)} stroke={INK} strokeWidth={3} />}
      {far === "dunes" && <path d={`M-300 ${FLOOR_Y - 60} Q300 ${FLOOR_Y - 300} 700 ${FLOOR_Y - 80} T1700 ${FLOOR_Y - 120} V${FLOOR_Y + 100} H-300 Z`} fill={shade(PAL.sand, 0.15)} stroke={INK} strokeWidth={3} />}
      {far === "sea" && <g><rect x={-300} y={FLOOR_Y - 200} width={WORLD_W + 600} height={400} fill="#4F8CA8" stroke={INK} strokeWidth={3} />{[0, 1, 2, 3].map((i) => <path key={i} d={`M${-200 + ((f * 1.2 + i * 300) % 1700)} ${FLOOR_Y - 150 + i * 40} q30 -14 60 0`} stroke="#BFE0EC" strokeWidth={5} fill="none" />)}</g>}
      {far === "skyline" && Array.from({ length: 9 }, (_, i) => {
        const bw = 150 + (i % 3) * 30, bh = 380 + ((i * 137) % 5) * 90, x = -150 + i * 180;
        return (
          <g key={i}>
            <rect x={x} y={FLOOR_Y - bh} width={bw} height={bh + 60} fill={night ? shade("#2A3558", (i % 3) * 0.08) : shade("#9AA5A8", (i % 3) * 0.08)} stroke={INK} strokeWidth={3} />
            {Array.from({ length: Math.floor(bh / 70) }, (_, k) => <rect key={k} x={x + 24} y={FLOOR_Y - bh + 30 + k * 70} width={bw - 48} height={22} fill={night ? ((i + k + Math.floor(f / 50)) % 3 ? "#F3D36B" : "#1E2744") : "#D9E6E3"} />)}
          </g>
        );
      })}
      {far === "stars" && <g><circle cx={WORLD_W * 0.25} cy={700} r={220} fill="#C98E57" stroke={INK} strokeWidth={4} /><path d={`M${WORLD_W * 0.25 - 300} 700 Q${WORLD_W * 0.25} 620 ${WORLD_W * 0.25 + 300} 700`} stroke="#E2C26B" strokeWidth={12} fill="none" /></g>}
      <rect x={-400} y={FLOOR_Y - 260} width={WORLD_W + 800} height={300} fill={hazeC} opacity={0.22} />
    </g>
  );
};

export const Ground: React.FC<{ set: SetSpec; kit: Kit; uid: string }> = ({ set, kit, uid }) => {
  return (
    <g>
      <defs><Pattern id={`floor${uid}`} kind={set.floor ?? kit.floorPattern} fill={kit.floor} /></defs>
      <rect x={-500} y={FLOOR_Y} width={WORLD_W + 1000} height={H - FLOOR_Y + 600} fill={`url(#floor${uid})`} stroke={INK} strokeWidth={4} />
      <rect x={-500} y={FLOOR_Y} width={WORLD_W + 1000} height={70} fill="#000" opacity={0.12} />
      {kit.light === "lamp" && <ellipse cx={WORLD_W * 0.78} cy={FLOOR_Y + 260} rx={260} ry={70} fill="#FFE2A3" opacity={0.28} />}
    </g>
  );
};

export const SceneDefs: React.FC = () => (
  <defs>
    <radialGradient id="lampDisc"><stop offset="0" stopColor="#FFE9B0" stopOpacity={0.55} /><stop offset="1" stopColor="#FFE9B0" stopOpacity={0} /></radialGradient>
    <radialGradient id="heroHalo"><stop offset="0" stopColor={PAL.accent} stopOpacity={0.6} /><stop offset="0.55" stopColor={PAL.accent} stopOpacity={0.25} /><stop offset="1" stopColor={PAL.accent} stopOpacity={0} /></radialGradient>
    <filter id="fgBlur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6" /></filter>
    <filter id="whipBlur" x="-20%" y="-5%" width="140%" height="110%"><feGaussianBlur stdDeviation="40 0" /></filter>
  </defs>
);
