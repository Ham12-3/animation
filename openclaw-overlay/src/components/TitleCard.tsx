import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig, spring } from "remotion";

export const TitleCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, config: { damping: 14, stiffness: 100 }, durationInFrames: 20 });
  const opacity = interpolate(frame, [0, 8, 40, 50], [0, 1, 1, 0]);

  return (
    <div
      style={{
        position: "absolute",
        top: 0, left: 0, right: 0, bottom: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "flex-start",
        paddingTop: 36,
        opacity,
        pointerEvents: "none",
      }}
    >
      {/* Brand pill */}
      <div
        style={{
          transform: `scale(${scale})`,
          background: "linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)",
          borderRadius: 40,
          paddingLeft: 28,
          paddingRight: 28,
          paddingTop: 10,
          paddingBottom: 10,
          boxShadow: "0 8px 32px rgba(124,58,237,0.55)",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        {/* Claw icon SVG */}
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <path d="M6 22 C6 22 9 12 14 8 C19 4 22 8 20 14 C18 20 14 22 14 22" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
          <path d="M10 24 C10 24 12 16 16 13 C20 10 22 13 20 18" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
          <path d="M14 25 C14 25 15 19 18 17" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
        </svg>
        <span style={{ color: "white", fontFamily: "sans-serif", fontWeight: 800, fontSize: 26, letterSpacing: 1 }}>
          OpenClaw
        </span>
      </div>

      {/* Subtitle */}
      <div style={{
        marginTop: 12,
        background: "rgba(0,0,0,0.55)",
        borderRadius: 16,
        padding: "6px 18px",
        color: "#e2e8f0",
        fontFamily: "sans-serif",
        fontSize: 13,
        fontWeight: 600,
        letterSpacing: 0.5,
      }}>
        AI Agent Gateway
      </div>
    </div>
  );
};
