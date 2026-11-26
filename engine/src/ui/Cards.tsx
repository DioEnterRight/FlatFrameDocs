// Text that sits on the lens (skill 5.3): black text cards typed in Caveat and locked to the voice, the one title card
// over a live scene, place/date strips in a corner, a hanging date tag on a string, a quote bar for real quotes.
// Never a running subtitle, never at bottom centre, never a restatement of the narration.
import React from "react";
import { H, PAL, W, clamp01, easeOut, pendulum } from "../theme";

export function wrap(text: string, maxChars: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let cur = "";
  for (const w of words) {
    if ((cur + " " + w).trim().length > maxChars && cur) {
      lines.push(cur);
      cur = w;
    } else cur = (cur + " " + w).trim();
  }
  if (cur) lines.push(cur);
  return lines;
}

/** Vertical-format adaptation: the skill's single unwrapped line at 9 % height does not fit 1080 px, so the card
 *  uses up to three balanced lines with cap height ~5 % of the frame. Typing speed and timing are unchanged. */
export const BlackCard: React.FC<{ text: string; f: number; typeFrom: number; cps: number }> = ({ text, f, typeFrom, cps }) => {
  let fs = 140;
  let lines = wrap(text, Math.floor(930 / (fs * 0.43)));
  while (lines.length > 3 && fs > 90) {
    fs -= 10;
    lines = wrap(text, Math.floor(930 / (fs * 0.43)));
  }
  const shown = Math.max(0, Math.floor(((f - typeFrom) * cps) / 30));
  let left = shown;
  const lh = fs * 1.08;
  const y0 = H / 2 - ((lines.length - 1) * lh) / 2 + fs * 0.3;
  return (
    <g>
      <rect x={0} y={0} width={W} height={H} fill="#000000" />
      {lines.map((l, i) => {
        const vis = l.slice(0, Math.max(0, left));
        left -= l.length + 1;
        return <text key={i} x={W / 2} y={y0 + i * lh} fontFamily="Caveat" fontSize={fs} fill="#FFFFFF" textAnchor="middle">{vis}<tspan fill="#000">{l.slice(vis.length)}</tspan></text>;
      })}
    </g>
  );
};

export const TitleCard: React.FC<{ lines: string[]; accentWord?: string; at: number[]; f: number }> = ({ lines, accentWord, at, f }) => {
  const longest = Math.max(...lines.map((l) => l.length));
  const fs = Math.min(126, Math.floor(960 / (longest * 0.66)));
  const y0 = 560;
  return (
    <g>
      <rect x={0} y={y0 - 190} width={W} height={lines.length * fs * 1.12 + 150} fill="#000" opacity={0.28} />
      {lines.map((l, i) => {
        const t = clamp01((f - (at[i] ?? i * 10)) / 6);
        if (t <= 0) return null;
        const words = l.toUpperCase().split(" ");
        return (
          <text key={i} x={W / 2} y={y0 + i * fs * 1.12} fontFamily="PermanentMarker" fontSize={fs} textAnchor="middle" opacity={t} transform={`translate(0 ${(1 - easeOut(t)) * 18})`} stroke="#111" strokeWidth={10} paintOrder="stroke" strokeLinejoin="round">
            {words.map((w, k) => <tspan key={k} fill={accentWord && w.replace(/[^A-Z0-9]/g, "") === accentWord.toUpperCase().replace(/[^A-Z0-9]/g, "") ? PAL.accent : PAL.cream}>{w + (k < words.length - 1 ? " " : "")}</tspan>)}
          </text>
        );
      })}
    </g>
  );
};

