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
import { AnimatedCounter } from "../components/AnimatedCounter";
import { AnimatedLineChart } from "../components/AnimatedLineChart";
import { BackendBadge } from "../components/BackendBadge";
import { FadeTransition } from "../components/FadeTransition";
import {
  BACKENDS,
  RECALL_AT_TURN_15,
  RECALL_AT_TURN_50,
  RECALL_BY_SEED_TURN_AT_50,
  SEED_TURNS,
  SEEDED_FACTS,
} from "../data/benchmarkData";

// Cue points synced to public/audio/scene04.wav (whisper word-level, 30fps).
const CUE = {
  intro: 0,                      // 0.00 "Let's start"
  canItRemember: 87,             // 2.79s
  introEnd: 128,                 // 4.25s
  atTurn15: 131,                 // 4.36s
  fourBackends: 182,             // 6.14s
  hundredPctRecall: 222,         // 7.42s "100%"
  recallWord: 258,               // 8.62s
  onlyFourFacts: 270,            // 9.00s
  noChallenge: 429,              // 14.31s
  turn15End: 464,                // 15.48s
  butAtTurn50: 464,              // 15.48s "But at turn 50"
  storyChanges: 626,             // 20.79s
  dramatically: 653,             // 21.78s
  turn50SetupEnd: 684,           // 22.80s
  bufferReveal: 703,             // 23.44s "Buffer"
  buffer90: 727,                 // 24.24s "90%"
  bufferReason: 787,             // 26.23s "it has"
  ofCourseRemembers: 901,        // 30.03s
  onlyFailures: 940,             // 31.32s
  wifiPasswordBankPIN: 982,      // 32.71s
  claudeSafety: 1051,            // 35.04s
  notMemoryFailure: 1186,        // 39.56s
  qdrantPgvectorReveal: 1244,    // 41.48s
  qdrantPgvector82: 1299,        // 43.33s
  solidPerformance: 1328,        // 44.27s
  sameSafetyDrops: 1496,         // 49.87s
  summaryReveal: 1602,           // 53.40s "And then"
  summary42: 1663,               // 55.43s "42%"
  lessThanHalf: 1683,            // 56.19s
  scoreboardEnd: 1735,           // 57.84s
  letsLookAt: 1735,              // 57.84s
  summaryRemembersT1to12: 1791,  // 59.73s
  perfectly: 1894,               // 63.13s
  everythingAfter18: 1922,       // 64.08s
  turn18Zero: 1982,              // 66.06s
  summarizerCompressed: 2024,    // 67.48s
  sistersWedding: 2078,          // 69.22s
  bookReading: 2142,             // 71.41s
  supplementDosage: 2190,        // 73.02s
  allGone: 2230,                 // 74.34s
  notJustForget: 2294,           // 76.40s
  activelyDestroys: 2356,        // 78.55s
  end: 2469,                     // 82.27s
};

