import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { GlassCard } from "../components/GlassCard";
import { FadeTransition } from "../components/FadeTransition";

const RECS = [
  {
    useCase: "Production chatbot (cost-sensitive)",
    backend: "pgvector / qdrant",
    color: COLORS.qdrant,
    icon: "💰",
    detail: "82% recall at 1/10th the cost",
  },
  {
    useCase: "Short conversations (< 15 turns)",
    backend: "buffer",
    color: COLORS.buffer,
    icon: "⚡",
    detail: "Simple, perfect recall, low cost at small scale",
  },
  {
    useCase: "Already running PostgreSQL",
    backend: "pgvector",
    color: COLORS.pgvector,
    icon: "🐘",
    detail: "Zero extra infrastructure — just add the extension",
  },
  {
    useCase: "Millions of vectors at scale",
    backend: "qdrant",
    color: COLORS.qdrant,
    icon: "🔍",
    detail: "Purpose-built vector search engine",
  },
  {
    useCase: "NOT recommended",
    backend: "summary",
    color: COLORS.danger,
    icon: "⛔",
    detail: "42% recall, slowest, destroys details",
  },
];

export const Scene9_Recommendations: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={1350}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 40%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        <AnimatedText
          text="What Should You Use?"
          startFrame={0}
          fontSize={48}
          fontWeight={700}
          textAlign="center"
        />

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 20,
            marginTop: 50,
            maxWidth: 1200,
            margin: "50px auto 0",
          }}
        >
          {RECS.map((rec, i) => {
            const cardStart = 60 + i * 60;
            const isLast = i === RECS.length - 1;

            return (
              <div
                key={i}
                style={{
                  opacity: interpolate(frame, [cardStart, cardStart + 20], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  }),
                  transform: `translateX(${interpolate(
                    frame,
                    [cardStart, cardStart + 20],
                    [-40, 0],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  )}px)`,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 24,
                    padding: "20px 28px",
                    background: isLast ? "rgba(255,68,68,0.06)" : COLORS.bgCard,
                    border: `1px solid ${isLast ? COLORS.danger + "44" : COLORS.border}`,
                    borderRadius: 14,
                    backdropFilter: "blur(10px)",
                  }}
                >
                  <div style={{ fontSize: 36, flexShrink: 0 }}>{rec.icon}</div>

                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontFamily: FONTS.body,
                        fontSize: 20,
                        color: COLORS.text,
                        fontWeight: 600,
                        marginBottom: 4,
                      }}
                    >
                      {rec.useCase}
                    </div>
                    <div
                      style={{
                        fontFamily: FONTS.body,
                        fontSize: 15,
                        color: COLORS.textMuted,
                      }}
                    >
                      {rec.detail}
                    </div>
                  </div>

                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 20,
                      fontWeight: 700,
                      color: rec.color,
                      padding: "6px 18px",
                      background: `${rec.color}15`,
                      border: `1px solid ${rec.color}44`,
                      borderRadius: 10,
                      textDecoration: isLast ? "line-through" : undefined,
                      textShadow: isLast ? undefined : `0 0 10px ${rec.color}44`,
                    }}
                  >
                    {rec.backend}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
