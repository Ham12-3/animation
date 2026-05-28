import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig, Img } from "remotion";

const WA_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/WhatsApp_Logo_green.svg/500px-WhatsApp_Logo_green.svg.png";
const TG_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Telegram_2019_Logo.svg/960px-Telegram_2019_Logo.svg.png";

export const WhatsAppTelegram: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enterWa = spring({ frame, fps, config: { damping: 14, stiffness: 120 }, durationInFrames: 18 });
  const enterTg = spring({ frame: Math.max(0, frame - 8), fps, config: { damping: 14, stiffness: 120 }, durationInFrames: 18 });
  const opacity = interpolate(frame, [0, 6, 50, 60], [0, 1, 1, 0]);

  const arrow = Math.abs(Math.sin((frame / fps) * Math.PI * 1.5)) * 0.5 + 0.5;

  return (
    <div style={{
      position: "absolute",
      bottom: 110,
      left: 0, right: 0,
      display: "flex",
      justifyContent: "center",
      opacity,
      pointerEvents: "none",
    }}>
      <div style={{
        background: "rgba(10,10,30,0.85)",
        borderRadius: 20,
        padding: "14px 20px",
        border: "1.5px solid rgba(255,255,255,0.12)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.55)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        minWidth: 270,
      }}>
        <span style={{ color: "#94a3b8", fontFamily: "sans-serif", fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase" }}>
          Send prompts via
        </span>

        {/* Icons row */}
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          {/* WhatsApp */}
          <div style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
            transform: `translateY(${interpolate(enterWa, [0, 1], [20, 0])}px)`,
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: "#25D366",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 4px 16px rgba(37,211,102,0.45)",
            }}>
              <Img src={WA_URL} style={{ width: 38, height: 38 }} />
            </div>
            <span style={{ color: "#25D366", fontFamily: "sans-serif", fontSize: 11, fontWeight: 700 }}>WhatsApp</span>
          </div>

          {/* Arrow */}
          <span style={{ color: "#a78bfa", fontSize: 22, opacity: arrow }}>→</span>

          {/* Telegram */}
          <div style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
            transform: `translateY(${interpolate(enterTg, [0, 1], [20, 0])}px)`,
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: "#229ED9",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 4px 16px rgba(34,158,217,0.45)",
            }}>
              <Img src={TG_URL} style={{ width: 38, height: 38 }} />
            </div>
            <span style={{ color: "#229ED9", fontFamily: "sans-serif", fontSize: 11, fontWeight: 700 }}>Telegram</span>
          </div>
        </div>

        <span style={{ color: "#64748b", fontFamily: "sans-serif", fontSize: 11 }}>
          Use your favourite chat app
        </span>
      </div>
    </div>
  );
};
