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
import { GlassCard } from "../components/GlassCard";
import { FadeTransition } from "../components/FadeTransition";
import { BACKENDS } from "../data/benchmarkData";

const SENSITIVE_FACTS = [
  { turn: 30, fact: "Wi-Fi password", index: 6 },
  { turn: 45, fact: "Bank PIN", index: 9 },
];

// Cue points synced to public/audio/scene08.wav (whisper word-level, 30fps).
const CUE = {
  intro: 0,                  // 0.33s "There"
  oneFinding: 6,             // 0.46s
  didntExpect: 39,            // 1.57s
  introEnd: 74,               // 2.73s
  everyBackend: 78,          // 2.88s
  includingBuffer: 101,       // 3.62s
  dataInPrompt: 176,          // 6.15s
  failedToRecall: 200,        // 6.95s
  wifiPassword: 244,          // 8.40s
  bankPIN: 295,               // 10.11s
  atTurn50: 307,              // 10.50s — FLASH HAPPENS HERE
  recallEnd: 342,             // 11.67s
  thisIsntMemory: 351,        // 11.96s
  safetyBehavior: 416,        // 14.12s
  safetyEnd: 449,             // 15.23s
  claudeRecognizes: 453,      // 15.36s
  sensitiveDataWord: 488,     // 16.53s
  declinesRepeat: 567,        // 19.16s
  explicitlyProvided: 643,    // 21.70s
  convHistory: 702,           // 23.67s
  claudeEnd: 728,             // 24.53s
  thisMatters: 735,           // 24.76s
  benchmarkDesign: 765,       // 25.76s
  testFacts: 892,             // 29.99s
  misleadingRecall: 979,     // 32.90s
  matterEnd: 1029,            // 34.58s
  failureNotMemory: 1037,     // 34.84s
  llmSafetyLayer: 1121,       // 37.64s
  end: 1175,                  // 39.73s
};

const FLASH_FRAME = CUE.atTurn50;

