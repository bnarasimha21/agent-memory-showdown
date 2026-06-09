import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
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

// Cue points synced to public/audio/scene05.wav (whisper word-level, 30fps).
const CUE = {
  intro: 0,                    // 0.19s "Now"
  speedWord: 38,               // 1.64s "speed"
  chartTitle: 66,              // 2.58s "This chart"
  chartDrawStart: 201,         // 7.06s (Qdrant/pgvector start being discussed)
  qdrantPgvFlat: 250,          // 8.70s "stay flat"
  sevenSeconds: 285,           // 9.86s
  topK: 445,                   // 15.19s "top-K snippets"
  qdrantPgvEnd: 556,           // 18.90s
  bufferStart: 562,            // 19.10s "Buffer"
  bufferClimb12: 636,          // 21.57s "climbs to 12+"
  byTurn30: 687,               // 23.26s "by turn 30"
  bufferEnd: 847,              // 28.60s
  summaryStart: 853,           // 28.81s "Let's look at summary"
  summaryRockets: 945,         // 31.85s "rockets to 50"
  byTurn20: 1011,              // 34.06s
  summaryEnd: 1046,            // 35.23s
  whyWord: 1056,               // 35.58s "Why?"
  twoLLMCalls: 1152,           // 38.77s "two LLM calls"
  oneToRespond: 1172,          // 39.42s
  oneToUpdate: 1211,           // 40.75s "update the running summary"
  doublesLatency: 1291,        // 43.40s
  whyEnd: 1388,                // 46.63s
  onAverage: 1396,             // 46.90s "On average"
  vector7: 1420,               // 47.69s
  buffer10: 1481,              // 49.72s
  summaryWhopping: 1552,       // 52.11s
  thirtySixSec: 1572,          // 52.78s
  fiveTimesSlower: 1638,       // 54.98s
  totalWallclock: 1697,        // 56.95s
  qdrantPgv32min: 1830,        // 61.38s
  buffer45min: 1893,           // 63.48s
  summary3hrs: 1935,           // 64.86s
  end: 1981,                   // 66.83s
};

