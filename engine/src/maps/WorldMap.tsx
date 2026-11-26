// Animated map (skill 5.3): pale blue sea, beige land with a dark outline, the one relevant country in a flat
// saturated colour, a pin that drops, a white arc route drawn in about a second with the camera following, small
// outlined caps for labels. Dark style with a glowing front for conflict. Natural Earth data via world-atlas (ISC).
import React from "react";
import { geoMercator, geoPath, geoInterpolate } from "d3-geo";
import { feature } from "topojson-client";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import world from "world-atlas/countries-110m.json";
import type { MapSpec } from "../types";
import { H, INK, PAL, W, clamp01, easeInOut, easeOut } from "../theme";

type Country = Feature<Geometry, { name: string }>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const countries = (feature(world as any, (world as any).objects.countries) as unknown as FeatureCollection<Geometry, { name: string }>).features as Country[];

export function findCountry(name: string): Country | undefined {
  const n = name.toLowerCase();
  return countries.find((c) => c.properties.name.toLowerCase() === n) ?? countries.find((c) => c.properties.name.toLowerCase().includes(n));
}

export const WorldMap: React.FC<{ m: MapSpec; f: number; dur: number }> = ({ m, f, dur }) => {
  const dark = m.style === "dark";
  const focus = m.focus === "world" ? undefined : findCountry(m.focus);
  const proj = geoMercator();
  const box: [[number, number], [number, number]] = [[90, 420], [W - 90, H - 520]];
  if (focus) proj.fitExtent(box, focus);
  else proj.fitExtent(box, { type: "Sphere" } as never);
  // camera: zoom from a wider view down to the focus (or a slow push when there is no zoomFrom)
  const zf = m.zoomFrom ?? 1.0;
  const t = easeInOut(clamp01(f / Math.max(1, Math.min(dur * 0.6, 45))));
  const zoom = (zf + (1 - zf) * t) * (1 + 0.04 * (f / Math.max(1, dur)));
  const [cx, cy] = [W / 2, (box[0][1] + box[1][1]) / 2];
  proj.scale(proj.scale() * zoom).translate([cx + (proj.translate()[0] - cx) * zoom, cy + (proj.translate()[1] - cy) * zoom]);
  const path = geoPath(proj);
  const hl = new Set((m.highlight ?? (focus ? [focus.properties.name] : [])).map((s) => s.toLowerCase()));
  const sea = dark ? "#0F1A2A" : "#BFDCE8";
  const land = dark ? "#2A3245" : "#E6D3A8";
  const hot = dark ? PAL.red : "#D9A441";
  return (
    <g>
      <rect x={0} y={0} width={W} height={H} fill={sea} />
      {Array.from({ length: 9 }, (_, i) => <path key={i} d={`M0 ${200 + i * 200} H${W}`} stroke={dark ? "#1B2A40" : "#A9CDDC"} strokeWidth={3} />)}
      {countries.map((c, i) => {
        const d = path(c);
        if (!d) return null;
        const on = hl.has(c.properties.name.toLowerCase());
        return <path key={i} d={d} fill={on ? hot : land} stroke={INK} strokeWidth={on ? 5 : 2.5} strokeLinejoin="round" />;
      })}
      {focus && (() => {
        const [x, y] = path.centroid(focus);
        return <text x={x} y={y} fontFamily="PatrickHand" fontSize={64} fill="#fff" stroke={INK} strokeWidth={9} paintOrder="stroke" textAnchor="middle" style={{ letterSpacing: 3 }}>{focus.properties.name.toUpperCase()}</text>;
      })()}
      {m.route && (() => {
        const k = clamp01((f - m.route.at) / 30);
        if (k <= 0) return null;
        const interp = geoInterpolate(m.route.from, m.route.to);
        const pts = Array.from({ length: 40 }, (_, i) => proj(interp((i / 39) * k)) as [number, number]);
        const lift = pts.map(([x, y], i) => [x, y - Math.sin((i / 39) * Math.PI) * 120 * k] as [number, number]);
        return <path d={"M" + lift.map((p) => p.join(" ")).join(" L")} stroke="#fff" strokeWidth={9} fill="none" strokeLinecap="round" strokeDasharray="22 14" />;
      })()}
      {(m.pins ?? []).map((p, i) => {
        const k = f - p.at;
        if (k < 0) return null;
        const xy = proj([p.lon, p.lat]);
        if (!xy) return null;
        const drop = (1 - easeOut(k / 8)) * -300;
        return (
          <g key={i} transform={`translate(${xy[0]} ${xy[1] + drop})`}>
            <ellipse cx={0} cy={4} rx={22} ry={8} fill="#000" opacity={0.25} />
            <path d="M0 0 C-30 -40 -40 -60 -40 -84 A40 40 0 1 1 40 -84 C40 -60 30 -40 0 0 Z" fill={PAL.red} stroke={INK} strokeWidth={5} />
            <circle cx={0} cy={-84} r={14} fill="#fff" stroke={INK} strokeWidth={3} />
            {p.label && <text x={0} y={-140} fontFamily="PatrickHand" fontSize={52} fill="#fff" stroke={INK} strokeWidth={8} paintOrder="stroke" textAnchor="middle">{p.label.toUpperCase()}</text>}
          </g>
        );
      })}
    </g>
  );
};
