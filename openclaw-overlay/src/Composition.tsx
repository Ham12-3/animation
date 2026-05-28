import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile } from "remotion";
import { TitleCard } from "./components/TitleCard";
import { GatewayDiagram } from "./components/GatewayDiagram";
import { TraditionalVsNew } from "./components/TraditionalVsNew";
import { WhatsAppTelegram } from "./components/WhatsAppTelegram";
import { GatewayFlow } from "./components/GatewayFlow";
import { LLMConnect } from "./components/LLMConnect";
import { LocalMachine } from "./components/LocalMachine";

const FPS = 25;
const sec = (s: number) => Math.round(s * FPS);

// Each Sequence gives the overlay its own local frame (frame 0 = its start).
// durationInFrames = overlap window so the exit fade has time to finish.
const OVERLAYS: Array<{ from: number; duration: number; Component: React.FC }> = [
  { from: sec(0),  duration: sec(8),  Component: TitleCard },
  { from: sec(6),  duration: sec(10), Component: GatewayDiagram },
  { from: sec(14), duration: sec(10), Component: TraditionalVsNew },
  { from: sec(22), duration: sec(16), Component: WhatsAppTelegram },
  { from: sec(36), duration: sec(12), Component: GatewayFlow },
  { from: sec(46), duration: sec(11), Component: LLMConnect },
  { from: sec(55), duration: sec(9),  Component: LocalMachine },
];

export const OpenClawOverlay: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Original video — plays underneath */}
      <OffthreadVideo src={staticFile("video.mp4")} />

      {/* Overlays — each Sequence shifts frame to 0 at its start */}
      {OVERLAYS.map(({ from, duration, Component }) => (
        <Sequence key={from} from={from} durationInFrames={duration} layout="none">
          <Component />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
