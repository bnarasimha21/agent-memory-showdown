import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS, FONTS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { GlassCard } from "../components/GlassCard";
import { FadeTransition } from "../components/FadeTransition";

// Cue points synced to public/audio/scene10.wav (whisper word-level, 30fps).
const CUE = {
  thats: 10,                // 0.34s "That's"
  agentMemory: 25,          // 0.85s
  showdown: 56,             // 1.89s
  introEnd: 76,             // 2.53s
  fourBackends: 89,         // 2.96s
  thousandCalls: 137,       // 4.56s
  fiveHours: 187,           // 6.22s
  digitalOceanDroplet: 241, // 8.06s
  statsEnd: 303,            // 10.11s
  ifBuilding: 314,          // 10.48s
  haventBenchmarked: 379,   // 12.56s
  youreGuessing: 452,       // 15.08s
  guessingEnd: 473,         // 15.76s
  theDifference: 480,       // 16.00s
  tenTimesCost: 579,        // 19.34s
  fiveTimesLatency: 631,    // 21.04s
  twoTimesRecall: 678,      // 22.61s
  recallEnd: 738,           // 24.60s
  soDoNot: 738,             // 24.60s "So do not"
  guess: 760,               // 25.31s
  measure: 780,             // 26.02s
  end: 822,                 // 27.38s
};

const HEADLINE_STATS = [
  { value: "4", label: "memory backends", reveal: CUE.fourBackends, color: COLORS.accent },
  { value: "1,000+", label: "LLM calls", reveal: CUE.thousandCalls, color: COLORS.neonGreen },
  { value: "5 hrs", label: "benchmarking", reveal: CUE.fiveHours, color: COLORS.qdrant },
  { value: "$48/mo", label: "DO Droplet", reveal: CUE.digitalOceanDroplet, color: COLORS.pgvector },
];

const DIFF_STATS = [
  { multiplier: "10×", label: "cost", reveal: CUE.tenTimesCost, color: COLORS.danger },
  { multiplier: "5×", label: "latency", reveal: CUE.fiveTimesLatency, color: COLORS.summary },
  { multiplier: "2×", label: "recall accuracy", reveal: CUE.twoTimesRecall, color: COLORS.accent },
];

