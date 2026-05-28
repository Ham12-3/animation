import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig, Img } from "remotion";

const CLAUDE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Claude_AI_logo.svg/960px-Claude_AI_logo.svg.png";
const OPENAI_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/OpenAI_Logo.svg/960px-OpenAI_Logo.svg.png";

export const LLMConnect: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 14 }, durationInFrames: 20 });
  const opacity = interpolate(frame, [0, 6, 50, 58], [0, 1, 1, 0]);
  const glow = 0.5 + 0.5 * Math.sin((frame / fps) * Math.PI * 1.8);

  return (
    <div style={{
      position: "absolute",
      bottom: 105,
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
        padding: "14px 22px",
        border: "1.5px solid rgba(96,165,250,0.4)",
        boxShadow: `0 8px 40px rgba(0,0,0,0.6), 0 0 ${20 + glow * 12}px rgba(96,165,250,0.2)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        minWidth: 270,
      }}>
        <span style={{ color: "#60a5fa", fontFamily: "sans-serif", fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase" }}>
          Connect your LLM
        </span>

        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          {/* Claude */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: "#CC785C",
              display: "flex", alignItems: "center", justifyContent: "center",
              padding: 6,
              boxShadow: "0 4px 16px rgba(204,120,92,0.45)",
            }}>
              <Img src={CLAUDE_URL} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
            </div>
            <span style={{ color: "#CC785C", fontFamily: "sans-serif", fontSize: 10, fontWeight: 700 }}>Claude</span>
          </div>

          <span style={{ color: "#475569", fontFamily: "sans-serif", fontSize: 18 }}>or</span>

          {/* OpenAI */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: "#10a37f",
              display: "flex", alignItems: "center", justifyContent: "center",
              padding: 8,
              boxShadow: "0 4px 16px rgba(16,163,127,0.45)",
            }}>
              <Img src={OPENAI_URL} style={{ width: "100%", height: "100%", objectFit: "contain", filter: "brightness(0) invert(1)" }} />
            </div>
            <span style={{ color: "#10a37f", fontFamily: "sans-serif", fontSize: 10, fontWeight: 700 }}>OpenAI</span>
          </div>

          <span style={{ color: "#475569", fontFamily: "sans-serif", fontSize: 18 }}>or</span>

          {/* Local */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: "#1e293b",
              border: "1.5px solid #334155",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 26,
            }}>
              🤖
            </div>
            <span style={{ color: "#94a3b8", fontFamily: "sans-serif", fontSize: 10, fontWeight: 700 }}>Local</span>
          </div>
        </div>

        <span style={{ color: "#64748b", fontFamily: "sans-serif", fontSize: 11 }}>
          You choose the model
        </span>
      </div>
    </div>
  );
};
