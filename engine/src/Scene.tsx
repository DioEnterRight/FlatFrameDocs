// A complete place for every beat (skill 5.1): back wall or sky, floor, furniture against the wall, the cast line,
// a blurred foreground prop, effects, the location grade (applied to the characters too) and a vignette.
// Every layer moves with its own depth so a push-in spreads them.
import React from "react";
import type { Actor, CastMember, PropItem, Shot } from "./types";
import { CAST_Y, FLOOR_Y, GRADES, H, INK, PAL, W, WORLD_W, clamp01, easeOut, hashStr, rng, settle } from "./theme";
import { camAt, DEPTH, layerTransform, type CamState } from "./camera/camera";
import { Backdrop, Ground } from "./sets/Backdrop";
import { KITS } from "./sets/kits";
import { propDef } from "./props/library";
import { Character, viewFor } from "./rig/Character";
import { Creature } from "./creatures/Creature";
import { Effect } from "./fx/Effects";
import { BuildView } from "./builds/Builds";

export const BASE_SCALE = 1.3; // a 420-unit figure is ~28 % of frame height in a wide set (skill: 20-30 %)

function propEntry(p: PropItem, f: number): { show: boolean; tr: string; puff: number } {
  const at = p.at ?? 0;
  const k = f - at;
  if (p.entry === undefined || p.entry === "none" || k >= 30) return { show: true, tr: "", puff: -1 };
  if (k < 0) return { show: false, tr: "", puff: -1 };
  switch (p.entry) {
    case "slide": return { show: true, tr: `translate(${(1 - settle(k / 5)) * (p.x < 0.5 ? -900 : 900)} 0)`, puff: -1 };
    case "drop": return { show: true, tr: `translate(0 ${(1 - easeOut(k / 7)) * -1200})`, puff: k - 7 };
    case "grow": return { show: true, tr: `scale(1 ${easeOut(k / 10)})`, puff: -1 };
    case "slam": return { show: true, tr: k < 6 ? `rotate(${-7 * (1 - k / 6)}) scale(${1.7 - 0.7 * (k / 6)})` : "", puff: -1 };
    case "switch": return { show: true, tr: "", puff: -1 };
    default: return { show: true, tr: "", puff: -1 };
  }
}

export const PropView: React.FC<{ p: PropItem; f: number; base: number; defaultY: number }> = ({ p, f, base, defaultY }) => {
  const d = propDef(p.kind);
  const e = propEntry(p, f);
  if (!e.show) return null;
  const s = base * (p.scale ?? 1);
  const x = p.x * WORLD_W;
  const y = p.y !== undefined ? p.y * H : defaultY;
  const k = f - (p.at ?? 0);
  return (
    <g transform={`translate(${x} ${y}) scale(${p.flip ? -s : s} ${s})`}>
      {p.glow && <circle cx={0} cy={-d.h / 2} r={Math.max(d.w, d.h) * 0.85} fill="url(#heroHalo)" opacity={0.85 + 0.15 * Math.sin(f / 10)} />}
      {p.glow && <g transform={`translate(0 ${-d.h / 2})`}><Effect kind="glow_particles" f={f} seed={hashStr(p.kind)} strength={0.7} /></g>}
      <ellipse cx={0} cy={0} rx={d.w * 0.48} ry={d.w * 0.06} fill="#000" opacity={0.18} />
      <g transform={e.tr}>{d.draw({ f, label: p.label })}</g>
      {p.entry === "switch" && k >= 0 && k < 3 && <circle cx={0} cy={-d.h / 2} r={Math.max(d.w, d.h) * 0.55 * (1 + k / 30)} fill="none" stroke={PAL.accent} strokeWidth={4} />}
      {e.puff >= 0 && e.puff < 8 && <g opacity={1 - e.puff / 8}>{[-1, 0, 1].map((i) => <circle key={i} cx={i * (36 + e.puff * 6)} cy={-12 - e.puff * 2} r={20 + e.puff * 2} fill="#E6E2DA" stroke={INK} strokeWidth={3} />)}</g>}
    </g>
  );
};

