// Staged builds (skill 5.4): one line told with an object build instead of a label, every 8-12 s. Items land on
// their spoken words (frames in `at`), props never scale up from nothing, overshoot <= 2 %, a dust puff instead of
// a frame shake. Numbers count on an object in the scene (60 % of the value in the first third, then hold).
import React from "react";
import type { Build } from "../types";
import { CAST_Y, INK, PAL, WORLD_W, clamp01, easeOut, settle } from "../theme";
import { Lettering, propDef } from "../props/library";

const Puff: React.FC<{ k: number; x: number; y: number }> = ({ k, x, y }) =>
  k >= 0 && k < 8 ? (
    <g opacity={1 - k / 8}>
      {[-1, 0, 1].map((i) => <circle key={i} cx={x + i * (30 + k * 6)} cy={y - 10 - k * 2} r={18 + k * 2} fill="#E6E2DA" stroke={INK} strokeWidth={3} />)}
    </g>
  ) : null;

export function countValue(from: number, to: number, k: number, len = 30) {
  const t = clamp01(k / len);
  const p = t < 1 / 3 ? (t * 3) * 0.6 : 0.6 + ((t - 1 / 3) / (2 / 3)) * 0.4; // 60 % in the first third
  return from + (to - from) * easeOut(p);
}

export function fmt(v: number) {
  const r = Math.round(v);
  return r.toLocaleString("en-US");
}

const Board: React.FC<{ text: string; sub?: string; w?: number; hang?: boolean }> = ({ text, sub, w = 560, hang }) => (
  <g>
    {hang
      ? <path d={`M${-w / 2 + 50} -420 L${-w / 2 + 120} -1400 M${w / 2 - 50} -420 L${w / 2 - 120} -1400`} stroke="#3B2A20" strokeWidth={6} />
      : <path d={`M${-w / 2 + 40} 0 V-120 M${w / 2 - 40} 0 V-120`} stroke={PAL.wood} strokeWidth={16} />}
    <rect x={-w / 2} y={-420} width={w} height={300} rx={14} fill="#2F3B35" stroke={INK} strokeWidth={6} />
    <rect x={-w / 2 + 16} y={-404} width={w - 32} height={268} rx={8} fill="none" stroke="#5E6B5E" strokeWidth={4} />
    <text x={0} y={-238} fontFamily="PermanentMarker" fontSize={Math.min(130, (w - 60) / Math.max(1, text.length * 0.62))} fill={PAL.accent} textAnchor="middle">{text}</text>
    {sub && <Lettering x={0} y={-160} size={44} text={sub} color={PAL.cream} maxW={w - 60} />}
  </g>
);

export const BuildView: React.FC<{ b: Build; f: number }> = ({ b, f }) => {
  const x = (b.x ?? 0.5) * WORLD_W;
  const y = (b.y ?? 1) * CAST_Y;
  const s = b.scale ?? 1;
  return <g transform={`translate(${x} ${y}) scale(${s}) translate(${-x} ${-y})`}><BuildInner b={b} f={f} x={x} y={y} /></g>;
};

