// Channel branding: the handle in the top-right corner of every frame, word-by-word captions in the lower third,
// and the follow sign of the 3-second outro.
import React from "react";
import type { Plan } from "../types";
import { INK, PAL, W, clamp01, easeOut, settle } from "../theme";

export const CornerTag: React.FC<{ text: string }> = ({ text }) => {
  const w = text.length * 25 + 44;
  return (
    <g transform={`translate(${W - 36 - w} 70)`} opacity={0.92}>
      <rect width={w} height={66} rx={33} fill="#111" opacity={0.55} />
      <text x={w / 2} y={45} fontFamily="PermanentMarker" fontSize={36} fill="#fff" textAnchor="middle">{text}</text>
    </g>
  );
};

/** captions: 1-3 words at a time, the spoken word in the accent colour, white with a thick ink edge */
export const Captions: React.FC<{ plan: Plan; frame: number }> = ({ plan, frame }) => {
  const cue = (plan.captions ?? []).find((c) => frame >= c.from && frame < c.to + 1);
  if (!cue) return null;
  const shot = plan.shots.find((s) => frame >= s.from && frame < s.from + s.dur);
  if (!shot || shot.kind === "card" || shot.kind === "outro") return null;
  const text = cue.words.map((w) => w.w.toUpperCase());
  const len = text.join(" ").length;
  const fs = Math.min(92, Math.floor(980 / Math.max(1, len * 0.62)));
  const pop = 1 + 0.06 * (1 - clamp01((frame - cue.from) / 4));
  return (
    <g transform={`translate(${W / 2} 1360) scale(${pop})`}>
      <text x={0} y={0} fontFamily="PermanentMarker" fontSize={fs} textAnchor="middle" stroke="#111" strokeWidth={16} paintOrder="stroke" strokeLinejoin="round">
        {cue.words.map((w, i) => (
          <tspan key={i} fill={frame >= w.s && frame <= w.e + 2 ? PAL.accent : "#FFFFFF"}>{text[i] + (i < text.length - 1 ? " " : "")}</tspan>
        ))}
      </text>
    </g>
  );
};

/** outro sign: hangs down into the frame, FOLLOW + channel name + handle */
export const FollowSign: React.FC<{ text: string; f: number }> = ({ text, f }) => {
  const m = text.match(/^Follow\s+(.*?)\s+and\s+(@\S+)$/i);
  const channel = m ? m[1] : text;
  const handle = m ? m[2] : "";
  const drop = (1 - settle(f / 10)) * -900;
  const btn = 1 + 0.05 * Math.sin(f / 4) * (f > 20 ? 1 : 0);
  return (
    <g transform={`translate(${W / 2 + 90} ${330 + drop})`}>
      <path d="M-200 -400 L-180 0 M200 -400 L180 0" stroke="#3B2A20" strokeWidth={6} />
      <rect x={-300} y={0} width={600} height={430} rx={22} fill={PAL.paper} stroke={INK} strokeWidth={8} />
      <g transform={`translate(0 92) scale(${btn})`}>
        <rect x={-190} y={-62} width={380} height={110} rx={55} fill={PAL.red} stroke={INK} strokeWidth={6} />
        <text x={0} y={18} fontFamily="PermanentMarker" fontSize={70} fill="#fff" textAnchor="middle">FOLLOW</text>
      </g>
      <text x={0} y={250} fontFamily="PermanentMarker" fontSize={Math.min(76, 540 / Math.max(1, channel.length * 0.6))} fill={INK} textAnchor="middle">{channel.toUpperCase()}</text>
      {handle && <text x={0} y={350} fontFamily="PermanentMarker" fontSize={64} fill={PAL.accentBody} textAnchor="middle" opacity={clamp01((f - 12) / 6)} transform={`translate(0 ${(1 - easeOut((f - 12) / 8)) * 20})`}>{"& " + handle}</text>}
    </g>
  );
};
