import React from "react";
import { Composition } from "remotion";
import { OpenClawOverlay } from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="OpenClawOverlay"
      component={OpenClawOverlay}
      durationInFrames={1564}  // 62.56s @ 25fps
      fps={25}
      width={480}
      height={852}
    />
  );
};
