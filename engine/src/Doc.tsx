// The whole documentary: one <Sequence> per beat (skill 5.0), hard cuts by default (>= 85 % of transitions),
// a few designed transitions: whip-pans (real travel with motion blur) and colour washes that hide a dolly-through.
import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame } from "remotion";
import { Captions, CornerTag } from "./ui/Brand";
import type { Plan, Shot } from "./types";
import { H, PAL, W, clamp01, easeIn, easeOut } from "./theme";
import { ShotView } from "./Shot";
import { RigDefs } from "./rig/Character";
import { SceneDefs } from "./sets/Backdrop";
import { FONT_CSS } from "./ui/fontData";

const WHIP = 7;

const Beat: React.FC<{ shot: Shot; next?: Shot; plan: Plan; idx: number }> = ({ shot, next, plan, idx }) => {
  const f = useCurrentFrame();
  let dx = 0, blur = 0, wash = 0;
  // whip-pan: the outgoing shot travels out and the incoming one travels in from the other side, in one direction
  const dirIn = idx % 2 ? -1 : 1;
  const dirOut = (idx + 1) % 2 ? -1 : 1;
  if (shot.transition === "whip" && f < WHIP) {
    const t = 1 - easeOut(f / WHIP);
    dx = dirIn * W * 0.85 * t;
    blur = t;
  }
  if (next?.transition === "whip" && f >= shot.dur - WHIP) {
    const t = easeIn((f - (shot.dur - WHIP)) / WHIP);
    dx = -dirOut * W * 0.85 * t;
    blur = t;
  }
  if (shot.transition === "flash" && f < 7) wash = 1 - clamp01(f / 7);
  if (next?.transition === "flash" && f >= shot.dur - 7) wash = clamp01((f - (shot.dur - 7)) / 7);
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", inset: 0 }}>
      <RigDefs />
      <SceneDefs />
      <g transform={`translate(${dx} 0)`} filter={blur > 0.05 ? "url(#whipBlur)" : undefined}>
        <ShotView shot={shot} f={f} cast={plan.cast} idx={idx} />
      </g>
      {wash > 0 && <rect x={0} y={0} width={W} height={H} fill={PAL.accent} opacity={wash * 0.85} />}
    </svg>
  );
};

const Overlay: React.FC<{ plan: Plan }> = ({ plan }) => {
  const f = useCurrentFrame();
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", inset: 0 }}>
      <Captions plan={plan} frame={f} />
      {plan.brand?.corner && <CornerTag text={plan.brand.corner} />}
    </svg>
  );
};

export const Doc: React.FC<{ plan: Plan }> = ({ plan }) => (
  <AbsoluteFill style={{ backgroundColor: "#000" }}>
    <style>{FONT_CSS}</style>
    {plan.shots.map((s, i) => (
      <Sequence key={i} from={s.from} durationInFrames={s.dur} name={`${i + 1} ${s.kind}${s.line ? ": " + s.line.slice(0, 40) : ""}`}>
        <Beat shot={s} next={plan.shots[i + 1]} plan={plan} idx={i} />
      </Sequence>
    ))}
    <Overlay plan={plan} />
  </AbsoluteFill>
);
