// Video constants – matches the actual uploaded video
export const VIDEO_FPS = 25;
export const VIDEO_DURATION_FRAMES = 1564; // 62.56s × 25fps
export const VIDEO_WIDTH = 480;
export const VIDEO_HEIGHT = 852;

// Cue times in seconds → overlay segments
export const CUES = [
  { start: 0,  end: 6,  id: "title" },
  { start: 6,  end: 12, id: "gateway" },
  { start: 12, end: 20, id: "traditional_vs_new" },
  { start: 20, end: 28, id: "channels" },
  { start: 28, end: 38, id: "whatsapp_telegram" },
  { start: 38, end: 46, id: "gateway_flow" },
  { start: 46, end: 55, id: "llm_connect" },
  { start: 55, end: 63, id: "local_machine" },
] as const;

export type CueId = (typeof CUES)[number]["id"];
