import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";

export const LocalMachine: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 14 }, durationInFrames: 20 });
  const opacity = interpolate(frame, [0, 6, 48, 58], [0, 1, 1, 0]);
  const blink = Math.floor((frame / fps) * 2) % 2 === 0;

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
        border: "1.5px solid rgba(52,211,153,0.4)",
        boxShadow: "0 8px 40px rgba(0,0,0,0.6)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        minWidth: 270,
      }}>
        <span style={{ color: "#34d399", fontFamily: "sans-serif", fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase" }}>
          Runs on your machine
        </span>

        {/* Laptop SVG illustration */}
        <svg width="100" height="70" viewBox="0 0 100 70" fill="none">
          {/* screen */}
          <rect x="15" y="5" width="70" height="44" rx="4" fill="#1e293b" stroke="#334155" strokeWidth="1.5"/>
          <rect x="20" y="10" width="60" height="34" rx="2" fill="#0f172a"/>
          {/* terminal lines */}
          <text x="24" y="22" fill="#34d399" fontSize="6" fontFamily="monospace">$ openclaw start</text>
          <text x="24" y="32" fill="#60a5fa" fontSize="6" fontFamily="monospace">  Gateway: OK</text>
          <text x="24" y="40" fill="#34d399" fontSize="6" fontFamily="monospace">  LLM: Connected{blink ? "█" : " "}</text>
          {/* base */}
          <path d="M5 52 Q5 49 15 49 L85 49 Q95 49 95 52 L95 54 Q95 56 85 56 L15 56 Q5 56 5 54 Z" fill="#334155"/>
          <rect x="38" y="49" width="24" height="3" rx="1.5" fill="#475569"/>
        </svg>

        {/* Stats */}
        <div style={{ display: "flex", gap: 12 }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <span style={{ color: "#34d399", fontFamily: "sans-serif", fontSize: 14, fontWeight: 800 }}>100%</span>
            <span style={{ color: "#64748b", fontFamily: "sans-serif", fontSize: 10 }}>Private</span>
          </div>
          <div style={{ width: 1, background: "#1e293b" }}/>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <span style={{ color: "#60a5fa", fontFamily: "sans-serif", fontSize: 14, fontWeight: 800 }}>Free</span>
            <span style={{ color: "#64748b", fontFamily: "sans-serif", fontSize: 10 }}>Open Source</span>
          </div>
          <div style={{ width: 1, background: "#1e293b" }}/>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <span style={{ color: "#a78bfa", fontFamily: "sans-serif", fontSize: 14, fontWeight: 800 }}>375k★</span>
            <span style={{ color: "#64748b", fontFamily: "sans-serif", fontSize: 10 }}>GitHub</span>
          </div>
        </div>
      </div>
    </div>
  );
};