export const Scene4_Recall: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene04.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, #0d1525 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: "Can it remember?" + Turn 15 line chart (0 → 684f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [0, 12, CUE.turn50SetupEnd - 25, CUE.turn50SetupEnd + 10],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: 60,
          }}
        >
          <AnimatedText
            text="Can it remember?"
            startFrame={CUE.canItRemember}
            fontSize={56}
            fontWeight={700}
            textAlign="center"
          />
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 36,
              fontWeight: 600,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 28,
              opacity: interpolate(
                frame,
                [CUE.atTurn15, CUE.atTurn15 + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            Recall accuracy: turn 15 vs turn 50
          </div>

          {/* Annotation: 100% recall at turn 15 — sits above the chart */}
          <div
            style={{
              position: "absolute",
              top: 250,
              left: "50%",
              transform: "translateX(-50%)",
              opacity: interpolate(
                frame,
                [CUE.hundredPctRecall, CUE.hundredPctRecall + 15, CUE.butAtTurn50, CUE.butAtTurn50 + 30],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              fontFamily: FONTS.mono,
              fontSize: 22,
              fontWeight: 700,
              color: COLORS.neonGreen,
              textShadow: `0 0 16px rgba(0,255,136,0.4)`,
              background: "rgba(0,255,136,0.07)",
              border: `1px solid rgba(0,255,136,0.35)`,
              borderRadius: 10,
              padding: "8px 18px",
              letterSpacing: 1,
              boxShadow: `0 0 18px rgba(0,255,136,0.12)`,
              whiteSpace: "nowrap",
            }}
          >
            ✓ 100% at Turn 15 · no challenge
          </div>

          <div style={{ display: "flex", justifyContent: "center", marginTop: 90 }}>
            <AnimatedLineChart
              series={BACKENDS.map((b) => ({
                label: b,
                data: [RECALL_AT_TURN_15[b], RECALL_AT_TURN_50[b]],
                color: BACKEND_COLORS[b],
              }))}
              startFrame={CUE.atTurn15 + 20}
              drawDuration={120}
              chartWidth={1300}
              chartHeight={620}
              xLabels={["Turn 15", "Turn 50"]}
              yMax={105}
              yLabel="Recall %"
            />
          </div>

          {/* "But at turn 50..." subtitle */}
          <div
            style={{
              position: "absolute",
              bottom: 100,
              left: 0,
              right: 0,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.butAtTurn50, CUE.butAtTurn50 + 15],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <AnimatedText
              text="But at turn 50, the story changes dramatically."
              startFrame={CUE.butAtTurn50 + 5}
              fontSize={32}
              fontWeight={600}
              color={COLORS.danger}
              glow
              glowColor={COLORS.dangerGlow}
              textAlign="center"
              mode="wordByWord"
              durationFrames={140}
            />
          </div>
        </div>

        {/* Phase 2: Scoreboard at Turn 50 (684 → 1735f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.turn50SetupEnd, CUE.turn50SetupEnd + 15, CUE.scoreboardEnd - 15, CUE.scoreboardEnd + 5],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: "50px 120px",
          }}
        >
          <AnimatedText
            text="Recall at Turn 50"
            startFrame={CUE.turn50SetupEnd + 5}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
          />

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 44,
              maxWidth: 1500,
              margin: "60px auto 0",
            }}
          >
            {BACKENDS.map((b) => {
              const pct = RECALL_AT_TURN_50[b];
              const color = BACKEND_COLORS[b];
              const isSummary = b === "summary";
              const isBuffer = b === "buffer";
              const isVector = b === "qdrant" || b === "pgvector";

              const rowStart = isBuffer
                ? CUE.bufferReveal
                : isVector
                ? CUE.qdrantPgvectorReveal
                : CUE.summaryReveal;
              const counterStart = isBuffer
                ? CUE.buffer90
                : isVector
                ? CUE.qdrantPgvector82
                : CUE.summary42;

              const barWidth = spring({
                frame: Math.max(0, frame - counterStart),
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
                    gap: 32,
                  }}
                >
                  <div style={{ width: 240, flexShrink: 0 }}>
                    <BackendBadge name={b} fontSize={32} />
                  </div>

                  <div
                    style={{
                      flex: 1,
                      height: 90,
                      background: COLORS.bgCard,
                      borderRadius: 12,
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
                        borderRadius: 10,
                        boxShadow: isSummary
                          ? `0 0 30px ${COLORS.dangerGlow}`
                          : `0 0 24px ${color}44`,
                      }}
                    />
                  </div>

                  <div style={{ width: 160, textAlign: "right", flexShrink: 0 }}>
                    <AnimatedCounter
                      value={pct}
                      startFrame={counterStart}
                      durationFrames={40}
                      suffix="%"
                      fontSize={56}
                      color={isSummary ? COLORS.danger : color}
                      fontWeight={800}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary shock callout */}
          <div
            style={{
              position: "absolute",
              left: 120,
              right: 120,
              bottom: 100,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.summary42, CUE.summary42 + 15, CUE.scoreboardEnd - 10, CUE.scoreboardEnd],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <AnimatedText
              text="Summary: 42%. Less than half."
              startFrame={CUE.summary42 + 5}
              fontSize={56}
              fontWeight={800}
              color={COLORS.danger}
              glow
              glowColor={COLORS.dangerGlow}
              textAlign="center"
              mode="wordByWord"
              durationFrames={60}
            />
          </div>
        </div>

        {/* Phase 3: Summary cliff heatmap + lost facts (1735 → 2469f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.scoreboardEnd, CUE.scoreboardEnd + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: "40px 80px",
          }}
        >
          <AnimatedText
            text="The Summary Cliff"
            startFrame={CUE.letsLookAt + 5}
            fontSize={44}
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
              marginTop: 12,
              opacity: interpolate(
                frame,
                [CUE.letsLookAt + 20, CUE.letsLookAt + 40],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            Each cell = one planted fact. Green kept, red lost.
          </div>

          {(() => {
            const cliffIndex = 4;
            const cellW = 115;
            const cellH = 92;
            const cellGap = 8;
            const cliffGap = 36;
            const rowLabelW = 180;
            const gridTop = 110;

            const getCellLeft = (si: number) =>
              rowLabelW + si * (cellW + cellGap) + (si >= cliffIndex ? cliffGap : 0);

            const gridWidth =
              rowLabelW + SEED_TURNS.length * (cellW + cellGap) + cliffGap;

            return (
              <div
                style={{
                  position: "relative",
                  marginTop: 24,
                  width: gridWidth,
                  marginLeft: "auto",
                  marginRight: "auto",
                }}
              >
                {SEED_TURNS.map((turn, si) => (
                  <div
                    key={turn}
                    style={{
                      position: "absolute",
                      left: getCellLeft(si),
                      top: gridTop - 42,
                      width: cellW,
                      textAlign: "center",
                      fontFamily: FONTS.mono,
                      fontSize: 26,
                      fontWeight: 700,
                      color: COLORS.textMuted,
                      opacity: interpolate(
                        frame,
                        [CUE.letsLookAt + 30, CUE.letsLookAt + 50],
                        [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      ),
                    }}
                  >
                    T{turn}
                  </div>
                ))}

                {/* Cliff line */}
                <div
                  style={{
                    position: "absolute",
                    left:
                      rowLabelW +
                      cliffIndex * (cellW + cellGap) -
                      cellGap / 2 +
                      cliffGap / 2 -
                      1,
                    top: gridTop - 44,
                    width: 2,
                    height: BACKENDS.length * (cellH + cellGap) + 56,
                    background: COLORS.danger,
                    boxShadow: `0 0 12px ${COLORS.dangerGlow}`,
                    opacity: interpolate(
                      frame,
                      [CUE.everythingAfter18, CUE.everythingAfter18 + 40],
                      [0, 0.85],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left:
                      rowLabelW +
                      cliffIndex * (cellW + cellGap) -
                      cellGap / 2 +
                      cliffGap / 2 -
                      130,
                    top: gridTop - 84,
                    width: 260,
                    textAlign: "center",
                    fontFamily: FONTS.mono,
                    fontSize: 26,
                    color: COLORS.danger,
                    fontWeight: 800,
                    letterSpacing: 3,
                    textShadow: `0 0 16px ${COLORS.dangerGlow}`,
                    opacity: interpolate(
                      frame,
                      [CUE.everythingAfter18 + 30, CUE.everythingAfter18 + 60],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                >
                  ↓ THE CLIFF
                </div>

                {BACKENDS.map((b, bi) => {
                  const rowDelay = CUE.letsLookAt + 60 + bi * 35;
                  const rowOpacity = interpolate(
                    frame,
                    [rowDelay, rowDelay + 20],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  );
                  const isSummary = b === "summary";
                  return (
                    <div key={b} style={{ opacity: rowOpacity }}>
                      <div
                        style={{
                          position: "absolute",
                          left: 0,
                          top: gridTop + bi * (cellH + cellGap),
                          width: rowLabelW - 12,
                          height: cellH,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "flex-end",
                          paddingRight: 20,
                          fontFamily: FONTS.mono,
                          fontSize: 30,
                          fontWeight: 800,
                          color: BACKEND_COLORS[b],
                          textShadow: isSummary
                            ? `0 0 14px ${COLORS.dangerGlow}`
                            : undefined,
                        }}
                      >
                        {b}
                      </div>

                      {SEED_TURNS.map((turn, si) => {
                        const val = RECALL_BY_SEED_TURN_AT_50[b][si];
                        const kept = val >= 50;
                        const partial = val > 0 && val < 50;
                        const cellDelay = rowDelay + si * 10;
                        const cellFill = spring({
                          frame: Math.max(0, frame - cellDelay),
                          fps,
                          config: { damping: 18, stiffness: 90 },
                        });
                        const scale = 0.7 + 0.3 * cellFill;

                        const bg = kept
                          ? `linear-gradient(135deg, ${COLORS.neonGreen}cc, ${COLORS.neonGreen}66)`
                          : partial
                          ? `linear-gradient(135deg, #ffaa44cc, #ffaa4466)`
                          : `linear-gradient(135deg, ${COLORS.danger}cc, ${COLORS.danger}66)`;

                        const glow = kept
                          ? `0 0 14px rgba(0,255,136,0.25)`
                          : partial
                          ? `0 0 14px rgba(255,170,68,0.3)`
                          : `0 0 18px ${COLORS.dangerGlow}`;

                        return (
                          <div
                            key={turn}
                            style={{
                              position: "absolute",
                              left: getCellLeft(si),
                              top: gridTop + bi * (cellH + cellGap),
                              width: cellW,
                              height: cellH,
                              borderRadius: 8,
                              background: bg,
                              border: `1px solid ${
                                kept
                                  ? "rgba(0,255,136,0.4)"
                                  : partial
                                  ? "rgba(255,170,68,0.4)"
                                  : "rgba(255,68,68,0.5)"
                              }`,
                              boxShadow: glow,
                              display: "flex",
                              flexDirection: "column",
                              alignItems: "center",
                              justifyContent: "center",
                              opacity: cellFill,
                              transform: `scale(${scale})`,
                            }}
                          >
                            <div
                              style={{
                                fontFamily: FONTS.mono,
                                fontSize: 32,
                                fontWeight: 800,
                                color: "#fff",
                                lineHeight: 1,
                              }}
                            >
                              {val}%
                            </div>
                            <div
                              style={{
                                fontFamily: FONTS.mono,
                                fontSize: 28,
                                color: "rgba(255,255,255,0.95)",
                                marginTop: 4,
                              }}
                            >
                              {kept ? "✓" : "✗"}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            );
          })()}

          {/* Lost facts strip during "compressed away" narration */}
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 820,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.summarizerCompressed, CUE.summarizerCompressed + 15, CUE.allGone + 20, CUE.allGone + 40],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 32,
                fontWeight: 700,
                color: COLORS.textMuted,
                letterSpacing: 5,
                textTransform: "uppercase",
                marginBottom: 24,
              }}
            >
              Compressed away by summary
            </div>
            <div style={{ display: "flex", gap: 20, justifyContent: "center", flexWrap: "wrap" }}>
              {[
                { label: "💒 Sister's wedding", reveal: CUE.sistersWedding },
                { label: "📖 Book reading", reveal: CUE.bookReading },
                { label: "💊 Supplement dosage", reveal: CUE.supplementDosage },
              ].map((f) => (
                <div
                  key={f.label}
                  style={{
                    fontFamily: FONTS.body,
                    fontSize: 26,
                    fontWeight: 600,
                    color: COLORS.text,
                    background: "rgba(255,68,68,0.10)",
                    border: `1px solid ${COLORS.danger}66`,
                    borderRadius: 12,
                    padding: "12px 22px",
                    textDecoration: frame >= f.reveal + 20 ? "line-through" : "none",
                    opacity: interpolate(
                      frame,
                      [f.reveal, f.reveal + 15],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                >
                  {f.label}
                </div>
              ))}
            </div>
          </div>

          {/* Closing tagline */}
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 740,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.activelyDestroys, CUE.activelyDestroys + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <AnimatedText
              text="Summary actively destroys new information as it compresses."
              startFrame={CUE.activelyDestroys + 5}
              fontSize={40}
              fontWeight={800}
              color={COLORS.summary}
              glow
              glowColor={COLORS.summaryGlow}
              textAlign="center"
              mode="wordByWord"
              durationFrames={100}
            />
          </div>
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