export const Scene10_Closing: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={CUE.end} fadeOutFrames={0}>
      <Audio src={staticFile("audio/scene10.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, #0d1525 0%, ${COLORS.bg} 70%)`,
          padding: 80,
        }}
      >
        {/* Phase 1: "That's the Agent Memory Showdown" title reveal (10 → 303f) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            opacity: interpolate(
              frame,
              [CUE.thats, CUE.thats + 12, CUE.statsEnd - 25, CUE.statsEnd + 10],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 18,
              color: COLORS.accent,
              letterSpacing: 6,
              textTransform: "uppercase",
              marginBottom: 20,
              opacity: interpolate(frame, [CUE.thats, CUE.thats + 15], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            That's the
          </div>
          <h1
            style={{
              fontFamily: FONTS.body,
              fontSize: 96,
              fontWeight: 800,
              color: COLORS.text,
              margin: 0,
              textAlign: "center",
              letterSpacing: -2,
              textShadow: `0 0 60px ${COLORS.accentGlow}`,
              opacity: interpolate(
                frame,
                [CUE.agentMemory, CUE.agentMemory + 15],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              transform: `scale(${spring({
                frame: Math.max(0, frame - CUE.agentMemory),
                fps,
                config: { damping: 14, stiffness: 90 },
              })})`,
            }}
          >
            Agent Memory<br />Showdown
          </h1>

          {/* Headline stats appear below title */}
          <div
            style={{
              display: "flex",
              gap: 30,
              marginTop: 60,
            }}
          >
            {HEADLINE_STATS.map((s, i) => (
              <div
                key={i}
                style={{
                  textAlign: "center",
                  opacity: interpolate(frame, [s.reveal, s.reveal + 15], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  }),
                  transform: `translateY(${interpolate(
                    frame,
                    [s.reveal, s.reveal + 15],
                    [12, 0],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  )}px)`,
                }}
              >
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 44,
                    fontWeight: 700,
                    color: s.color,
                    textShadow: `0 0 20px ${s.color}55`,
                  }}
                >
                  {s.value}
                </div>
                <div
                  style={{
                    fontFamily: FONTS.body,
                    fontSize: 22,
                    color: COLORS.textMuted,
                    marginTop: 8,
                  }}
                >
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Phase 2: "You're guessing" warning (314 → 473f) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "0 120px",
            opacity: interpolate(
              frame,
              [CUE.ifBuilding, CUE.ifBuilding + 15, CUE.guessingEnd - 8, CUE.theDifference],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <AnimatedText
            text="If you haven't benchmarked your memory backend,"
            startFrame={CUE.ifBuilding + 5}
            fontSize={34}
            color={COLORS.textMuted}
            textAlign="center"
            mode="wordByWord"
            durationFrames={130}
          />
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 96,
              fontWeight: 800,
              color: COLORS.accent,
              marginTop: 30,
              textShadow: `0 0 60px ${COLORS.accentGlow}`,
              opacity: interpolate(
                frame,
                [CUE.youreGuessing, CUE.youreGuessing + 12],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              transform: `scale(${interpolate(
                frame,
                [CUE.youreGuessing, CUE.youreGuessing + 18],
                [0.8, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              )})`,
            }}
          >
            you're guessing.
          </div>
        </div>

        {/* Phase 3: The difference (480 → 738f) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            opacity: interpolate(
              frame,
              [CUE.theDifference, CUE.theDifference + 15, CUE.recallEnd - 8, CUE.recallEnd + 4],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 22,
              color: COLORS.textMuted,
              letterSpacing: 4,
              textTransform: "uppercase",
              marginBottom: 36,
            }}
          >
            Best vs. worst choice
          </div>

          <div style={{ display: "flex", gap: 60 }}>
            {DIFF_STATS.map((s) => (
              <GlassCard
                key={s.label}
                startFrame={s.reveal}
                padding={32}
                glowColor={`${s.color}66`}
              >
                <div style={{ textAlign: "center", minWidth: 220 }}>
                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 88,
                      fontWeight: 800,
                      color: s.color,
                      lineHeight: 1,
                      textShadow: `0 0 30px ${s.color}55`,
                      opacity: interpolate(
                        frame,
                        [s.reveal + 5, s.reveal + 20],
                        [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      ),
                      transform: `scale(${spring({
                        frame: Math.max(0, frame - s.reveal - 5),
                        fps,
                        config: { damping: 12, stiffness: 100 },
                      })})`,
                    }}
                  >
                    {s.multiplier}
                  </div>
                  <div
                    style={{
                      fontFamily: FONTS.body,
                      fontSize: 22,
                      color: COLORS.text,
                      marginTop: 12,
                    }}
                  >
                    {s.label}
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        </div>

        {/* Phase 4: "Don't guess. Measure." + GitHub (738 → 822f) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            opacity: interpolate(
              frame,
              [CUE.soDoNot, CUE.soDoNot + 12],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <h1
            style={{
              fontFamily: FONTS.body,
              fontSize: 110,
              fontWeight: 800,
              color: COLORS.text,
              margin: 0,
              letterSpacing: -2,
              textShadow: `0 0 60px ${COLORS.accentGlow}`,
              textAlign: "center",
            }}
          >
            <span
              style={{
                opacity: interpolate(
                  frame,
                  [CUE.guess, CUE.guess + 10],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
              }}
            >
              Don't guess.{" "}
            </span>
            <span
              style={{
                color: COLORS.accent,
                opacity: interpolate(
                  frame,
                  [CUE.measure, CUE.measure + 10],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
                transform: `scale(${interpolate(
                  frame,
                  [CUE.measure, CUE.measure + 18],
                  [0.85, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )})`,
                display: "inline-block",
              }}
            >
              Measure.
            </span>
          </h1>

        </div>

        {/* Bottom progress bar (full gradient at the very end) */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: 4,
            background: `linear-gradient(90deg, ${COLORS.buffer}, ${COLORS.summary}, ${COLORS.qdrant}, ${COLORS.pgvector})`,
            opacity: interpolate(
              frame,
              [CUE.measure, CUE.measure + 30],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        />
      </AbsoluteFill>
    </FadeTransition>
  );
};
