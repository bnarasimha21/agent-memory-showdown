import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { AnimatedCounter } from "../components/AnimatedCounter";
import { AnimatedLineChart } from "../components/AnimatedLineChart";
import { BackendBadge } from "../components/BackendBadge";
import { GlassCard } from "../components/GlassCard";
import { FadeTransition } from "../components/FadeTransition";
import {
  BACKENDS,
  RECALL_AT_TURN_15,
  RECALL_AT_TURN_50,
  RECALL_BY_SEED_TURN_AT_50,
  SEED_TURNS,
  BACKEND_LABELS,
} from "../data/benchmarkData";

export const Scene4_Recall: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={3150}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, #0d1525 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: Memory Decay Curve (0-30s / 0-900f) */}
        <div
          style={{
            opacity: interpolate(frame, [0, 15, 850, 900], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: 60,
          }}
        >
          <AnimatedText
            text="Can It Remember?"
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
            Recall accuracy at turn 15 vs turn 50
          </div>

          <div style={{ display: "flex", justifyContent: "center", marginTop: 30 }}>
            <AnimatedLineChart
              series={BACKENDS.map((b) => ({
                label: b,
                data: [RECALL_AT_TURN_15[b], RECALL_AT_TURN_50[b]],
                color: BACKEND_COLORS[b],
              }))}
              startFrame={60}
              drawDuration={120}
              chartWidth={1000}
              chartHeight={500}
              xLabels={["Turn 15", "Turn 50"]}
              yMax={105}
              yLabel="Recall %"
            />
          </div>
        </div>

        {/* Phase 2: Scoreboard (30-65s / 900-1950f) */}
        <div
          style={{
            opacity: interpolate(frame, [900, 930, 1900, 1950], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: "60px 120px",
          }}
        >
          <AnimatedText
            text="Recall at Turn 50"
            startFrame={910}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
          />

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 24,
              marginTop: 60,
              maxWidth: 1000,
              margin: "60px auto 0",
            }}
          >
            {BACKENDS.map((b, i) => {
              const rowStart = 960 + i * 60;
              const pct = RECALL_AT_TURN_50[b];
              const color = BACKEND_COLORS[b];
              const isSummary = b === "summary";

              const barWidth = spring({
                frame: Math.max(0, frame - rowStart),
                fps,
                config: { damping: 18, stiffness: 60 },
              });

              return (
                <div
                  key={b}
                  style={{
                    opacity: interpolate(frame, [rowStart, rowStart + 15], [0, 1], {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                    }),
                    display: "flex",
                    alignItems: "center",
                    gap: 24,
                  }}
                >
                  <div style={{ width: 140 }}>
                    <BackendBadge name={b} fontSize={18} />
                  </div>

                  <div
                    style={{
                      flex: 1,
                      height: 48,
                      background: COLORS.bgCard,
                      borderRadius: 8,
                      overflow: "hidden",
                      position: "relative",
                      border: `1px solid ${COLORS.border}`,
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${pct * barWidth}%`,
                        background: isSummary
                          ? `linear-gradient(90deg, ${color}, ${COLORS.danger})`
                          : `linear-gradient(90deg, ${color}88, ${color})`,
                        borderRadius: 7,
                        boxShadow: isSummary
                          ? `0 0 20px ${COLORS.dangerGlow}`
                          : `0 0 20px ${color}33`,
                      }}
                    />
                  </div>

                  <div style={{ width: 100, textAlign: "right" }}>
                    <AnimatedCounter
                      value={pct}
                      startFrame={rowStart}
                      durationFrames={50}
                      suffix="%"
                      fontSize={36}
                      color={isSummary ? COLORS.danger : color}
                      fontWeight={700}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Commentary */}
          <AnimatedText
            text='Summary: 42% — it forgot more than it remembers'
            startFrame={1250}
            fontSize={24}
            color={COLORS.danger}
            glow
            glowColor={COLORS.dangerGlow}
            textAlign="center"
            style={{ marginTop: 50 }}
          />
        </div>

        {/* Phase 3: Grouped bar chart — recall by seed turn (65-105s / 1950-3150f) */}
        <div
          style={{
            opacity: interpolate(frame, [1950, 1990], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: "50px 40px",
          }}
        >
          <AnimatedText
            text="Recall at Turn 50 — By Fact Seed Turn"
            startFrame={1960}
            fontSize={40}
            fontWeight={700}
            textAlign="center"
          />

          <div style={{ position: "relative", marginTop: 40, height: 600, width: "100%" }}>
            {/* Grid and bars */}
            {SEED_TURNS.map((seedTurn, si) => {
              const groupX = 80 + si * 170;
              const groupDelay = 2020 + si * 20;

              return (
                <div key={seedTurn}>
                  {/* Seed turn label */}
                  <div
                    style={{
                      position: "absolute",
                      left: groupX,
                      bottom: 10,
                      width: 160,
                      textAlign: "center",
                      fontFamily: FONTS.mono,
                      fontSize: 14,
                      color: COLORS.textMuted,
                      opacity: interpolate(frame, [groupDelay, groupDelay + 10], [0, 1], {
                        extrapolateLeft: "clamp",
                        extrapolateRight: "clamp",
                      }),
                    }}
                  >
                    Turn {seedTurn}
                  </div>

                  {/* 4 bars per group */}
                  {BACKENDS.map((b, bi) => {
                    const val = RECALL_BY_SEED_TURN_AT_50[b][si];
                    const barDelay = groupDelay + bi * 5;
                    const barH = spring({
                      frame: Math.max(0, frame - barDelay),
                      fps,
                      config: { damping: 16, stiffness: 80 },
                    });
                    const color = BACKEND_COLORS[b];
                    const barWidth = 32;
                    const barLeft = groupX + 16 + bi * (barWidth + 4);
                    const maxBarHeight = 400;
                    const height = (val / 100) * maxBarHeight * barH;

                    return (
                      <div
                        key={b}
                        style={{
                          position: "absolute",
                          left: barLeft,
                          bottom: 40,
                          width: barWidth,
                          height,
                          background: val === 0
                            ? `${COLORS.danger}44`
                            : `linear-gradient(180deg, ${color}, ${color}88)`,
                          borderRadius: "4px 4px 0 0",
                          boxShadow: val === 0 ? undefined : `0 0 8px ${color}33`,
                        }}
                      >
                        {val === 0 && barH > 0.9 && (
                          <div
                            style={{
                              position: "absolute",
                              top: -20,
                              left: "50%",
                              transform: "translateX(-50%)",
                              fontFamily: FONTS.mono,
                              fontSize: 10,
                              color: COLORS.danger,
                            }}
                          >
                            0%
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}

            {/* Legend */}
            <div
              style={{
                position: "absolute",
                top: 0,
                right: 40,
                display: "flex",
                gap: 20,
                opacity: interpolate(frame, [2000, 2020], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              {BACKENDS.map((b) => (
                <div key={b} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div
                    style={{
                      width: 14,
                      height: 14,
                      borderRadius: 3,
                      background: BACKEND_COLORS[b],
                    }}
                  />
                  <span style={{ fontFamily: FONTS.mono, fontSize: 14, color: COLORS.textMuted }}>
                    {b}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <AnimatedText
            text="Summary destroys new information as it compresses"
            startFrame={2500}
            fontSize={26}
            color={COLORS.summary}
            glow
            glowColor={COLORS.summaryGlow}
            textAlign="center"
            style={{ marginTop: -20 }}
          />
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
