import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { FadeTransition } from "../components/FadeTransition";
import { BACKENDS, COST_PER_1K, AVG_TOKENS } from "../data/benchmarkData";

// Cue points synced to public/audio/scene06.wav (whisper word-level, 30fps).
const CUE = {
  intro: 0,                  // 0.00s "Here"
  reallyInteresting: 31,     // 1.03s
  extrapolate: 96,           // 3.21s
  thousandConv: 124,         // 4.14s
  introEnd: 190,             // 6.32s
  bufferReveal: 202,         // 6.72s "Buffer"
  bufferAmount: 249,         // 8.29s "$4,303"
  bufferReason: 303,         // 10.11s "it sends the entire"
  byTurn50: 423,             // 14.12s
  bufferEnd: 604,            // 20.12s
  summaryReveal: 604,        // 20.12s "Summary"
  summaryAmount: 625,        // 20.83s "$2,256"
  summaryReason: 666,        // 22.22s
  payingTwice: 843,          // 28.11s
  summaryEnd: 910,           // 30.34s
  qdrantReveal: 912,         // 30.41s
  qdrantAmount: 947,         // 31.56s "$418"
  pgvectorAmount: 1025,      // 34.18s "$416"
  ninetyPctReduction: 1083,  // 36.10s
  vectorExplain: 1175,       // 39.07s
  flatTokens: 1330,          // 44.42s
  vectorEnd: 1428,           // 47.61s
  putAnotherWay: 1436,       // 47.88s
  forEveryDollar: 1475,      // 49.46s
  vectorMemoryWord: 1530,    // 51.01s
  tenDollars: 1571,          // 52.39s
  bufferMemWord: 1605,       // 53.51s
  end: 1686,                 // 56.19s
};