/** place / date / name strip: a small level dark strip in a top corner with an accent bar, typed on in 0.5 s */
export const Strip: React.FC<{ text: string; f: number; at: number; corner?: "left" | "right" }> = ({ text, f, at, corner = "left" }) => {
  if (f < at) return null;
  const t = text.toUpperCase();
  const n = Math.ceil(clamp01((f - at) / 15) * t.length);
  const w = Math.min(760, t.length * 40 + 70);
  const x = corner === "left" ? 60 : W - 60 - w;
  return (
    <g transform={`translate(${x} 250)`}>
      <rect width={w} height={86} fill="#14161C" opacity={0.92} />
      <rect width={12} height={86} fill={PAL.accent} />
      <text x={36} y={60} fontFamily="PatrickHand" fontSize={58} fill={PAL.cream} style={{ letterSpacing: 2 }}>{t.slice(0, n)}</text>
    </g>
  );
};

/** date or place stamp: a yellow tag hanging from a string that drops in and swings like a damped pendulum */
export const StampTag: React.FC<{ text: string; f: number; at: number; corner?: "left" | "right" }> = ({ text, f, at, corner = "right" }) => {
  if (f < at) return null;
  const k = f - at;
  const drop = (1 - easeOut(k / 8)) * -260;
  const ang = pendulum(k, 16, 28, 0.07);
  const x = corner === "right" ? W - 250 : 250;
  const t = text.toUpperCase();
  const w = Math.max(220, t.length * 42 + 60);
  return (
    <g transform={`translate(${x} ${drop}) rotate(${ang} 0 0)`}>
      <path d="M0 0 V180" stroke="#2A2A2A" strokeWidth={4} />
      <g transform="translate(0 180)">
        <path d={`M${-w / 2} 20 L-30 0 L30 0 L${w / 2} 20 L${w / 2} 130 L${-w / 2} 130 Z`} fill={PAL.yellow} stroke="#111" strokeWidth={5} />
        <circle cx={0} cy={14} r={9} fill="#fff" stroke="#111" strokeWidth={4} />
        <text x={0} y={100} fontFamily="PatrickHand" fontSize={62} fill="#111" textAnchor="middle">{t}</text>
      </g>
    </g>
  );
};

/** a real quote: off-white rounded bar across the top, typed, with the speaker's name */
export const QuoteBar: React.FC<{ text: string; who?: string; f: number; at: number }> = ({ text, who, f, at }) => {
  if (f < at) return null;
  const n = Math.floor(((f - at) * 22) / 30);
  const lines = wrap(`“${text}”`, 30);
  let left = n;
  return (
    <g transform="translate(60 220)">
      <rect width={W - 120} height={lines.length * 66 + 110} rx={26} fill={PAL.paper} stroke="#111" strokeWidth={5} />
      {lines.map((l, i) => {
        const vis = l.slice(0, Math.max(0, left));
        left -= l.length + 1;
        return <text key={i} x={40} y={80 + i * 66} fontFamily="PatrickHand" fontSize={54} fill="#111">{vis}</text>;
      })}
      {who && <text x={W - 160} y={lines.length * 66 + 86} fontFamily="PatrickHand" fontSize={40} fill={PAL.red} textAnchor="end">— {who.toUpperCase()}</text>}
    </g>
  );
};

/** wall calendar whose top page rips off and falls with gravity and a spin */
export const CalendarRip: React.FC<{ text: string; f: number; at: number }> = ({ text, f, at }) => {
  const k = f - at;
  const page = (label: string, extra = {}) => (
    <g {...extra}>
      <rect x={-130} y={0} width={260} height={300} fill={PAL.paper} stroke="#111" strokeWidth={5} />
      <rect x={-130} y={0} width={260} height={70} fill={PAL.red} stroke="#111" strokeWidth={5} />
      <text x={0} y={210} fontFamily="PatrickHand" fontSize={110} textAnchor="middle" fill="#111">{label}</text>
    </g>
  );
  const parts = text.split("|");
  return (
    <g transform={`translate(${W - 230} 200)`}>
      {page(parts[1] ?? parts[0])}
      {k < 40 && page(parts[0], k > 0 ? { transform: `translate(${k * 4} ${k * k * 0.9}) rotate(${k * 6} 0 0)`, opacity: 1 - k / 40 } : {})}
    </g>
  );
};