export const Scene8_Surprise: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const postFlash = frame >= FLASH_FRAME;

  const flashOverlayOpacity = interpolate(
    frame,
    [FLASH_FRAME - 2, FLASH_FRAME + 4, FLASH_FRAME + 30],
    [0, 0.55, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene08.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, #1a0d0d 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Full-screen red flash overlay */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `radial-gradient(ellipse at 50% 50%, ${COLORS.danger}, transparent 70%)`,
            opacity: flashOverlayOpacity,
            pointerEvents: "none",
            zIndex: 5,
          }}
        />

        {/* Phase 1: Setup + indicator grid + synchronized red flash (0 → 470f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [0, 12, CUE.safetyEnd - 8, CUE.safetyEnd + 8],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: "50px 80px",
          }}
        >
          <AnimatedText
            text="One finding I didn't expect."
            startFrame={CUE.intro}
            fontSize={42}
            color={COLORS.textMuted}
            textAlign="center"
            mode="wordByWord"
            durationFrames={80}
          />

          {/* Setup line */}
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 32,
              fontWeight: 500,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 20,
              opacity: interpolate(
                frame,
                [CUE.includingBuffer, CUE.includingBuffer + 20, FLASH_FRAME - 10, FLASH_FRAME + 10],
                [0, 1, 1, 0.4],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            Buffer has the password right there in its prompt. It should ace this.
          </div>

          {/* 4 backends × 2 facts indicator grid */}
          {(() => {
            const tileW = 220;
            const tileH = 120;
            const gapX = 28;
            const gapY = 18;
            const rowHeaderW = 170;
            // Center based on the VISIBLE tiles (since labels are short text
            // right-aligned, the tile cluster dominates the visual weight).
            const tilesWidth = SENSITIVE_FACTS.length * (tileW + gapX) - gapX;
            const tilesViewportX = (1920 - tilesWidth) / 2;
            // gridLeft (relative to container that starts at viewport padding-left = 80)
            const gridLeft = tilesViewportX - 80 - rowHeaderW;
            const gridTop = 40;

            return (
              <div style={{ position: "relative", marginTop: 20 }}>
                {/* Column headers: sensitive facts */}
                {SENSITIVE_FACTS.map((sf, si) => (
                  <div
                    key={sf.turn}
                    style={{
                      position: "absolute",
                      left: gridLeft + rowHeaderW + si * (tileW + gapX),
                      top: gridTop,
                      width: tileW,
                      textAlign: "center",
                      opacity: interpolate(
                        frame,
                        [CUE.wifiPassword - 30 + si * 30, CUE.wifiPassword + si * 30],
                        [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      ),
                    }}
                  >
                    <div style={{ fontSize: 36, marginBottom: 4 }}>🔒</div>
                    <div
                      style={{
                        fontFamily: FONTS.mono,
                        fontSize: 18,
                        color: COLORS.textMuted,
                      }}
                    >
                      Turn {sf.turn}
                    </div>
                    <div
                      style={{
                        fontFamily: FONTS.body,
                        fontSize: 24,
                        fontWeight: 700,
                        color: COLORS.text,
                        marginTop: 4,
                      }}
                    >
                      {sf.fact}
                    </div>
                  </div>
                ))}

                {/* Row headers + tiles */}
                {BACKENDS.map((b, bi) => {
                  const rowTop = gridTop + 60 + 60 + bi * (tileH + gapY);
                  const rowDelay = CUE.failedToRecall + bi * 8;
                  const rowOpacity = interpolate(
                    frame,
                    [rowDelay, rowDelay + 20],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  );

                  return (
                    <div key={b} style={{ opacity: rowOpacity }}>
                      <div
                        style={{
                          position: "absolute",
                          left: gridLeft,
                          top: rowTop,
                          width: rowHeaderW - 16,
                          height: tileH,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "flex-end",
                          paddingRight: 16,
                          fontFamily: FONTS.mono,
                          fontSize: 22,
                          fontWeight: 700,
                          color: BACKEND_COLORS[b],
                        }}
                      >
                        {b}
                      </div>

                      {SENSITIVE_FACTS.map((sf, si) => {
                        const tileLeft = gridLeft + rowHeaderW + si * (tileW + gapX);

                        const flashProgress = interpolate(
                          frame,
                          [FLASH_FRAME, FLASH_FRAME + 8],
                          [0, 1],
                          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                        );

                        const popScale =
                          frame >= FLASH_FRAME && frame <= FLASH_FRAME + 20
                            ? 1 +
                              0.18 *
                                spring({
                                  frame: Math.max(0, frame - FLASH_FRAME),
                                  fps,
                                  config: { damping: 8, stiffness: 200, mass: 0.6 },
                                }) *
                                interpolate(
                                  frame,
                                  [FLASH_FRAME + 8, FLASH_FRAME + 20],
                                  [1, 0],
                                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                                )
                            : 1;

                        const bgGray = `linear-gradient(135deg, ${COLORS.bgCard}, rgba(255,255,255,0.02))`;
                        const bgRed = `linear-gradient(135deg, ${COLORS.danger}cc, ${COLORS.danger}66)`;
                        const borderNeutral = COLORS.border;
                        const borderRed = "rgba(255,68,68,0.7)";

                        return (
                          <div
                            key={b + sf.turn}
                            style={{
                              position: "absolute",
                              left: tileLeft,
                              top: rowTop,
                              width: tileW,
                              height: tileH,
                              borderRadius: 14,
                              background: flashProgress > 0.5 ? bgRed : bgGray,
                              border: `2px solid ${
                                flashProgress > 0.5 ? borderRed : borderNeutral
                              }`,
                              boxShadow:
                                flashProgress > 0.5
                                  ? `0 0 ${
                                      28 +
                                      40 *
                                        interpolate(
                                          frame,
                                          [FLASH_FRAME, FLASH_FRAME + 6, FLASH_FRAME + 25],
                                          [0, 1, 0.3],
                                          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                                        )
                                    }px ${COLORS.dangerGlow}`
                                  : "none",
                              display: "flex",
                              flexDirection: "column",
                              alignItems: "center",
                              justifyContent: "center",
                              transform: `scale(${popScale})`,
                            }}
                          >
                            {!postFlash ? (
                              <div
                                style={{
                                  fontFamily: FONTS.mono,
                                  fontSize: 56,
                                  fontWeight: 700,
                                  color: COLORS.textMuted,
                                  opacity: 0.6,
                                }}
                              >
                                ?
                              </div>
                            ) : (
                              <div
                                style={{
                                  display: "flex",
                                  flexDirection: "column",
                                  alignItems: "center",
                                }}
                              >
                                <div
                                  style={{
                                    fontFamily: FONTS.mono,
                                    fontSize: 52,
                                    fontWeight: 800,
                                    color: "#fff",
                                    lineHeight: 1,
                                  }}
                                >
                                  ✗
                                </div>
                                <div
                                  style={{
                                    fontFamily: FONTS.mono,
                                    fontSize: 24,
                                    fontWeight: 700,
                                    color: "#fff",
                                    marginTop: 8,
                                    letterSpacing: 2,
                                  }}
                                >
                                  FAILED
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            );
          })()}

        </div>

        {/* Phase 2: Safety explanation (470 → 757f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.claudeRecognizes, CUE.claudeRecognizes + 15, CUE.claudeEnd - 10, CUE.claudeEnd + 8],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
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
            text="Claude refuses to repeat sensitive data."
            startFrame={CUE.claudeRecognizes + 5}
            fontSize={44}
            fontWeight={700}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={90}
          />

          <div
            style={{
              marginTop: 40,
              maxWidth: 900,
              opacity: interpolate(
                frame,
                [CUE.declinesRepeat, CUE.declinesRepeat + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <GlassCard startFrame={CUE.declinesRepeat} padding={36}>
              <div
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 28,
                  fontWeight: 500,
                  color: COLORS.textMuted,
                  lineHeight: 1.55,
                  textAlign: "center",
                }}
              >
                Passwords and PINs trip a safety layer.{" "}
                <span style={{ color: COLORS.text, fontWeight: 700 }}>
                  Claude declines to repeat them
                </span>{" "}
                even when they were explicitly provided in the conversation.
              </div>
            </GlassCard>
          </div>
        </div>

        {/* Phase 3: Benchmark design lesson (764 → 1044f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.thisMatters, CUE.thisMatters + 15, CUE.matterEnd - 8, CUE.matterEnd + 8],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "0 140px",
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 18,
              color: COLORS.accent,
              letterSpacing: 4,
              textTransform: "uppercase",
              marginBottom: 24,
            }}
          >
            Benchmark Design Lesson
          </div>
          <AnimatedText
            text="Don't seed sensitive facts in memory benchmarks."
            startFrame={CUE.benchmarkDesign}
            fontSize={42}
            fontWeight={700}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={120}
          />
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 30,
              fontWeight: 500,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 36,
              maxWidth: 1300,
              opacity: interpolate(
                frame,
                [CUE.testFacts, CUE.testFacts + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            Recall scores get <span style={{ color: COLORS.danger, fontWeight: 700 }}>misleading</span> when the LLM's safety layer is doing the refusing.
          </div>
        </div>

        {/* Phase 4: Closing tagline (1052 → 1198f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.failureNotMemory, CUE.failureNotMemory + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.55), rgba(0,0,0,0.85))`,
          }}
        >
          <AnimatedText
            text="The failure isn't in the memory."
            startFrame={CUE.failureNotMemory + 5}
            fontSize={36}
            color={COLORS.textMuted}
            textAlign="center"
            mode="wordByWord"
            durationFrames={70}
          />
          <AnimatedText
            text="It's the LLM's safety layer."
            startFrame={CUE.llmSafetyLayer - 30}
            fontSize={48}
            fontWeight={800}
            color={COLORS.accent}
            glow
            textAlign="center"
            mode="wordByWord"
            durationFrames={50}
            style={{ marginTop: 16 }}
          />
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
