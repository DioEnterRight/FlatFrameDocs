// No bare surfaces (skill 5.1): every wall and floor gets one drawn pattern in lines one tone darker than the fill.
import React from "react";
import { shade } from "../theme";

export const WALL_PATTERNS = ["panels", "brick", "stone", "wallpaper", "siding", "tiles", "stripes"];
export const FLOOR_PATTERNS = ["planks", "checker", "tiles", "carpet", "concrete"];

export const Pattern: React.FC<{ id: string; kind: string; fill: string }> = ({ id, kind, fill }) => {
  const ln = shade(fill, -0.22);
  const sw = 3;
  switch (kind) {
    case "brick":
      return <pattern id={id} width={120} height={60} patternUnits="userSpaceOnUse"><rect width={120} height={60} fill={fill} /><path d="M0 0 H120 M0 30 H120 M60 0 V30 M0 30 V60 M120 30 V60" stroke={ln} strokeWidth={sw} /></pattern>;
    case "stone":
      return <pattern id={id} width={200} height={100} patternUnits="userSpaceOnUse"><rect width={200} height={100} fill={fill} /><path d="M0 0 H200 M0 50 H200 M70 0 V50 M150 0 V50 M30 50 V100 M120 50 V100" stroke={ln} strokeWidth={sw} /></pattern>;
    case "wallpaper":
      return <pattern id={id} width={90} height={90} patternUnits="userSpaceOnUse"><rect width={90} height={90} fill={fill} /><circle cx={22} cy={22} r={6} fill={ln} /><circle cx={67} cy={67} r={6} fill={ln} /><path d="M45 10 v12 M39 16 h12" stroke={ln} strokeWidth={2} /></pattern>;
    case "siding":
      return <pattern id={id} width={100} height={44} patternUnits="userSpaceOnUse"><rect width={100} height={44} fill={fill} /><path d="M0 40 H100" stroke={ln} strokeWidth={sw + 1} /><path d="M0 4 H100" stroke={shade(fill, 0.12)} strokeWidth={4} /></pattern>;
    case "tiles":
      return <pattern id={id} width={80} height={80} patternUnits="userSpaceOnUse"><rect width={80} height={80} fill={fill} /><path d="M0 0 H80 V80" stroke={ln} strokeWidth={sw} fill="none" /></pattern>;
    case "stripes":
      return <pattern id={id} width={70} height={70} patternUnits="userSpaceOnUse"><rect width={70} height={70} fill={fill} /><rect width={22} height={70} fill={shade(fill, -0.08)} /><path d="M22 0 V70" stroke={ln} strokeWidth={2} /></pattern>;
    case "planks":
      return <pattern id={id} width={300} height={56} patternUnits="userSpaceOnUse"><rect width={300} height={56} fill={fill} /><path d="M0 0 H300 M0 28 H300 M120 0 V28 M240 28 V56 M40 28 V56" stroke={ln} strokeWidth={sw} /><path d="M160 12 q20 -4 40 0" stroke={shade(fill, -0.12)} strokeWidth={2} fill="none" /></pattern>;
    case "checker":
      return <pattern id={id} width={120} height={120} patternUnits="userSpaceOnUse"><rect width={120} height={120} fill={fill} /><rect width={60} height={60} fill={shade(fill, -0.2)} /><rect x={60} y={60} width={60} height={60} fill={shade(fill, -0.2)} /></pattern>;
    case "carpet":
      return <pattern id={id} width={60} height={60} patternUnits="userSpaceOnUse"><rect width={60} height={60} fill={fill} /><path d="M0 30 L30 0 L60 30 L30 60 Z" fill="none" stroke={ln} strokeWidth={2} /></pattern>;
    case "concrete":
      return <pattern id={id} width={240} height={120} patternUnits="userSpaceOnUse"><rect width={240} height={120} fill={fill} /><path d="M0 0 H240 M0 0 V120" stroke={ln} strokeWidth={sw} /><circle cx={80} cy={40} r={3} fill={ln} /><circle cx={170} cy={90} r={4} fill={ln} /></pattern>;
    case "grass":
      return <pattern id={id} width={140} height={70} patternUnits="userSpaceOnUse"><rect width={140} height={70} fill={fill} /><path d="M20 50 l6 -16 l6 16 M90 30 l5 -14 l5 14 M60 64 l4 -10 l4 10" stroke={ln} strokeWidth={3} fill="none" /></pattern>;
    case "furrows":
      return <pattern id={id} width={160} height={46} patternUnits="userSpaceOnUse"><rect width={160} height={46} fill={fill} /><path d="M0 40 Q40 32 80 40 T160 40" stroke={ln} strokeWidth={4} fill="none" /></pattern>;
    case "sand":
      return <pattern id={id} width={200} height={60} patternUnits="userSpaceOnUse"><rect width={200} height={60} fill={fill} /><path d="M10 40 q30 -10 60 0 M110 20 q30 -10 60 0" stroke={ln} strokeWidth={3} fill="none" /><circle cx={160} cy={50} r={4} fill={ln} /></pattern>;
    case "water":
      return <pattern id={id} width={160} height={50} patternUnits="userSpaceOnUse"><rect width={160} height={50} fill={fill} /><path d="M10 30 q20 -12 40 0 t40 0" stroke={shade(fill, 0.25)} strokeWidth={4} fill="none" /></pattern>;
    case "road":
      return <pattern id={id} width={260} height={80} patternUnits="userSpaceOnUse"><rect width={260} height={80} fill={fill} /><rect x={30} y={36} width={110} height={10} fill="#E8E1C8" /></pattern>;
    default: // panels
      return <pattern id={id} width={180} height={300} patternUnits="userSpaceOnUse"><rect width={180} height={300} fill={fill} /><rect x={20} y={24} width={140} height={250} fill="none" stroke={ln} strokeWidth={sw} rx={4} /><path d="M0 0 V300" stroke={ln} strokeWidth={sw} /></pattern>;
  }
};