function actorX(a: Actor, f: number) {
  const target = a.x * WORLD_W;
  if (a.enterAt !== undefined) {
    const k = f - a.enterAt;
    const from = a.enterFrom === "right" ? WORLD_W + 300 : -300;
    if (k < 0) return { x: from, walking: false, hidden: true };
    if (k < 15) return { x: from + (target - from) * easeOut(k / 15), walking: true, hidden: false };
  }
  if (a.pose === "running") return { x: target + (a.facing === "left" ? -1 : 1) * f * 7, walking: true, hidden: false };
  return { x: target, walking: a.pose === "walking", hidden: false };
}

function exprAt(a: Actor, f: number) {
  let e = a.expr;
  for (const s of a.exprAt ?? []) if (f >= s.at) e = s.expr;
  return e;
}

export const ActorView: React.FC<{ a: Actor; who: CastMember; f: number; profile: boolean; dim: boolean; scaleMul?: number; forceView?: "back" }> = ({ a, who, f, profile, dim, scaleMul = 1, forceView }) => {
  const n = Math.max(1, a.count ?? 1);
  const r = rng(hashStr(a.id + who.id));
  return (
    <g>
      {Array.from({ length: n }, (_, i) => {
        const pos = actorX(a, f);
        if (pos.hidden) return null;
        const spread = n > 1 ? (i - (n - 1) / 2) * 150 + (r() - 0.5) * 50 : 0;
        const row = n > 1 ? (i % 2) * 70 - 35 : 0;
        const s = BASE_SCALE * (a.scale ?? 1) * scaleMul * (n > 1 ? 0.85 + r() * 0.2 : 1);
        const x = pos.x + spread;
        const y = CAST_Y + row;
        const walk = pos.walking ? (f + i * 7) / (a.pose === "running" ? 10 : 16) : null;
        const lvl = a.talk && f >= a.talk.start && f - a.talk.start < a.talk.env.length ? a.talk.env[f - a.talk.start] : null;
        const { view, mirror } = forceView ? { view: forceView, mirror: false } : viewFor(a.facing, profile || pos.walking);
        const bodyW = 150 * s;
        const expr = exprAt(a, f + i * 5);
        return (
          <g key={i}>
            <ellipse cx={x + bodyW / 3} cy={y} rx={bodyW * 0.62} ry={bodyW * 0.1} fill="#000" opacity={dim ? 0.42 : 0.25} />
            <g transform={`translate(${x} ${y}) scale(${s})`}>
              {who.creature ? (
                <g transform={mirror || a.facing === "left" ? "scale(-1,1)" : ""}><Creature kind={who.creature} frame={f + i * 13} expr={expr} walk={walk} color={who.outfit?.color} /></g>
              ) : (
                <Character who={who} frame={f + i * 17} expr={expr} pose={a.pose} view={view} mirror={mirror} talkLevel={lvl} walkPhase={walk} holdKind={a.hold}
                  renderHeld={(k) => { const d = propDef(k); return <g transform={`translate(0 ${d.h * 0.25}) scale(0.5)`}>{d.draw({ f })}</g>; }} />
              )}
            </g>
          </g>
        );
      })}
    </g>
  );
};

export function castOf(cast: CastMember[], id: string): CastMember {
  return cast.find((c) => c.id === id) ?? { id, skin: "#E8B48A", hair: { style: "side_part", color: "#3B2A20" }, outfit: { kind: "sweater", color: PAL.teal, accent: PAL.paper } };
}

