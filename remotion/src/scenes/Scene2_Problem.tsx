import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { GlassCard } from "../components/GlassCard";
import { BackendBadge } from "../components/BackendBadge";
import { AnimatedText } from "../components/AnimatedText";
import { FadeTransition } from "../components/FadeTransition";

const BACKENDS_INFO = [
  {
    name: "buffer",
    title: "Buffer Memory",
    desc: "Shove the entire conversation history into the prompt",
    strength: "Perfect recall (short-term)",
    weakness: "Context explodes, costs skyrocket",
    icon: "📋",
  },
  {
    name: "summary",
    title: "Summary Memory",
    desc: "LLM compresses conversation into a running summary",
    strength: "Lower token usage",
    weakness: "Lossy — facts get summarized away",
    icon: "📝",
  },
  {
    name: "qdrant",
    title: "Vector Memory (Qdrant)",
    desc: "Embed messages, retrieve semantically relevant snippets",
    strength: "Fast, accurate, low cost",
    weakness: "Requires Qdrant service",
    icon: "🔍",
  },
  {
    name: "pgvector",
    title: "Vector Memory (pgvector)",
    desc: "Same idea — using PostgreSQL with pgvector extension",
    strength: "SQL-native, zero extra infra",
    weakness: "Slightly slower at massive scale",
    icon: "🐘",
  },
];

export const Scene2_Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const contextFill = interpolate(frame, [0, 200], [0, 100], {
    extrapolateRight: "clamp",
  });
  const overflow = contextFill > 85;

  return (
    <FadeTransition durationFrames={1800}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 30% 60%, #0d1420 0%, ${COLORS.bg} 70%)`,
          padding: 80,
        }}
      >
        {/* Phase 1: Context window animation (0-15s / 0-450f) */}
        <div
          style={{
            opacity: interpolate(frame, [0, 15, 400, 430], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            position: "absolute",
            inset: 0,
          }}
        >
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 28,
              color: COLORS.textMuted,
              marginBottom: 40,
            }}
          >
            Context Window
          </div>

          <div
            style={{
              width: 700,
              height: 60,
              borderRadius: 12,
              border: `2px solid ${overflow ? COLORS.danger : COLORS.border}`,
              overflow: "hidden",
              position: "relative",
              transition: "border-color 0.3s",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${Math.min(contextFill, 100)}%`,
                background: overflow
                  ? `linear-gradient(90deg, ${COLORS.buffer}, ${COLORS.danger})`
                  : `linear-gradient(90deg, ${COLORS.buffer}88, ${COLORS.buffer})`,
                borderRadius: 10,
                boxShadow: overflow ? `0 0 30px ${COLORS.dangerGlow}` : undefined,
              }}
            />
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                fontFamily: FONTS.mono,
                fontSize: 16,
                color: COLORS.text,
              }}
            >
              {Math.floor(contextFill)}% full
            </div>
          </div>

          {overflow && (
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 20,
                color: COLORS.danger,
                marginTop: 24,
                opacity: interpolate(frame, [175, 195], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
                textShadow: `0 0 20px ${COLORS.dangerGlow}`,
              }}
            >
              ⚠ OVERFLOW — tokens lost
            </div>
          )}

          {/* Messages flowing in */}
          {Array.from({ length: 8 }).map((_, i) => {
            const msgFrame = i * 22;
            const msgOpacity = interpolate(
              frame,
              [msgFrame, msgFrame + 10, msgFrame + 60, msgFrame + 80],
              [0, 0.6, 0.6, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const msgY = interpolate(frame, [msgFrame, msgFrame + 80], [300, 100], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  top: msgY,
                  left: 300 + (i % 3) * 200,
                  background: COLORS.bgCard,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 8,
                  padding: "6px 14px",
                  fontFamily: FONTS.mono,
                  fontSize: 13,
                  color: COLORS.textDim,
                  opacity: msgOpacity,
                }}
              >
                msg_{i + 1}
              </div>
            );
          })}
        </div>

        {/* Phase 2: Backend cards (15-55s / 450-1650f) */}
        <div
          style={{
            opacity: interpolate(frame, [440, 460], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: 60,
          }}
        >
          <AnimatedText
            text="Four Memory Strategies"
            startFrame={450}
            fontSize={44}
            fontWeight={700}
            textAlign="center"
            style={{ marginBottom: 50 }}
          />

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 28,
              maxWidth: 1600,
              margin: "0 auto",
              marginTop: 20,
            }}
          >
            {BACKENDS_INFO.map((b, i) => {
              const cardStart = 500 + i * 90;
              const color = BACKEND_COLORS[b.name];
              return (
                <GlassCard
                  key={b.name}
                  startFrame={cardStart}
                  glowColor={`${color}33`}
                  padding={28}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 14 }}>
                    <span style={{ fontSize: 32 }}>{b.icon}</span>
                    <div>
                      <BackendBadge name={b.name} fontSize={14} />
                      <div
                        style={{
                          fontFamily: FONTS.body,
                          fontSize: 24,
                          fontWeight: 600,
                          color: COLORS.text,
                          marginTop: 4,
                        }}
                      >
                        {b.title}
                      </div>
                    </div>
                  </div>
                  <div
                    style={{
                      fontFamily: FONTS.body,
                      fontSize: 18,
                      color: COLORS.textMuted,
                      marginBottom: 16,
                      lineHeight: 1.4,
                    }}
                  >
                    {b.desc}
                  </div>
                  <div style={{ display: "flex", gap: 12 }}>
                    <span
                      style={{
                        fontSize: 13,
                        fontFamily: FONTS.mono,
                        color: COLORS.neonGreen,
                        background: "rgba(0,255,136,0.08)",
                        padding: "3px 10px",
                        borderRadius: 6,
                      }}
                    >
                      + {b.strength}
                    </span>
                    <span
                      style={{
                        fontSize: 13,
                        fontFamily: FONTS.mono,
                        color: COLORS.danger,
                        background: "rgba(255,68,68,0.08)",
                        padding: "3px 10px",
                        borderRadius: 6,
                      }}
                    >
                      - {b.weakness}
                    </span>
                  </div>
                </GlassCard>
              );
            })}
          </div>
        </div>

        {/* Phase 3: Question (55-60s / 1650-1800f) */}
        <div
          style={{
            position: "absolute",
            bottom: 100,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: interpolate(frame, [1650, 1680], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <AnimatedText
            text="50 turns. 10 planted facts. Who survives?"
            startFrame={1660}
            fontSize={36}
            fontWeight={600}
            color={COLORS.accent}
            glow
            textAlign="center"
            mode="wordByWord"
            durationFrames={40}
          />
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
