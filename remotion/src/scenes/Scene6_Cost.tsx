import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { AnimatedBarChart } from "../components/AnimatedBarChart";
import { FadeTransition } from "../components/FadeTransition";
import { BACKENDS, COST_PER_1K, AVG_TOKENS } from "../data/benchmarkData";

export const Scene6_Cost: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={1800}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 60% 50%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: Cost bar chart (0-40s / 0-1200f) */}
        <div
          style={{
            opacity: interpolate(frame, [0, 15, 1150, 1200], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: "50px 60px",
          }}
        >
          <AnimatedText
            text="Cost per 1,000 Conversations"
            startFrame={0}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
          />

          <div style={{ display: "flex", justifyContent: "center", marginTop: 50 }}>
            <AnimatedBarChart
              data={BACKENDS.map((b) => ({
                label: b,
                value: COST_PER_1K[b],
                displayValue: `$${COST_PER_1K[b].toLocaleString()}`,
                color: BACKEND_COLORS[b],
              }))}
              startFrame={50}
              barWidth={160}
              chartHeight={480}
              chartWidth={1000}
            />
          </div>

          {/* 90% savings badge */}
          <div
            style={{
              position: "absolute",
              top: 280,
              left: "50%",
              transform: "translateX(-50%)",
              opacity: interpolate(frame, [400, 430], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 28,
                fontWeight: 700,
                color: COLORS.neonGreen,
                background: "rgba(0,255,136,0.08)",
                border: `2px solid rgba(0,255,136,0.3)`,
                borderRadius: 12,
                padding: "12px 28px",
                textShadow: `0 0 20px rgba(0,255,136,0.4)`,
                boxShadow: `0 0 30px rgba(0,255,136,0.15)`,
              }}
            >
              90% cost reduction
            </div>
          </div>

          {/* Token counts below */}
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 60,
              marginTop: 20,
              opacity: interpolate(frame, [500, 530], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            {BACKENDS.map((b) => (
              <div key={b} style={{ textAlign: "center" }}>
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 14,
                    color: COLORS.textMuted,
                  }}
                >
                  {b}
                </div>
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 18,
                    color: BACKEND_COLORS[b],
                    marginTop: 4,
                  }}
                >
                  {(AVG_TOKENS[b] / 1000).toFixed(0)}K tokens/run
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Phase 2: $1 vs $10 visual (40-60s / 1200-1800f) */}
        <div
          style={{
            opacity: interpolate(frame, [1200, 1240], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <AnimatedText
            text="For every $1 on vector memory..."
            startFrame={1240}
            fontSize={40}
            fontWeight={600}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={30}
          />

          <div style={{ display: "flex", alignItems: "center", gap: 80, marginTop: 60 }}>
            {/* Vector side: 1 coin */}
            <div style={{ textAlign: "center" }}>
              <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
                <div
                  style={{
                    width: 80,
                    height: 80,
                    borderRadius: "50%",
                    background: `linear-gradient(135deg, ${COLORS.qdrant}, ${COLORS.neonGreen})`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: FONTS.mono,
                    fontSize: 32,
                    fontWeight: 700,
                    color: "#fff",
                    boxShadow: `0 0 30px ${COLORS.qdrantGlow}`,
                    opacity: interpolate(frame, [1320, 1340], [0, 1], {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                    }),
                    transform: `scale(${spring({
                      frame: Math.max(0, frame - 1320),
                      fps,
                      config: { damping: 12, stiffness: 100 },
                    })})`,
                  }}
                >
                  $1
                </div>
              </div>
              <div
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 20,
                  color: COLORS.qdrant,
                  marginTop: 16,
                }}
              >
                vector memory
              </div>
            </div>

            <div
              style={{
                fontFamily: FONTS.body,
                fontSize: 32,
                color: COLORS.textMuted,
                opacity: interpolate(frame, [1360, 1380], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              vs
            </div>

            {/* Buffer side: 10 coins */}
            <div style={{ textAlign: "center" }}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center", maxWidth: 340 }}>
                {Array.from({ length: 10 }).map((_, i) => {
                  const coinDelay = 1400 + i * 8;
                  return (
                    <div
                      key={i}
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: "50%",
                        background: `linear-gradient(135deg, ${COLORS.buffer}, ${COLORS.buffer}88)`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: FONTS.mono,
                        fontSize: 16,
                        fontWeight: 700,
                        color: "#fff",
                        boxShadow: `0 0 15px ${COLORS.bufferGlow}`,
                        opacity: interpolate(frame, [coinDelay, coinDelay + 10], [0, 1], {
                          extrapolateLeft: "clamp",
                          extrapolateRight: "clamp",
                        }),
                        transform: `scale(${spring({
                          frame: Math.max(0, frame - coinDelay),
                          fps,
                          config: { damping: 12, stiffness: 120 },
                        })})`,
                      }}
                    >
                      $1
                    </div>
                  );
                })}
              </div>
              <div
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 20,
                  color: COLORS.buffer,
                  marginTop: 16,
                }}
              >
                buffer memory
              </div>
            </div>
          </div>

          <AnimatedText
            text="...you'd spend $10 on buffer."
            startFrame={1550}
            fontSize={36}
            fontWeight={700}
            color={COLORS.accent}
            glow
            textAlign="center"
            style={{ marginTop: 50 }}
          />
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