export const World: React.FC<{ shot: Shot; f: number; cast: CastMember[]; uid: string; cam?: CamState }> = ({ shot, f, cast, uid, cam: camIn }) => {
  const set = shot.set ?? { kind: "office", grade: "day", variant: 0 };
  const kit = KITS[set.kind] ?? KITS.office;
  const g = GRADES[set.grade] ?? GRADES.day;
  const seed = hashStr(uid);
  const cam = camIn ?? camAt(shot.camera, f, shot.dur, seed % 1000);
  const dim = set.grade === "night" || set.grade === "dark" || set.grade === "dinner";
  const props = shot.props ?? [];
  const byLayer = (l: string) => props.filter((p) => (p.layer ?? "cast") === l);
  const r = rng(seed);
  const furniture = kit.outdoor ? (kit.mid ?? []) : kit.furniture;
  const furnX = furniture.map((_, i) => (0.12 + (i * 0.76) / Math.max(1, furniture.length - 1) + (r() - 0.5) * 0.05));
  const ots = shot.ots;
  const actors = (shot.actors ?? []).filter((a) => !(ots && a.id === ots.near));
  const near = ots ? (shot.actors ?? []).find((a) => a.id === ots.near) : undefined;
  const profile = shot.kind === "skit" && !ots;
  return (
    <g>
      <g transform={layerTransform(cam, DEPTH.back)}><Backdrop set={set} kit={kit} f={f} uid={uid} /></g>
      <g transform={layerTransform(cam, DEPTH.floor)}><Ground set={set} kit={kit} uid={uid} /></g>
      <g transform={layerTransform(cam, DEPTH.mid)}>
        {furniture.map((k, i) => {
          const d = propDef(k);
          const s = kit.outdoor ? 0.8 : 1.05;
          return <g key={i} transform={`translate(${furnX[i] * WORLD_W} ${FLOOR_Y + (kit.outdoor ? 40 : 110)}) scale(${s})`}>{d.draw({ f, label: set.signs?.[i + 1] })}</g>;
        })}
        {byLayer("back").concat(byLayer("mid")).map((p, i) => <PropView key={i} p={p} f={f} base={1.1} defaultY={FLOOR_Y + 120} />)}
      </g>
      <g transform={layerTransform(cam, DEPTH.cast)}>
        {byLayer("cast").filter((p) => p.y === undefined || p.y > 0.6).map((p, i) => <PropView key={"b" + i} p={p} f={f} base={1.3} defaultY={CAST_Y + 30} />)}
        {actors.map((a) => <ActorView key={a.id} a={a} who={castOf(cast, a.id)} f={f} profile={profile} dim={dim} />)}
        {byLayer("cast").filter((p) => p.y !== undefined && p.y <= 0.6).map((p, i) => <PropView key={"t" + i} p={p} f={f} base={1.3} defaultY={CAST_Y} />)}
        {shot.build && <BuildView b={shot.build} f={f} />}
      </g>
      <g transform={layerTransform(cam, DEPTH.fg)}>
        {!near && shot.kind !== "skit" && (
          <g filter="url(#fgBlur)" transform={`translate(${(seed % 2 ? 0.02 : 0.98) * WORLD_W} ${H + 40}) scale(1.9)`}>{propDef(kit.fg).draw({ f })}</g>
        )}
        {byLayer("fg").map((p, i) => <PropView key={i} p={p} f={f} base={1.8} defaultY={H + 20} />)}
      </g>
      {near && (
        // over-the-shoulder: the near character's back and shoulder frame the edge of the shot (screen space)
        <g transform={`translate(${near.x < 0.5 ? 60 : W - 60} ${H + 430}) scale(${BASE_SCALE * 1.9})`}>
          <Character who={castOf(cast, near.id)} frame={f} expr={near.expr} pose="idle" view="back" />
          <rect x={-200} y={-460} width={400} height={480} fill="#000" opacity={0.18} />
        </g>
      )}
      {shot.fx?.bg && <Effect kind={shot.fx.bg.kind} f={f} seed={seed + 1} strength={(shot.fx.bg.strength ?? 0.6) * 0.6} />}
      {shot.fx?.main && <Effect kind={shot.fx.main.kind} f={f} seed={seed} strength={shot.fx.main.strength ?? 1} />}
      <rect x={0} y={0} width={W} height={H} fill={g.tint} opacity={g.tintOpacity} style={{ mixBlendMode: g.blend }} />
      <Vignette strength={g.vignette} />
    </g>
  );
};

export const Vignette: React.FC<{ strength: number }> = ({ strength }) => (
  <g>
    <defs>
      <radialGradient id={`vig${Math.round(strength * 100)}`} cx="0.5" cy="0.5" r="0.75">
        <stop offset="0.45" stopColor="#000" stopOpacity={0} />
        <stop offset="1" stopColor="#000" stopOpacity={strength} />
      </radialGradient>
    </defs>
    <rect x={0} y={0} width={W} height={H} fill={`url(#vig${Math.round(strength * 100)})`} />
  </g>
);

export const clampT = clamp01;
