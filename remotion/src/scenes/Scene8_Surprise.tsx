import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { GlassCard } from "../components/GlassCard";
import { FadeTransition } from "../components/FadeTransition";
import { BACKENDS, RECALL_BY_SEED_TURN_AT_50 } from "../data/benchmarkData";

const SENSITIVE_FACTS = [
  { turn: 30, fact: "Wi-Fi password", index: 6 },
  { turn: 45, fact: "Bank PIN", index: 9 },
];

export const Scene8_Surprise: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <FadeTransition durationFrames={1350}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, #1a0d0d 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: Highlight failures (0-25s / 0-750f) */}
        <div
          style={{
            opacity: interpolate(frame, [0, 15, 700, 750], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: "50px 80px",
          }}
        >
          <AnimatedText
            text="The Unexpected Finding"
            startFrame={0}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
          />

          <div
            style={{
              display: "flex",
              gap: 40,
              justifyContent: "center",
              marginTop: 60,
            }}
          >
            {SENSITIVE_FACTS.map((sf, si) => (
              <GlassCard
                key={sf.turn}
                startFrame={60 + si * 40}
                width={500}
                padding={32}
                borderColor={COLORS.danger + "66"}
                glowColor={COLORS.dangerGlow}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                    marginBottom: 20,
                  }}
                >
                  <div style={{ fontSize: 36 }}>🔒</div>
                  <div>
                    <div
                      style={{
                        fontFamily: FONTS.mono,
                        fontSize: 14,
                        color: COLORS.danger,
                        marginBottom: 4,
                      }}
                    >
                      Turn {sf.turn}
                    </div>
                    <div
                      style={{
                        fontFamily: FONTS.body,
                        fontSize: 24,
                        fontWeight: 600,
                        color: COLORS.text,
                      }}
                    >
                      {sf.fact}
                    </div>
                  </div>
                </div>

                {/* Per-backend results */}
                {BACKENDS.map((b, bi) => {
                  const val = RECALL_BY_SEED_TURN_AT_50[b][sf.index];
                  const rowOpacity = interpolate(
                    frame,
                    [150 + si * 40 + bi * 15, 165 + si * 40 + bi * 15],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  );
                  const failed = val < 50;
                  return (
                    <div
                      key={b}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "8px 0",
                        borderBottom: `1px solid ${COLORS.border}`,
                        opacity: rowOpacity,
                      }}
                    >
                      <span
                        style={{
                          fontFamily: FONTS.mono,
                          fontSize: 16,
                          color: BACKEND_COLORS[b],
                        }}
                      >
                        {b}
                      </span>
                      <span
                        style={{
                          fontFamily: FONTS.mono,
                          fontSize: 18,
                          fontWeight: 700,
                          color: failed ? COLORS.danger : COLORS.neonGreen,
                        }}
                      >
                        {val}%{" "}
                        {failed ? "✗" : "✓"}
                      </span>
                    </div>
                  );
                })}
              </GlassCard>
            ))}
          </div>

          <AnimatedText
            text="Every backend failed — including buffer (data was in the prompt!)"
            startFrame={400}
            fontSize={24}
            color={COLORS.danger}
            glow
            glowColor={COLORS.dangerGlow}
            textAlign="center"
            style={{ marginTop: 40 }}
          />
        </div>

        {/* Phase 2: Explanation (25-45s / 750-1350f) */}
        <div
          style={{
            opacity: interpolate(frame, [750, 790], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "0 120px",
          }}
        >
          <div style={{ fontSize: 80, marginBottom: 30 }}>🛡️</div>

          <AnimatedText
            text="Not a memory failure —"
            startFrame={800}
            fontSize={44}
            fontWeight={600}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={25}
          />
          <AnimatedText
            text="a safety behavior."
            startFrame={850}
            fontSize={52}
            fontWeight={700}
            color={COLORS.accent}
            glow
            textAlign="center"
          />

          <div
            style={{
              marginTop: 50,
              maxWidth: 900,
              opacity: interpolate(frame, [920, 950], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            <GlassCard startFrame={920} padding={32}>
              <div
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 22,
                  color: COLORS.textMuted,
                  lineHeight: 1.6,
                  textAlign: "center",
                }}
              >
                Claude recognizes sensitive data (passwords, PINs) and{" "}
                <span style={{ color: COLORS.text, fontWeight: 600 }}>
                  declines to repeat them
                </span>
                , even when explicitly provided in the conversation history.
              </div>
            </GlassCard>
          </div>

          <AnimatedText
            text="Lesson: don't use sensitive data in memory benchmarks"
            startFrame={1050}
            fontSize={22}
            color={COLORS.textMuted}
            textAlign="center"
            style={{ marginTop: 30 }}
          />
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
