import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { GlassCard } from "../components/GlassCard";
import { FadeTransition } from "../components/FadeTransition";
import { QDRANT_VS_PGVECTOR } from "../data/benchmarkData";

export const Scene7_QdrantVsPgvector: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={1350}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: Comparison table (0-35s / 0-1050f) */}
        <div
          style={{
            opacity: interpolate(frame, [0, 15, 1000, 1050], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: "50px 100px",
          }}
        >
          <AnimatedText
            text="Qdrant vs pgvector"
            startFrame={0}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
          />
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 22,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 8,
              opacity: interpolate(frame, [20, 40], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            Does the vector database choice matter?
          </div>

          {/* VS divider + comparison */}
          <div
            style={{
              display: "flex",
              gap: 40,
              marginTop: 50,
              justifyContent: "center",
              alignItems: "flex-start",
            }}
          >
            {/* Qdrant side */}
            <GlassCard startFrame={60} width={380} padding={28} glowColor={COLORS.qdrantGlow}>
              <div
                style={{
                  fontFamily: FONTS.mono,
                  fontSize: 28,
                  fontWeight: 700,
                  color: COLORS.qdrant,
                  textAlign: "center",
                  marginBottom: 24,
                }}
              >
                🔍 Qdrant
              </div>
              {QDRANT_VS_PGVECTOR.map((row, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "10px 0",
                    borderBottom: `1px solid ${COLORS.border}`,
                    opacity: interpolate(
                      frame,
                      [120 + i * 30, 135 + i * 30],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                >
                  <span style={{ fontFamily: FONTS.body, fontSize: 16, color: COLORS.textMuted }}>
                    {row.metric}
                  </span>
                  <span style={{ fontFamily: FONTS.mono, fontSize: 16, color: COLORS.text, fontWeight: 600 }}>
                    {row.qdrant}
                  </span>
                </div>
              ))}
            </GlassCard>

            {/* VS */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: 400,
                opacity: interpolate(frame, [80, 100], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              <div
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 48,
                  fontWeight: 800,
                  color: COLORS.textDim,
                  textShadow: `0 0 30px ${COLORS.accentGlow}`,
                }}
              >
                VS
              </div>
            </div>

            {/* pgvector side */}
            <GlassCard startFrame={80} width={380} padding={28} glowColor={COLORS.pgvectorGlow}>
              <div
                style={{
                  fontFamily: FONTS.mono,
                  fontSize: 28,
                  fontWeight: 700,
                  color: COLORS.pgvector,
                  textAlign: "center",
                  marginBottom: 24,
                }}
              >
                🐘 pgvector
              </div>
              {QDRANT_VS_PGVECTOR.map((row, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "10px 0",
                    borderBottom: `1px solid ${COLORS.border}`,
                    opacity: interpolate(
                      frame,
                      [120 + i * 30, 135 + i * 30],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                >
                  <span style={{ fontFamily: FONTS.body, fontSize: 16, color: COLORS.textMuted }}>
                    {row.metric}
                  </span>
                  <span style={{ fontFamily: FONTS.mono, fontSize: 16, color: COLORS.text, fontWeight: 600 }}>
                    {row.pgvector}
                  </span>
                </div>
              ))}
            </GlassCard>
          </div>

          {/* Winner badges */}
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 20,
              marginTop: 30,
            }}
          >
            {QDRANT_VS_PGVECTOR.map((row, i) => {
              const badgeOpacity = interpolate(
                frame,
                [350 + i * 30, 370 + i * 30],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );
              return (
                <div
                  key={i}
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 13,
                    color: COLORS.neonGreen,
                    background: "rgba(0,255,136,0.08)",
                    border: "1px solid rgba(0,255,136,0.2)",
                    borderRadius: 6,
                    padding: "4px 10px",
                    opacity: badgeOpacity,
                  }}
                >
                  ={row.winner}
                </div>
              );
            })}
          </div>
        </div>

        {/* Phase 2: Verdict (35-45s / 1050-1350f) */}
        <div
          style={{
            position: "absolute",
            bottom: 80,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: interpolate(frame, [1050, 1080], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <AnimatedText
            text="No meaningful difference at this scale"
            startFrame={1060}
            fontSize={36}
            fontWeight={700}
            color={COLORS.accent}
            glow
            textAlign="center"
            mode="wordByWord"
            durationFrames={30}
          />
          <AnimatedText
            text="Already run PostgreSQL? Just add pgvector."
            startFrame={1130}
            fontSize={24}
            color={COLORS.textMuted}
            textAlign="center"
          />
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
