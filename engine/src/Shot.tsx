// One beat = one shot. Dispatches to the shot vocabulary of the skill (5.3): story / skit scenes, literal metaphors
// and hero objects (props in a scene), black text cards, the title over a live scene, inserts, maps, table-tops,
// triptychs. Overlay texts carry only what the picture cannot (a place, a date, a name, a number).
import React from "react";
import type { CastMember, Shot } from "./types";
import { GRADES, H, INK, PAL, W, easeOut, hashStr, settle } from "./theme";
import { camAt } from "./camera/camera";
import { World, Vignette, PropView } from "./Scene";
import { BuildView } from "./builds/Builds";
import { FollowSign } from "./ui/Brand";
import { BlackCard, CalendarRip, QuoteBar, StampTag, Strip, TitleCard } from "./ui/Cards";
import { WorldMap } from "./maps/WorldMap";
import { Pattern } from "./sets/patterns";
import { Lettering, propDef } from "./props/library";

const Overlays: React.FC<{ shot: Shot; f: number }> = ({ shot, f }) => (
  <g>
    {(shot.texts ?? []).map((t, i) => {
      if (t.kind === "strip") return <Strip key={i} text={t.text} f={f} at={t.at} corner={i % 2 ? "right" : "left"} />;
      if (t.kind === "stamp") return <StampTag key={i} text={t.text} f={f} at={t.at} />;
      if (t.kind === "quote") return <QuoteBar key={i} text={t.text} who={t.who} f={f} at={t.at} />;
      if (t.kind === "calendar") return <CalendarRip key={i} text={t.text} f={f} at={t.at} />;
      return null;
    })}
  </g>
);

/** 2-4 s cut to one object on a patterned wall (skill: insert set) */
const Insert: React.FC<{ shot: Shot; f: number; uid: string }> = ({ shot, f, uid }) => {
  const cam = camAt(shot.camera, f, shot.dur, hashStr(uid) % 1000);
  const p = (shot.props ?? [])[0] ?? { kind: "label_box", x: 0.5 };
  const d = propDef(p.kind);
  const s = Math.min(3.2, 820 / Math.max(d.w, d.h)) * (p.scale ?? 1);
  const g = GRADES[shot.set?.grade ?? "day"];
  const wallFill = shot.set?.grade === "night" || shot.set?.grade === "dark" ? "#2B2F3A" : "#B9A98A";
  return (
    <g>
      <defs><Pattern id={`ins${uid}`} kind={shot.set?.wall ?? "wallpaper"} fill={wallFill} /></defs>
      <g transform={`translate(${W / 2} ${H / 2}) scale(${cam.z}) translate(${-W / 2} ${-H / 2})`}>
        <rect x={-200} y={-200} width={W + 400} height={H + 400} fill={`url(#ins${uid})`} />
        <rect x={-200} y={1260} width={W + 400} height={900} fill={PAL.wood} stroke={INK} strokeWidth={5} />
        <rect x={-200} y={1260} width={W + 400} height={40} fill="#000" opacity={0.18} />
        <circle cx={W / 2} cy={1260 - (d.h * s) / 2} r={(Math.max(d.w, d.h) * s) / 1.4} fill="#FFF3C9" opacity={0.18} />
        <PropView p={{ ...p, x: (W / 2 + (1404 - W) / 2) / 1404, y: 1290 / H, scale: s / 1.3 }} f={f} base={1.3} defaultY={1290} />
        {p.label && !["label_box", "newspaper", "document", "sign_post", "banner", "crate", "sack"].includes(p.kind) && <g transform={`translate(${W / 2} 1500)`}><rect x={-300} y={-70} width={600} height={110} rx={10} fill="#D9B36A" stroke={INK} strokeWidth={5} /><Lettering x={0} y={8} size={60} text={p.label} maxW={560} /></g>}
      </g>
      {shot.build && <g transform={`translate(${-(1404 - W) / 2} ${-560}) scale(1)`}><BuildView b={{ ...shot.build, y: 1, hang: true, scale: 0.8 }} f={f} /></g>}
      <rect x={0} y={0} width={W} height={H} fill={g.tint} opacity={g.tintOpacity} style={{ mixBlendMode: g.blend }} />
      <Vignette strength={g.vignette} />
    </g>
  );
};