const BuildInner: React.FC<{ b: Build; f: number; x: number; y: number }> = ({ b, f, x, y }) => {
  const at0 = b.at[0] ?? 0;
  switch (b.recipe) {
    case "counter": {
      const v = f < at0 ? (b.from ?? 0) : countValue(b.from ?? 0, b.value ?? 0, f - at0, 30);
      return <g transform={`translate(${x} ${y})`}><Board text={`${b.prefix ?? ""}${fmt(v)}${b.suffix ?? ""}`} sub={b.label} hang={b.hang} /></g>;
    }
    case "slam_sticker": {
      const k = f - at0;
      if (k < 0) return null;
      const s = k < 6 ? 1.7 - 0.7 * (k / 6) : 1;
      return (
        <g transform={`translate(${x} ${y - 520}) rotate(-7) scale(${s})`}>
          <rect x={-250} y={-90} width={500} height={180} rx={18} fill="none" stroke={PAL.red} strokeWidth={14} />
          <text x={0} y={34} fontFamily="PermanentMarker" fontSize={Math.min(110, 460 / Math.max(1, (b.label ?? "").length * 0.62))} fill={PAL.red} textAnchor="middle">{(b.label ?? "").toUpperCase()}</text>
        </g>
      );
    }
    case "stack": {
      const items = b.items ?? [];
      return (
        <g transform={`translate(${x} ${y})`}>
          {items.map((it, i) => {
            const k = f - (b.at[i] ?? at0 + i * 10);
            if (k < 0) return null;
            const d = propDef(it.kind ?? "crate");
            const yy = -i * (d.h * 0.92);
            const drop = (1 - easeOut(k / 7)) * -700;
            return (
              <g key={i}>
                <g transform={`translate(${(i % 2) * 14 - 7} ${yy + drop})`}>{d.draw({ f, label: it.label })}</g>
                {i === 0 && <Puff k={k - 7} x={0} y={0} />}
              </g>
            );
          })}
        </g>
      );
    }
    case "side_slide": {
      const items = b.items ?? [];
      const gap = Math.min(380, (WORLD_W - 200) / Math.max(1, items.length));
      const x0 = WORLD_W / 2 - (gap * (items.length - 1)) / 2;
      return (
        <g>
          {items.map((it, i) => {
            const k = f - (b.at[i] ?? at0 + i * 12);
            if (k < 0) return null;
            const d = propDef(it.kind ?? "label_box");
            const dx = (1 - settle(k / 5)) * 900;
            return (
              <g key={i} transform={`translate(${x0 + i * gap + dx} ${y})`}>
                {d.draw({ f, label: it.label })}
                {it.label && it.kind && it.kind !== "label_box" && <Lettering x={0} y={50} size={42} text={it.label} color={PAL.cream} maxW={gap - 20} />}
              </g>
            );
          })}
        </g>
      );
    }
    case "compare": {
      const items = b.items ?? [];
      const max = Math.max(1, ...items.map((it) => it.value ?? 1));
      const pw = Math.min(360, (WORLD_W - 260) / Math.max(1, items.length));
      const x0 = WORLD_W / 2 - (pw * (items.length - 1)) / 2;
      return (
        <g>
          {items.map((it, i) => {
            const k = f - (b.at[i] ?? at0 + i * 18);
            if (k < 0) return null;
            const dy = (1 - easeOut(k / 17)) * -1400; // each panel drops from the top in 17 frames
            const hgt = 160 + 520 * ((it.value ?? 1) / max);
            return (
              <g key={i} transform={`translate(${x0 + i * pw} ${y + dy})`}>
                <rect x={-pw / 2 + 24} y={-hgt} width={pw - 48} height={hgt} rx={10} fill={it.accent ? PAL.accent : PAL.teal} stroke={INK} strokeWidth={6} />
                <text x={0} y={-hgt - 30} fontFamily="PermanentMarker" fontSize={70} textAnchor="middle" fill={PAL.cream} stroke={INK} strokeWidth={8} paintOrder="stroke">{fmt(countValue(0, it.value ?? 0, k, 24))}</text>
                <Lettering x={0} y={70} size={46} text={it.label} color={PAL.cream} maxW={pw - 20} />
              </g>
            );
          })}
        </g>
      );
    }
    case "state_flip": {
      const items = b.items ?? [{ label: "?" }, { label: "!" }];
      const k = f - at0;
      const flipped = k >= 0;
      return (
        <g transform={`translate(${x} ${y})`}>
          <Board text={(flipped ? items[1] : items[0]).label.toUpperCase()} sub={b.label} hang={b.hang} />
          {k >= 0 && k < 2 && <rect x={-400} y={-600} width={800} height={700} fill="#fff" opacity={0.4} />}
          {k >= 0 && k < 24 && Array.from({ length: 11 }, (_, i) => (
            <rect key={i} x={-200 + i * 40} y={-420 - k * (12 + (i % 3) * 4) + k * k * 0.5} width={34} height={24} fill={PAL.paper} stroke={INK} strokeWidth={2} transform={`rotate(${k * (i % 2 ? 12 : -10)} ${-183 + i * 40} ${-410 - k * 12})`} />
          ))}
        </g>
      );
    }
    case "glow_on": {
      const k = f - at0;
      const d = propDef(b.items?.[0]?.kind ?? "lightbulb");
      return (
        <g transform={`translate(${x} ${y}) scale(1.6)`}>
          {k >= 0 && <circle cx={0} cy={-d.h / 2} r={d.h * 0.9} fill="url(#heroHalo)" />}
          {k >= 0 && k < 3 && <circle cx={0} cy={-d.h / 2} r={d.h * 0.6 * (1 + (k / 3) * 0.1)} fill="none" stroke={PAL.accent} strokeWidth={4} />}
          <g opacity={k >= 0 ? 1 : 0.55}>{d.draw({ f, label: b.items?.[0]?.label })}</g>
        </g>
      );
    }
    case "drop_puff":
    case "grow": {
      const k = f - at0;
      if (k < 0) return null;
      const d = propDef(b.items?.[0]?.kind ?? "crate");
      const tr = b.recipe === "grow" ? `scale(1 ${easeOut(k / 10)})` : `translate(0 ${(1 - easeOut(k / 7)) * -800})`;
      return (
        <g transform={`translate(${x} ${y}) scale(1.4)`}>
          <g transform={tr}>{d.draw({ f, label: b.items?.[0]?.label })}</g>
          {b.recipe === "drop_puff" && <Puff k={k - 7} x={0} y={0} />}
        </g>
      );
    }
    case "tag_vanish": {
      const k = f - at0;
      if (k < 0 || k > 60) return k > 60 && k < 68 ? <Puff k={k - 60} x={x} y={y - 300} /> : null;
      return (
        <g transform={`translate(${x} ${y - 300}) rotate(-4)`}>
          <rect x={-220} y={-70} width={440} height={140} rx={16} fill={PAL.yellow} stroke={INK} strokeWidth={6} />
          <Lettering x={0} y={24} size={70} text={b.label} maxW={400} />
        </g>
      );
    }
    case "timeline": {
      const items = b.items ?? [];
      const x0 = 200, x1 = WORLD_W - 200;
      const prog = clamp01((f - at0) / 20);
      return (
        <g transform={`translate(0 ${y - 560})`}>
          <path d={`M${x0} 0 H${x0 + (x1 - x0) * prog}`} stroke={PAL.cream} strokeWidth={12} strokeLinecap="round" />
          {items.map((it, i) => {
            const k = f - (b.at[i] ?? at0 + i * 15);
            if (k < 0) return null;
            const xx = x0 + ((x1 - x0) * i) / Math.max(1, items.length - 1);
            const s = k < 6 ? 1.7 - 0.7 * (k / 6) : 1;
            return (
              <g key={i} transform={`translate(${xx} 0) scale(${s})`}>
                <circle r={22} fill={it.accent ? PAL.accent : PAL.yellow} stroke={INK} strokeWidth={5} />
                <Lettering x={0} y={i % 2 ? 100 : -50} size={58} text={it.label} color={PAL.cream} />
              </g>
            );
          })}
        </g>
      );
    }
    default:
      return null;
  }
};
