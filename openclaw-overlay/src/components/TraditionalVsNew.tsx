import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";

export const TraditionalVsNew: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 14 }, durationInFrames: 18 });
  const opacity = interpolate(frame, [0, 6, 44, 50], [0, 1, 1, 0]);

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
        padding: "12px 18px",
        border: "1.5px solid rgba(255,255,255,0.1)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.55)",
        display: "flex",
        gap: 12,
        alignItems: "stretch",
        minWidth: 280,
      }}>
        {/* Old */}
        <div style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 6,
          padding: "8px 6px",
          background: "rgba(239,68,68,0.1)",
          borderRadius: 12,
          border: "1px solid rgba(239,68,68,0.25)",
        }}>
          <span style={{ fontSize: 20 }}>🖥️</span>
          <span style={{ color: "#ef4444", fontFamily: "sans-serif", fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5 }}>Old way</span>
          <span style={{ color: "#94a3b8", fontFamily: "sans-serif", fontSize: 10, textAlign: "center", lineHeight: 1.4 }}>
            Separate app for every AI tool
          </span>
        </div>

        {/* VS */}
        <div style={{ display: "flex", alignItems: "center" }}>
          <span style={{ color: "#475569", fontFamily: "sans-serif", fontWeight: 800, fontSize: 12 }}>VS</span>
        </div>

        {/* New */}
        <div style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 6,
          padding: "8px 6px",
          background: "rgba(124,58,237,0.15)",
          borderRadius: 12,
          border: "1px solid rgba(124,58,237,0.35)",
        }}>
          <span style={{ fontSize: 20 }}>💬</span>
          <span style={{ color: "#a78bfa", fontFamily: "sans-serif", fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5 }}>OpenClaw</span>
          <span style={{ color: "#94a3b8", fontFamily: "sans-serif", fontSize: 10, textAlign: "center", lineHeight: 1.4 }}>
            Chat apps you already use
          </span>
        </div>
      </div>
    </div>
  );
};