/** a document or map lying flat, seen from above, with objects standing on it */
const Tabletop: React.FC<{ shot: Shot; f: number; uid: string }> = ({ shot, f, uid }) => {
  const cam = camAt(shot.camera, f, shot.dur, hashStr(uid) % 1000);
  const props = shot.props ?? [];
  return (
    <g>
      <defs><Pattern id={`tab${uid}`} kind="planks" fill="#7A5232" /></defs>
      <g transform={`translate(${W / 2} ${H / 2}) scale(${cam.z}) translate(${-W / 2} ${-H / 2})`}>
        <rect x={-300} y={-300} width={W + 600} height={H + 600} fill={`url(#tab${uid})`} />
        <g transform={`translate(${W / 2} ${H / 2 + 260}) rotate(-3) scale(4.2)`}>{propDef(props[0]?.kind ?? "document").draw({ f, label: props[0]?.label })}</g>
        {props.slice(1).map((p, i) => {
          const k = f - (p.at ?? 0);
          if (k < 0) return null;
          const d = propDef(p.kind);
          const drop = (1 - easeOut(k / 7)) * -900;
          return <g key={i} transform={`translate(${p.x * W} ${(p.y ?? 0.4 + i * 0.12) * H + drop}) rotate(${(i * 37) % 20 - 10}) scale(${(p.scale ?? 1) * 1.6})`}>{d.draw({ f, label: p.label })}</g>;
        })}
      </g>
      {shot.build && <g transform={`translate(${-(1404 - W) / 2} ${-560})`}><BuildView b={{ ...shot.build, y: 1, hang: true, scale: 0.8 }} f={f} /></g>}
      <Vignette strength={0.38} />
    </g>
  );
};

/** three panels with dark dividers sliding in one by one as the narrator lists three things (stacked for 9:16) */
const Triptych: React.FC<{ shot: Shot; f: number }> = ({ shot, f }) => {
  const panels = shot.panels ?? [];
  const ph = H / 3;
  const bg = ["#4A6B6E", "#6E4726", "#2C3E50"];
  return (
    <g>
      <rect x={0} y={0} width={W} height={H} fill="#111" />
      {panels.slice(0, 3).map((p, i) => {
        const k = f - p.at;
        if (k < 0) return null;
        const dx = (1 - settle(k / 6)) * (i % 2 ? -W : W);
        const d = propDef(p.prop);
        const s = Math.min(2.2, (ph * 0.62) / d.h);
        return (
          <g key={i} transform={`translate(${dx} ${i * ph})`}>
            <rect x={0} y={8} width={W} height={ph - 16} fill={bg[i]} />
            <circle cx={W * 0.36} cy={ph * 0.6} r={ph * 0.34} fill="#FFF3C9" opacity={0.15} />
            <g transform={`translate(${W * 0.36} ${ph * 0.86}) scale(${s})`}>{d.draw({ f, label: p.label })}</g>
            <Lettering x={W * 0.76} y={ph * 0.56} size={70} text={p.label} color={PAL.cream} maxW={W * 0.42} />
          </g>
        );
      })}
      <Vignette strength={0.3} />
    </g>
  );
};

export const ShotView: React.FC<{ shot: Shot; f: number; cast: CastMember[]; idx: number }> = ({ shot, f, cast, idx }) => {
  const uid = `s${idx}`;
  let body: React.ReactNode;
  switch (shot.kind) {
    case "card":
      body = <BlackCard text={shot.card?.text ?? ""} f={f} typeFrom={shot.card?.typeFrom ?? 0} cps={shot.card?.cps ?? 19} />;
      break;
    case "map":
      body = <g>{shot.map && <WorldMap m={shot.map} f={f} dur={shot.dur} />}<Vignette strength={0.3} /></g>;
      break;
    case "insert":
      body = <Insert shot={shot} f={f} uid={uid} />;
      break;
    case "tabletop":
      body = <Tabletop shot={shot} f={f} uid={uid} />;
      break;
    case "triptych":
      body = <Triptych shot={shot} f={f} />;
      break;
    default:
      body = <World shot={shot} f={f} cast={cast} uid={uid} />;
  }
  return (
    <g>
      {body}
      {shot.kind === "outro" && shot.outro && <FollowSign text={shot.outro.text} f={f} />}
      {shot.kind === "title" && shot.title && <TitleCard lines={shot.title.lines} accentWord={shot.title.accentWord} at={shot.title.at} f={f} />}
      {shot.kind !== "card" && <Overlays shot={shot} f={f} />}
    </g>
  );
};