export const Scene5_Latency: React.FC = () => {
  const frame = useCurrentFrame();

  const latencySeconds = Object.fromEntries(
    BACKENDS.map((b) => [b, LATENCY_PER_TURN[b].map((ms) => ms / 1000)])
  ) as Record<string, number[]>;

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene05.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 40% 40%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: Latency line chart (0 → 1441f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [0, 12, CUE.onAverage - 25, CUE.onAverage + 5],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: "50px 60px",
          }}
        >
          <AnimatedText
            text="Latency Per Turn"
            startFrame={CUE.chartTitle}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
          />
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 30,
              fontWeight: 500,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 10,
              opacity: interpolate(
                frame,
                [CUE.chartTitle + 30, CUE.chartTitle + 60],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            How response time changes across 50 conversation turns
          </div>

          <div style={{ display: "flex", justifyContent: "center", marginTop: 40 }}>
            <AnimatedLineChart
              series={BACKENDS.map((b) => ({
                label: b,
                data: latencySeconds[b],
                color: BACKEND_COLORS[b],
              }))}
              startFrame={CUE.chartDrawStart}
              drawDuration={200}
              chartWidth={1700}
              chartHeight={620}
              xLabels={["1", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50"]}
              yMax={55}
              yLabel="Latency (seconds)"
              xLabel="Conversation Turn"
            />
          </div>

          {/* Annotation: Qdrant + pgvector stay flat */}
          <div
            style={{
              position: "absolute",
              top: 660,
              right: 520,
              fontFamily: FONTS.mono,
              fontSize: 24,
              fontWeight: 700,
              color: COLORS.qdrant,
              background: `${COLORS.qdrant}15`,
              border: `1px solid ${COLORS.qdrant}55`,
              borderRadius: 10,
              padding: "10px 18px",
              opacity: interpolate(
                frame,
                [CUE.qdrantPgvFlat, CUE.qdrantPgvFlat + 20, CUE.bufferStart, CUE.bufferStart + 20],
                [0, 1, 1, 0.2],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              textShadow: `0 0 12px ${COLORS.qdrantGlow}`,
            }}
          >
            ↘ qdrant & pgvector: flat ~7s
          </div>

          {/* Annotation: Buffer climbs */}
          <div
            style={{
              position: "absolute",
              top: 540,
              right: 200,
              fontFamily: FONTS.mono,
              fontSize: 24,
              fontWeight: 700,
              color: COLORS.buffer,
              background: `${COLORS.buffer}20`,
              border: `1px solid ${COLORS.buffer}66`,
              borderRadius: 10,
              padding: "10px 18px",
              opacity: interpolate(
                frame,
                [CUE.bufferClimb12, CUE.bufferClimb12 + 20, CUE.summaryStart, CUE.summaryStart + 20],
                [0, 1, 1, 0.2],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              textShadow: `0 0 12px ${COLORS.bufferGlow}`,
            }}
          >
            ↗ buffer: 3s → 12+s by turn 30
          </div>

          {/* Annotation: Summary rockets */}
          <div
            style={{
              position: "absolute",
              top: 220,
              left: 850,
              fontFamily: FONTS.mono,
              fontSize: 28,
              fontWeight: 800,
              color: COLORS.summary,
              background: `${COLORS.summary}20`,
              border: `2px solid ${COLORS.summary}88`,
              borderRadius: 10,
              padding: "10px 18px",
              opacity: interpolate(
                frame,
                [CUE.summaryRockets, CUE.summaryRockets + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              textShadow: `0 0 12px ${COLORS.summaryGlow}`,
              boxShadow: `0 0 24px ${COLORS.summaryGlow}`,
            }}
          >
            🚀 summary: 9s → 50s
          </div>

          {/* "Why?" overlay during 2-LLM-call explanation */}
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 20,
              display: "flex",
              justifyContent: "center",
              opacity: interpolate(
                frame,
                [CUE.whyWord, CUE.whyWord + 20, CUE.whyEnd - 10, CUE.whyEnd + 5],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <div
              style={{
                background: COLORS.bgCard,
                border: `1px solid ${COLORS.summary}66`,
                borderRadius: 14,
                padding: "24px 36px",
                fontFamily: FONTS.body,
                fontSize: 30,
                fontWeight: 500,
                color: COLORS.text,
                backdropFilter: "blur(20px)",
                maxWidth: 1400,
                textAlign: "center",
                boxShadow: `0 0 30px ${COLORS.summaryGlow}`,
              }}
            >
              Summary needs <span style={{ color: COLORS.summary, fontWeight: 700 }}>2 LLM calls per turn</span>: one to respond, one to update the summary. Latency doubles, and the summary keeps growing.
            </div>
          </div>
        </div>

        {/* Phase 2: Average bar chart + wall clock (1441 → 2112f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.onAverage, CUE.onAverage + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: "50px 60px",
          }}
        >
          <AnimatedText
            text="Average Latency Per Turn"
            startFrame={CUE.onAverage + 5}
            fontSize={44}
            fontWeight={700}
            textAlign="center"
          />

          <div style={{ display: "flex", justifyContent: "center", marginTop: 100 }}>
            <AnimatedBarChart
              data={BACKENDS.map((b) => ({
                label: b,
                value: AVG_LATENCY_MS[b] / 1000,
                displayValue: `${(AVG_LATENCY_MS[b] / 1000).toFixed(1)}s`,
                color: BACKEND_COLORS[b],
              }))}
              startFrame={CUE.onAverage + 30}
              barWidth={160}
              chartHeight={400}
              chartWidth={1000}
              errorBars={BACKENDS.map((b) => STD_LATENCY_MS[b] / 1000)}
            />
          </div>

          {/* 5x slower badge */}
          <div
            style={{
              position: "absolute",
              top: 420,
              right: 360,
              fontFamily: FONTS.mono,
              fontSize: 24,
              fontWeight: 700,
              color: COLORS.danger,
              background: `${COLORS.danger}15`,
              border: `1px solid ${COLORS.danger}66`,
              borderRadius: 10,
              padding: "10px 18px",
              opacity: interpolate(
                frame,
                [CUE.fiveTimesSlower, CUE.fiveTimesSlower + 15],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              textShadow: `0 0 12px ${COLORS.dangerGlow}`,
              boxShadow: `0 0 24px ${COLORS.dangerGlow}`,
            }}
          >
            5× slower
          </div>

          {/* Wall clock totals */}
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 180,
              opacity: interpolate(
                frame,
                [CUE.totalWallclock, CUE.totalWallclock + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 28,
                fontWeight: 700,
                color: COLORS.textMuted,
                textAlign: "center",
                letterSpacing: 5,
                textTransform: "uppercase",
                marginBottom: 24,
              }}
            >
              Total wall-clock (5 runs)
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                gap: 80,
              }}
            >
              {BACKENDS.map((b) => {
                const revealFrame =
                  b === "buffer"
                    ? CUE.buffer45min
                    : b === "summary"
                    ? CUE.summary3hrs
                    : CUE.qdrantPgv32min;
                return (
                  <div
                    key={b}
                    style={{
                      textAlign: "center",
                      opacity: interpolate(
                        frame,
                        [revealFrame, revealFrame + 15],
                        [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      ),
                      transform: `scale(${interpolate(
                        frame,
                        [revealFrame, revealFrame + 15],
                        [0.9, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      )})`,
                    }}
                  >
                    <div
                      style={{
                        fontFamily: FONTS.mono,
                        fontSize: 20,
                        fontWeight: 600,
                        color: COLORS.textMuted,
                        marginBottom: 8,
                      }}
                    >
                      {b}
                    </div>
                    <div
                      style={{
                        fontFamily: FONTS.mono,
                        fontSize: 40,
                        fontWeight: 800,
                        color: BACKEND_COLORS[b],
                        textShadow: b === "summary" ? `0 0 16px ${COLORS.summaryGlow}` : undefined,
                      }}
                    >
                      {WALL_CLOCK[b]}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
