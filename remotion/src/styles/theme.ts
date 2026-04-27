export const COLORS = {
  bg: "#0a0a0f",
  bgCard: "rgba(255, 255, 255, 0.04)",
  bgCardHover: "rgba(255, 255, 255, 0.08)",
  border: "rgba(255, 255, 255, 0.08)",
  text: "#e4e4e7",
  textMuted: "#71717a",
  textDim: "#52525b",
  accent: "#00D4FF",
  accentGlow: "rgba(0, 212, 255, 0.3)",
  neonGreen: "#00FF88",
  danger: "#FF4444",
  dangerGlow: "rgba(255, 68, 68, 0.3)",

  buffer: "#4C72B0",
  bufferGlow: "rgba(76, 114, 176, 0.4)",
  summary: "#DD8452",
  summaryGlow: "rgba(221, 132, 82, 0.4)",
  qdrant: "#55A868",
  qdrantGlow: "rgba(85, 168, 104, 0.4)",
  pgvector: "#C44E52",
  pgvectorGlow: "rgba(196, 78, 82, 0.4)",
} as const;

export const BACKEND_COLORS: Record<string, string> = {
  buffer: COLORS.buffer,
  summary: COLORS.summary,
  qdrant: COLORS.qdrant,
  pgvector: COLORS.pgvector,
};

export const BACKEND_GLOWS: Record<string, string> = {
  buffer: COLORS.bufferGlow,
  summary: COLORS.summaryGlow,
  qdrant: COLORS.qdrantGlow,
  pgvector: COLORS.pgvectorGlow,
};

export const FONTS = {
  mono: "'JetBrains Mono', 'Fira Code', monospace",
  body: "'Inter', -apple-system, sans-serif",
};

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
