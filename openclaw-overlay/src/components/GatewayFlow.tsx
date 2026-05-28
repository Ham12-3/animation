import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig, Img, staticFile } from "remotion";

const WA_URL = staticFile("whatsapp.svg");
const TG_URL = staticFile("telegram.svg");

export const GatewayFlow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 14 }, durationInFrames: 20 });
  const opacity = interpolate(frame, [0, 6, 50, 58], [0, 1, 1, 0]);
  // animated travelling dot along the path
  const dot = (frame / fps) % 1.6; // repeats every 1.6s

  const dotX = interpolate(dot, [0, 0.8, 1.6], [20, 130, 240], { extrapolateRight: "clamp" });

  return (
    <div style={{
      position: "absolute",
      bottom: 100,
      left: 0, right: 0,
      display: "flex",
      justifyContent: "center",
      opacity,
      transform: `translateY(${interpolate(enter, [0, 1], [50, 0])}px)`,
      pointerEvents: "none",
    }}>
      <div style={{
        background: "rgba(5,5,20,0.88)",
        borderRadius: 20,
        padding: "14px 18px",
        border: "1.5px solid rgba(124,58,237,0.4)",
        boxShadow: "0 8px 40px rgba(0,0,0,0.6)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
        minWidth: 300,
      }}>
        <span style={{ color: "#a78bfa", fontFamily: "sans-serif", fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase" }}>
          Message flow
        </span>

        {/* Flow row */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, position: "relative" }}>
          {/* WhatsApp/Telegram stack */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
            <Img src={WA_URL} style={{ width: 26, height: 26 }} />
            <Img src={TG_URL} style={{ width: 26, height: 26 }} />
          </div>

          {/* Animated arrow track */}
          <div style={{ position: "relative", width: 80, height: 12 }}>
            <div style={{ position: "absolute", top: 5, left: 0, right: 0, height: 2, background: "rgba(167,139,250,0.3)", borderRadius: 1 }}/>
            <div style={{
              position: "absolute",
              top: 2,
              left: Math.min(dotX * 0.27, 60),
              width: 8, height: 8, borderRadius: "50%",
              background: "#a78bfa",
              boxShadow: "0 0 8px #a78bfa",
            }}/>
          </div>

          {/* Gateway */}
          <div style={{
            background: "linear-gradient(135deg,#7c3aed,#2563eb)",
            borderRadius: 10,
            padding: "5px 10px",
            color: "white",
            fontFamily: "sans-serif",
            fontSize: 11,
            fontWeight: 800,
          }}>
            Gateway
          </div>

          {/* Animated arrow track 2 */}
          <div style={{ position: "relative", width: 80, height: 12 }}>
            <div style={{ position: "absolute", top: 5, left: 0, right: 0, height: 2, background: "rgba(96,165,250,0.3)", borderRadius: 1 }}/>
            <div style={{
              position: "absolute",
              top: 2,
              left: Math.min(Math.max(0, (dotX - 60) * 0.27), 60),
              width: 8, height: 8, borderRadius: "50%",
              background: "#60a5fa",
              boxShadow: "0 0 8px #60a5fa",
              opacity: dot > 0.8 ? 1 : 0,
            }}/>
          </div>

          {/* LLM */}
          <div style={{
            background: "rgba(30,30,60,0.9)",
            border: "1.5px solid rgba(96,165,250,0.5)",
            borderRadius: 10,
            padding: "5px 10px",
            color: "#93c5fd",
            fontFamily: "sans-serif",
            fontSize: 11,
            fontWeight: 800,
          }}>
            LLM
          </div>
        </div>

        <span style={{ color: "#64748b", fontFamily: "sans-serif", fontSize: 11 }}>
          Prompt → Gateway → AI → Response
        </span>
      </div>
    </div>
  );
};
