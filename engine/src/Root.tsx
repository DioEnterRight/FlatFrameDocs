import React from "react";
import { Composition } from "remotion";
import { Doc } from "./Doc";
import type { Plan } from "./types";
import demo from "./demo-plan.json";

export const Root: React.FC = () => (
  <Composition
    id="Doc"
    component={Doc as unknown as React.FC<Record<string, unknown>>}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={(demo as unknown as Plan).durationInFrames}
    defaultProps={{ plan: demo as unknown as Plan }}
    calculateMetadata={({ props }) => {
      const plan = (props as { plan: Plan }).plan;
      return { durationInFrames: plan.durationInFrames, fps: plan.fps, width: plan.width, height: plan.height };
    }}
  />
);
