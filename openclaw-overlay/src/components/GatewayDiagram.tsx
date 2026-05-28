import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";

export const GatewayDiagram: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 16 }, durationInFrames: 18 });
  const opacity = interpolate(frame, [0, 6, 40, 50], [0, 1, 1, 0]);
  const pulse = 1 + 0.06 * Math.sin((frame / fps) * Math.PI * 2);

  return (
    <div style={{
      position: "absolute",
      bottom: 120,
      left: 0, right: 0,
      display: "flex",
      justifyContent: "center",
      opacity,
      transform: `translateY(${interpolate(enter, [0, 1], [40, 0])}px)`,
      pointerEvents: "none",
    }}>
      <div style={{
        background: "rgba(10,10,30,0.82)",
        borderRadius: 20,
        padding: "16px 20px",
        border: "1.5px solid rgba(124,58,237,0.5)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
        minWidth: 260,
      }}>
        <span style={{ color: "#a78bfa", fontFamily: "sans-serif", fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase" }}>
          How OpenClaw Works
        </span>

        {/* Gateway box */}
        <div style={{
          background: "linear-gradient(135deg,#7c3aed,#2563eb)",
          borderRadius: 12,
          padding: "8px 20px",
          color: "white",
          fontFamily: "sans-serif",
          fontWeight: 800,
          fontSize: 15,
          transform: `scale(${pulse})`,
          boxShadow: "0 0 18px rgba(124,58,237,0.6)",
        }}>
          🌐 OpenClaw Gateway
        </div>

        <svg width="20" height="20" viewBox="0 0 20 20" fill="#a78bfa">
          <path d="M10 0 L10 20 M10 20 L5 14 M10 20 L15 14" stroke="#a78bfa" strokeWidth="2" fill="none" strokeLinecap="round"/>
        </svg>

        <span style={{ color: "#94a3b8", fontFamily: "sans-serif", fontSize: 12 }}>
          Routes your AI prompts
        </span>
      </div>
    </div>
  );
};
