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
import { BACKENDS, RECALL_BY_SEED_TURN_AT_50 } from "../data/benchmarkData";

const SENSITIVE_FACTS = [
  { turn: 30, fact: "Wi-Fi password", index: 6 },
  { turn: 45, fact: "Bank PIN", index: 9 },
];

// Cue points synced to public/audio/scene08.wav (whisper word-level, 30fps).
const CUE = {
  intro: 11,                  // 0.36s "There"
  oneFinding: 30,             // 0.99s
  didntExpect: 71,            // 2.38s
  introEnd: 96,               // 3.21s
  everyBackend: 100,          // 3.36s
  includingBuffer: 121,       // 4.04s
  dataInPrompt: 184,          // 6.14s
  failedToRecall: 219,        // 7.29s
  wifiPassword: 262,          // 8.73s
  bankPIN: 311,               // 10.37s
  atTurn50: 333,              // 11.11s — FLASH HAPPENS HERE
  recallEnd: 363,             // 12.11s
  thisIsntMemory: 372,        // 12.42s
  safetyBehavior: 436,        // 14.53s
  safetyEnd: 469,             // 15.63s
  claudeRecognizes: 473,      // 15.78s
  sensitiveDataWord: 507,     // 16.92s
  declinesRepeat: 588,        // 19.62s
  explicitlyProvided: 672,    // 22.40s
  convHistory: 718,           // 23.94s
  claudeEnd: 757,             // 25.22s
  thisMatters: 764,           // 25.46s
  benchmarkDesign: 791,       // 26.36s
  testFacts: 921,             // 30.70s
  misleadingRecall: 1004,     // 33.49s
  matterEnd: 1044,            // 34.80s
  failureNotMemory: 1052,     // 35.06s
  llmSafetyLayer: 1133,       // 37.78s
  end: 1198,                  // 39.91s
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
              fontSize: 22,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 16,
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
            const tileH = 130;
            const gapX = 28;
            const gapY = 20;
            const rowHeaderW = 150;
            const gridLeft =
              (1920 -
                80 * 2 -
                (rowHeaderW + SENSITIVE_FACTS.length * (tileW + gapX) - gapX)) /
              2;
            const gridTop = 240;

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
                    <div style={{ fontSize: 28, marginBottom: 4 }}>🔒</div>
                    <div
                      style={{
                        fontFamily: FONTS.mono,
                        fontSize: 13,
                        color: COLORS.textMuted,
                      }}
                    >
                      Turn {sf.turn}
                    </div>
                    <div
                      style={{
                        fontFamily: FONTS.body,
                        fontSize: 20,
                        fontWeight: 600,
                        color: COLORS.text,
                        marginTop: 2,
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
                        const val = RECALL_BY_SEED_TURN_AT_50[b][sf.index];
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
                              <>
                                <div
                                  style={{
                                    fontFamily: FONTS.mono,
                                    fontSize: 44,
                                    fontWeight: 700,
                                    color: "#fff",
                                    lineHeight: 1,
                                  }}
                                >
                                  {val}%
                                </div>
                                <div
                                  style={{
                                    fontFamily: FONTS.mono,
                                    fontSize: 22,
                                    color: "rgba(255,255,255,0.9)",
                                    marginTop: 6,
                                  }}
                                >
                                  ✗ FAILED
                                </div>
                              </>
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

          {/* Tagline after flash */}
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 60,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.thisIsntMemory, CUE.thisIsntMemory + 15],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <AnimatedText
              text="This isn't a memory problem."
              startFrame={CUE.thisIsntMemory + 5}
              fontSize={32}
              fontWeight={600}
              color={COLORS.text}
              textAlign="center"
              mode="wordByWord"
              durationFrames={50}
            />
            <AnimatedText
              text="It's a safety behavior."
              startFrame={CUE.safetyBehavior - 12}
              fontSize={40}
              fontWeight={800}
              color={COLORS.accent}
              glow
              textAlign="center"
              mode="wordByWord"
              durationFrames={40}
              style={{ marginTop: 8 }}
            />
          </div>
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
            <GlassCard startFrame={CUE.declinesRepeat} padding={32}>
              <div
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 22,
                  color: COLORS.textMuted,
                  lineHeight: 1.6,
                  textAlign: "center",
                }}
              >
                Passwords and PINs trip a safety layer.{" "}
                <span style={{ color: COLORS.text, fontWeight: 600 }}>
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
              fontSize: 22,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 30,
              maxWidth: 1100,
              opacity: interpolate(
                frame,
                [CUE.testFacts, CUE.testFacts + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            Recall scores get <span style={{ color: COLORS.danger, fontWeight: 600 }}>misleading</span> when the LLM's safety layer is doing the refusing.
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
