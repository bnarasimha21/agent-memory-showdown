import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { AnimatedLineChart } from "../components/AnimatedLineChart";
import { AnimatedBarChart } from "../components/AnimatedBarChart";
import { FadeTransition } from "../components/FadeTransition";
import {
  BACKENDS,
  LATENCY_PER_TURN,
  AVG_LATENCY_MS,
  STD_LATENCY_MS,
  WALL_CLOCK,
} from "../data/benchmarkData";

export const Scene5_Latency: React.FC = () => {
  const frame = useCurrentFrame();

  const latencySeconds = Object.fromEntries(
    BACKENDS.map((b) => [b, LATENCY_PER_TURN[b].map((ms) => ms / 1000)])
  ) as Record<string, number[]>;

  return (
    <FadeTransition durationFrames={2250}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 40% 40%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: Line chart (0-45s / 0-1350f) */}
        <div
          style={{
            opacity: interpolate(frame, [0, 15, 1300, 1350], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: "50px 60px",
          }}
        >
          <AnimatedText
            text="Latency Per Turn"
            startFrame={0}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
          />
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 20,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 4,
              opacity: interpolate(frame, [15, 30], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            How response time changes across 50 conversation turns
          </div>

          <div style={{ display: "flex", justifyContent: "center", marginTop: 20 }}>
            <AnimatedLineChart
              series={BACKENDS.map((b) => ({
                label: b,
                data: latencySeconds[b],
                color: BACKEND_COLORS[b],
              }))}
              startFrame={50}
              drawDuration={150}
              chartWidth={1400}
              chartHeight={550}
              xLabels={["1", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50"]}
              yMax={55}
              yLabel="Latency (seconds)"
              xLabel="Conversation Turn"
            />
          </div>

          {/* 5x annotation */}
          <div
            style={{
              position: "absolute",
              top: 200,
              right: 200,
              opacity: interpolate(frame, [250, 280], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              fontFamily: FONTS.mono,
              fontSize: 22,
              color: COLORS.summary,
              background: `${COLORS.summary}15`,
              border: `1px solid ${COLORS.summary}44`,
              borderRadius: 8,
              padding: "8px 16px",
              textShadow: `0 0 10px ${COLORS.summaryGlow}`,
            }}
          >
            5x slower →
          </div>
        </div>

        {/* Phase 2: Bar chart (45-75s / 1350-2250f) */}
        <div
          style={{
            opacity: interpolate(frame, [1350, 1390], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: "50px 60px",
          }}
        >
          <AnimatedText
            text="Average Latency Per Backend"
            startFrame={1360}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
          />

          <div style={{ display: "flex", justifyContent: "center", marginTop: 50 }}>
            <AnimatedBarChart
              data={BACKENDS.map((b) => ({
                label: b,
                value: AVG_LATENCY_MS[b] / 1000,
                displayValue: `${(AVG_LATENCY_MS[b] / 1000).toFixed(1)}s`,
                color: BACKEND_COLORS[b],
              }))}
              startFrame={1400}
              barWidth={160}
              chartHeight={480}
              chartWidth={1000}
              errorBars={BACKENDS.map((b) => STD_LATENCY_MS[b] / 1000)}
            />
          </div>

          {/* Wall clock times */}
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 60,
              marginTop: 40,
              opacity: interpolate(frame, [1600, 1630], [0, 1], {
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
                    marginBottom: 4,
                  }}
                >
                  {b}
                </div>
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 22,
                    fontWeight: 700,
                    color: BACKEND_COLORS[b],
                  }}
                >
                  {WALL_CLOCK[b]}
                </div>
                <div
                  style={{
                    fontFamily: FONTS.body,
                    fontSize: 12,
                    color: COLORS.textDim,
                  }}
                >
                  wall clock (5 runs)
                </div>
              </div>
            ))}
          </div>
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