export const Scene6_Cost: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Bar chart geometry
  const chartHeight = 420;
  const maxCost = Math.max(...BACKENDS.map((b) => COST_PER_1K[b]));

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene06.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 60% 50%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: Intro headline (0 → 190f) */}
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
              [0, 10, CUE.introEnd - 10, CUE.introEnd + 5],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <AnimatedText
            text="Let's extrapolate to"
            startFrame={CUE.intro + 5}
            fontSize={42}
            color={COLORS.textMuted}
            textAlign="center"
            mode="wordByWord"
            durationFrames={70}
          />
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 120,
              fontWeight: 800,
              color: COLORS.accent,
              marginTop: 20,
              textShadow: `0 0 60px ${COLORS.accentGlow}`,
              opacity: interpolate(
                frame,
                [CUE.thousandConv, CUE.thousandConv + 15],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              transform: `scale(${interpolate(
                frame,
                [CUE.thousandConv, CUE.thousandConv + 18],
                [0.85, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              )})`,
            }}
          >
            1,000
          </div>
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 32,
              color: COLORS.text,
              marginTop: 10,
              opacity: interpolate(
                frame,
                [CUE.thousandConv + 20, CUE.thousandConv + 40],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            conversations
          </div>
        </div>

        {/* Phase 2: Cost bar chart (190 → 1436f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.introEnd, CUE.introEnd + 15, CUE.putAnotherWay - 15, CUE.putAnotherWay + 5],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: "50px 60px",
          }}
        >
          <AnimatedText
            text="Cost per 1,000 Conversations"
            startFrame={CUE.introEnd + 5}
            fontSize={44}
            fontWeight={700}
            textAlign="center"
          />

          {/* Custom bar chart with progressive reveal */}
          <div
            style={{
              position: "relative",
              width: 1100,
              height: chartHeight + 160,
              margin: "120px auto 0",
            }}
          >
            {/* Y-axis baseline */}
            <div
              style={{
                position: "absolute",
                bottom: 120,
                left: 0,
                right: 0,
                height: 1,
                background: COLORS.border,
              }}
            />

            {BACKENDS.map((b, i) => {
              const cost = COST_PER_1K[b];
              const color = BACKEND_COLORS[b];
              const revealFrame =
                b === "buffer"
                  ? CUE.bufferReveal
                  : b === "summary"
                  ? CUE.summaryReveal
                  : b === "qdrant"
                  ? CUE.qdrantReveal
                  : CUE.qdrantReveal + 80; // pgvector reveals after qdrant
              const amountFrame =
                b === "buffer"
                  ? CUE.bufferAmount
                  : b === "summary"
                  ? CUE.summaryAmount
                  : b === "qdrant"
                  ? CUE.qdrantAmount
                  : CUE.pgvectorAmount;

              const fillProgress = spring({
                frame: Math.max(0, frame - amountFrame),
                fps,
                config: { damping: 18, stiffness: 60 },
              });
              const barHeight = (cost / maxCost) * chartHeight * fillProgress;

              const barW = 180;
              const gap = 60;
              const totalW = BACKENDS.length * barW + (BACKENDS.length - 1) * gap;
              const startX = (1100 - totalW) / 2;
              const x = startX + i * (barW + gap);

              const isVector = b === "qdrant" || b === "pgvector";

              return (
                <div key={b}>
                  {/* Bar */}
                  <div
                    style={{
                      position: "absolute",
                      left: x,
                      bottom: 120,
                      width: barW,
                      height: barHeight,
                      background: `linear-gradient(180deg, ${color}, ${color}99)`,
                      borderRadius: "8px 8px 0 0",
                      boxShadow: isVector
                        ? `0 0 24px rgba(0,255,136,0.3)`
                        : `0 0 20px ${color}33`,
                      opacity: interpolate(
                        frame,
                        [revealFrame, revealFrame + 15],
                        [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      ),
                    }}
                  />
                  {/* Cost amount above bar */}
                  <div
                    style={{
                      position: "absolute",
                      left: x,
                      bottom: 120 + barHeight + 12,
                      width: barW,
                      textAlign: "center",
                      fontFamily: FONTS.mono,
                      fontSize: 32,
                      fontWeight: 700,
                      color: isVector ? COLORS.neonGreen : color,
                      opacity: interpolate(
                        frame,
                        [amountFrame, amountFrame + 15],
                        [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      ),
                      textShadow: isVector
                        ? `0 0 18px rgba(0,255,136,0.4)`
                        : undefined,
                    }}
                  >
                    ${cost.toLocaleString()}
                  </div>
                  {/* Backend label below bar */}
                  <div
                    style={{
                      position: "absolute",
                      left: x,
                      bottom: 60,
                      width: barW,
                      textAlign: "center",
                      fontFamily: FONTS.mono,
                      fontSize: 24,
                      fontWeight: 600,
                      color: COLORS.text,
                      opacity: interpolate(
                        frame,
                        [revealFrame, revealFrame + 15],
                        [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      ),
                    }}
                  >
                    {b}
                  </div>
                  {/* Token count below label */}
                  <div
                    style={{
                      position: "absolute",
                      left: x,
                      bottom: 16,
                      width: barW,
                      textAlign: "center",
                      fontFamily: FONTS.mono,
                      fontSize: 18,
                      color: COLORS.textMuted,
                      opacity: interpolate(
                        frame,
                        [revealFrame + 20, revealFrame + 40],
                        [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      ),
                    }}
                  >
                    {(AVG_TOKENS[b] / 1000).toFixed(0)}K tokens/run
                  </div>
                </div>
              );
            })}

            {/* 90% reduction badge */}
            <div
              style={{
                position: "absolute",
                top: 50,
                right: 30,
                fontFamily: FONTS.mono,
                fontSize: 26,
                fontWeight: 700,
                color: COLORS.neonGreen,
                background: "rgba(0,255,136,0.08)",
                border: `2px solid rgba(0,255,136,0.3)`,
                borderRadius: 12,
                padding: "12px 24px",
                textShadow: `0 0 20px rgba(0,255,136,0.4)`,
                boxShadow: `0 0 30px rgba(0,255,136,0.15)`,
                opacity: interpolate(
                  frame,
                  [CUE.ninetyPctReduction, CUE.ninetyPctReduction + 20],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
              }}
            >
              90% cost reduction
            </div>
          </div>

          {/* Buffer reasoning callout */}
          <div
            style={{
              position: "absolute",
              left: 60,
              right: 60,
              bottom: 60,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.bufferReason, CUE.bufferReason + 15, CUE.summaryReveal - 5, CUE.summaryReveal + 10],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              fontFamily: FONTS.body,
              fontSize: 28,
              fontWeight: 500,
              color: COLORS.textMuted,
            }}
          >
            Buffer sends the <span style={{ color: COLORS.buffer, fontWeight: 700 }}>entire conversation history</span> every turn. By turn 50, every message carries 50 turns of context.
          </div>

          {/* Summary reasoning callout */}
          <div
            style={{
              position: "absolute",
              left: 60,
              right: 60,
              bottom: 60,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.summaryReason, CUE.summaryReason + 15, CUE.qdrantReveal - 5, CUE.qdrantReveal + 10],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              fontFamily: FONTS.body,
              fontSize: 28,
              fontWeight: 500,
              color: COLORS.textMuted,
            }}
          >
            Summary pays <span style={{ color: COLORS.summary, fontWeight: 700 }}>twice per turn</span>: one call to respond, one to update the running summary.
          </div>

          {/* Vector reasoning callout */}
          <div
            style={{
              position: "absolute",
              left: 60,
              right: 60,
              bottom: 60,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.vectorExplain, CUE.vectorExplain + 15, CUE.vectorEnd - 10, CUE.vectorEnd + 5],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              fontFamily: FONTS.body,
              fontSize: 28,
              fontWeight: 500,
              color: COLORS.textMuted,
            }}
          >
            Vector backends send only <span style={{ color: COLORS.neonGreen, fontWeight: 700 }}>4 relevant snippets</span> per turn. Token usage stays flat regardless of conversation length.
          </div>
        </div>

        {/* Phase 3: $1 vs $10 metaphor (1436 → 1686f) */}
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
              [CUE.putAnotherWay, CUE.putAnotherWay + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <AnimatedText
            text="For every $1 on vector memory..."
            startFrame={CUE.forEveryDollar}
            fontSize={42}
            fontWeight={600}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={90}
          />

          <div style={{ display: "flex", alignItems: "flex-end", gap: 80, marginTop: 60 }}>
            {/* Vector side: 1 coin */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div
                style={{
                  width: 100,
                  height: 100,
                  borderRadius: "50%",
                  background: `linear-gradient(135deg, ${COLORS.qdrant}, ${COLORS.neonGreen})`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: FONTS.mono,
                  fontSize: 36,
                  fontWeight: 700,
                  color: "#fff",
                  boxShadow: `0 0 40px ${COLORS.qdrantGlow}`,
                  opacity: interpolate(
                    frame,
                    [CUE.vectorMemoryWord, CUE.vectorMemoryWord + 15],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  ),
                  transform: `scale(${spring({
                    frame: Math.max(0, frame - CUE.vectorMemoryWord),
                    fps,
                    config: { damping: 12, stiffness: 100 },
                  })})`,
                }}
              >
                $1
              </div>
              <div
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 26,
                  fontWeight: 600,
                  color: COLORS.qdrant,
                  marginTop: 16,
                }}
              >
                vector memory
              </div>
            </div>

            <div
              style={{
                alignSelf: "center",
                fontFamily: FONTS.body,
                fontSize: 32,
                color: COLORS.textMuted,
                marginBottom: 30,
                opacity: interpolate(
                  frame,
                  [CUE.tenDollars - 30, CUE.tenDollars],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
              }}
            >
              vs
            </div>

            {/* Buffer side: 10 coins in a 5×2 grid */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(5, 64px)",
                  gridTemplateRows: "repeat(2, 64px)",
                  gap: 10,
                  justifyContent: "center",
                }}
              >
                {Array.from({ length: 10 }).map((_, i) => {
                  const coinDelay = CUE.tenDollars + i * 6;
                  return (
                    <div
                      key={i}
                      style={{
                        width: 64,
                        height: 64,
                        borderRadius: "50%",
                        background: `linear-gradient(135deg, ${COLORS.buffer}, ${COLORS.buffer}88)`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: FONTS.mono,
                        fontSize: 18,
                        fontWeight: 700,
                        color: "#fff",
                        boxShadow: `0 0 15px ${COLORS.bufferGlow}`,
                        opacity: interpolate(
                          frame,
                          [coinDelay, coinDelay + 10],
                          [0, 1],
                          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                        ),
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
                  fontSize: 26,
                  fontWeight: 600,
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
            startFrame={CUE.bufferMemWord}
            fontSize={36}
            fontWeight={700}
            color={COLORS.accent}
            glow
            textAlign="center"
            mode="wordByWord"
            durationFrames={50}
            style={{ marginTop: 50 }}
          />
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
