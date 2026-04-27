import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { GlassCard } from "../components/GlassCard";
import { FadeTransition } from "../components/FadeTransition";

const MINI_STATS = [
  { label: "Recall", buffer: "90%", vector: "82%", summary: "42%" },
  { label: "Latency", buffer: "10.3s", vector: "7.0s", summary: "36.0s" },
  { label: "Cost/1K", buffer: "$4,303", vector: "$416", summary: "$2,256" },
];

export const Scene10_Closing: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={900} fadeOutFrames={0}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, #0d1525 0%, ${COLORS.bg} 70%)`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: 80,
        }}
      >
        {/* Phase 1: Mini stats grid (0-15s / 0-450f) */}
        <div
          style={{
            display: "flex",
            gap: 30,
            marginBottom: 60,
            opacity: interpolate(frame, [0, 20, 400, 450], [0, 1, 1, 0.6], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          {MINI_STATS.map((stat, i) => (
            <GlassCard key={i} startFrame={i * 15} padding={24} width={320}>
              <div
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 16,
                  color: COLORS.textMuted,
                  textAlign: "center",
                  marginBottom: 16,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: 2,
                }}
              >
                {stat.label}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                {[
                  { label: "buffer", val: stat.buffer, color: COLORS.buffer },
                  { label: "vector", val: stat.vector, color: COLORS.qdrant },
                  { label: "summary", val: stat.summary, color: COLORS.summary },
                ].map((col) => (
                  <div key={col.label} style={{ textAlign: "center", flex: 1 }}>
                    <div
                      style={{
                        fontFamily: FONTS.mono,
                        fontSize: 22,
                        fontWeight: 700,
                        color: col.color,
                      }}
                    >
                      {col.val}
                    </div>
                    <div
                      style={{
                        fontFamily: FONTS.mono,
                        fontSize: 11,
                        color: COLORS.textDim,
                        marginTop: 4,
                      }}
                    >
                      {col.label}
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          ))}
        </div>

        {/* Phase 2: Tagline (15-25s / 450-750f) */}
        <div
          style={{
            opacity: interpolate(frame, [450, 490], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            transform: `scale(${spring({
              frame: Math.max(0, frame - 450),
              fps,
              config: { damping: 12, stiffness: 80 },
            })})`,
            textAlign: "center",
          }}
        >
          <h1
            style={{
              fontFamily: FONTS.body,
              fontSize: 72,
              fontWeight: 800,
              color: COLORS.text,
              margin: 0,
              letterSpacing: -2,
              textShadow: `0 0 60px ${COLORS.accentGlow}`,
            }}
          >
            Don't guess.{" "}
            <span style={{ color: COLORS.accent }}>Measure.</span>
          </h1>
        </div>

        {/* Phase 3: GitHub + CTA (25-30s / 750-900f) */}
        <div
          style={{
            marginTop: 50,
            textAlign: "center",
            opacity: interpolate(frame, [750, 790], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 22,
              color: COLORS.accent,
              background: `${COLORS.accent}11`,
              border: `1px solid ${COLORS.accent}33`,
              borderRadius: 10,
              padding: "12px 32px",
              display: "inline-block",
              boxShadow: `0 0 30px ${COLORS.accentGlow}`,
            }}
          >
            github.com/bnarasimha21/agent-memory-showdown
          </div>

          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 18,
              color: COLORS.textMuted,
              marginTop: 20,
            }}
          >
            Full code, raw results, and all charts — open source
          </div>
        </div>

        {/* Bottom bar */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: 4,
            background: `linear-gradient(90deg, ${COLORS.buffer}, ${COLORS.summary}, ${COLORS.qdrant}, ${COLORS.pgvector})`,
            opacity: interpolate(frame, [750, 800], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        />
      </AbsoluteFill>
    </FadeTransition>
  );
};
