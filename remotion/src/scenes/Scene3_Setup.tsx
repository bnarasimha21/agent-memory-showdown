import React from "react";
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
import { AnimatedCounter } from "../components/AnimatedCounter";
import { FadeTransition } from "../components/FadeTransition";
import { SEEDED_FACTS, BACKENDS } from "../data/benchmarkData";

// Cue points synced to public/audio/scene03.wav (whisper word-level, 30fps).
// Audio trimmed 0.4s at start, end at 71.85s (shift -12 frames from original).
const CUE = {
  intro: 0,                  // 0s "Here"
  introEnd: 49,              // 2.21s end "works"
  dropletReveal: 65,         // 2.72s "I spun up"
  ramSpec: 132,              // 4.97s "8 gigs of RAM"
  vcpuSpec: 161,             // 5.92s "4 vCPUs"
  ubuntuSpec: 201,           // 7.25s "Ubuntu 24.04"
  bangaloreSpec: 266,        // 9.44s "Bangalore"
  qdrantReveal: 323,         // 11.32s "Qdrant"
  postgresReveal: 360,       // 12.57s "postgres"
  pgvectorTag: 419,          // 14.53s "PG vector extension"
  llmReveal: 464,            // 16.04s "The LLM is"
  claudeName: 486,           // 16.76s "Claude"
  doInferenceLink: 586,      // 20.09s "DigitalOcean serverless"
  embeddingsReveal: 643,     // 22.00s "Embeddings"
  modelName: 787,            // 26.80s "all-MiniLM-L6-v2"
  infraEnd: 836,             // 28.43s (next phase starts)
  conversationStart: 851,    // 28.95s "The benchmark generates"
  topicTravel: 993,         // 33.66s
  topicTech: 1021,           // 34.60s
  topicPersonal: 1055,       // 35.74s
  topicWork: 1089,           // 36.87s
  topicChatbot: 1119,        // 37.85s
  butHidden: 1175,           // 39.72s "But hidden"
  factsRevealStart: 1258,    // 42.51s pins start appearing
  factsRevealEnd: 1306,      // 44.09s
  atTurns15_50: 1340,        // 45.24s "At turns 15 and 50"
  pauseAndQuiz: 1398,        // 47.16s "the benchmark pauses"
  quizzesAI: 1465,           // 49.41s "quizzes the AI"
  memoryDecayCurve: 1583,    // 53.35s "memory decay curve"
  howMuchForget: 1624,       // 54.70s "How much"
  decayEnd: 1722,            // 57.97s
  eachBackend5x: 1737,       // 58.47s "Each backend runs 5 times"
  statsReliable: 1785,       // 60.08s "statistical reliability"
  thatsMath: 1838,           // 61.84s "That's"
  fourBackends: 1860,        // 62.56s "four backends"
  fiveRuns: 1889,            // 63.52s "five runs"
  fiftyTurns: 1922,          // 64.63s "50 turns"
  equalsAtLeast: 1956,       // 65.77s "equal to"
  thousandLLMCalls: 1974,    // 66.37s "1000 LLM calls"
  end: 2051,                 // 69.10s audio end (2073 frames @30fps)
};

// Box width used throughout the diagram
const BOX_W = 280;

// Infrastructure boxes with reveal cues.
// Topology: droplet hosts qdrant/postgres/embeddings (below).
// Claude is REMOTE, reached via DO Serverless Inference (right of droplet).
const INFRA_BOXES = [
  {
    key: "droplet",
    label: "DO Droplet",
    sub: "",
    icon: "☁️",
    x: 480,
    y: 180,
    reveal: CUE.dropletReveal,
  },
  {
    key: "dosi",
    label: "DO Serverless",
    sub: "Inference API",
    icon: "🌐",
    x: 1380,
    y: 180,
    reveal: CUE.doInferenceLink,
  },
  {
    key: "claude",
    label: "Claude 4.5 Sonnet",
    sub: "",
    icon: "🧠",
    x: 1380,
    y: 600,
    reveal: CUE.llmReveal,
  },
  {
    key: "qdrant",
    label: "Qdrant",
    sub: "Docker container",
    icon: "📦",
    x: 260,
    y: 600,
    reveal: CUE.qdrantReveal,
  },
  {
    key: "postgres",
    label: "PostgreSQL 16",
    sub: "+ pgvector ext",
    icon: "🐘",
    x: 640,
    y: 600,
    reveal: CUE.postgresReveal,
  },
  {
    key: "embeddings",
    label: "Embeddings",
    sub: "all-MiniLM-L6-v2 · 384d",
    icon: "🔢",
    x: 1020,
    y: 600,
    reveal: CUE.embeddingsReveal,
  },
];

// Connections by box key, with explicit direction type so we can anchor
// lines on the right edge (horizontal) vs bottom edge (vertical).
const CONNECTIONS: { from: string; to: string; type: "down" | "right"; reveal: number }[] = [
  { from: "droplet", to: "dosi",       type: "right", reveal: CUE.llmReveal },
  { from: "dosi",    to: "claude",     type: "down",  reveal: CUE.claudeName },
  { from: "droplet", to: "qdrant",     type: "down",  reveal: CUE.qdrantReveal + 10 },
  { from: "droplet", to: "postgres",   type: "down",  reveal: CUE.postgresReveal + 10 },
  { from: "droplet", to: "embeddings", type: "down",  reveal: CUE.embeddingsReveal + 10 },
];

const TOPICS = [
  { label: "Travel planning", reveal: CUE.topicTravel },
  { label: "Tech preferences", reveal: CUE.topicTech },
  { label: "Personal details", reveal: CUE.topicPersonal },
  { label: "Work projects", reveal: CUE.topicWork },
];

export const Scene3_Setup: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene03.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 60% 30%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: Infrastructure diagram (0 → 910f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [0, 15, CUE.infraEnd - 25, CUE.infraEnd + 10],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: 60,
          }}
        >
          <AnimatedText
            text="The Setup"
            startFrame={5}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
            style={{
              opacity: interpolate(
                frame,
                [5, 35, CUE.infraEnd - 25, CUE.infraEnd],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              marginBottom: 30,
            }}
          />

          {/* Connection lines.
              SVG positioned at top:0/left:0 with viewport coords.
              Each box renders at viewport (box.x, box.y + 60). Box height ~180-220
              depending on sub-label wrapping; we use a fixed 180 estimate for anchors. */}
          <svg
            width={1920}
            height={1080}
            style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none" }}
          >
            {CONNECTIONS.map((conn, i) => {
              const from = INFRA_BOXES.find((b) => b.key === conn.from)!;
              const to = INFRA_BOXES.find((b) => b.key === conn.to)!;
              const opacity = interpolate(
                frame,
                [conn.reveal, conn.reveal + 20],
                [0, 0.55],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );

              const BOX_H = 180;
              const fromTop = from.y + 60;
              const fromBottom = fromTop + BOX_H;
              const fromMidY = fromTop + BOX_H / 2;
              const fromRight = from.x + BOX_W;
              const fromCenterX = from.x + BOX_W / 2;

              const toTop = to.y + 60;
              const toMidY = toTop + BOX_H / 2;
              const toCenterX = to.x + BOX_W / 2;
              const toLeft = to.x;

              let x1: number, y1: number, x2: number, y2: number;
              if (conn.type === "right") {
                x1 = fromRight;
                y1 = fromMidY;
                x2 = toLeft;
                y2 = toMidY;
              } else {
                // "down"
                x1 = fromCenterX;
                y1 = fromBottom;
                x2 = toCenterX;
                y2 = toTop;
              }

              return (
                <g key={i} opacity={opacity}>
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={COLORS.accent}
                    strokeWidth={2.5}
                    strokeDasharray="10,6"
                  />
                  {/* Arrow head */}
                  <circle
                    cx={x2}
                    cy={y2}
                    r={5}
                    fill={COLORS.accent}
                  />
                </g>
              );
            })}
          </svg>

          {INFRA_BOXES.map((box, i) => {
            const boxScale = spring({
              frame: Math.max(0, frame - box.reveal),
              fps,
              config: { damping: 14, stiffness: 100 },
            });
            const boxOpacity = interpolate(
              frame,
              [box.reveal, box.reveal + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: box.x,
                  top: box.y + 60,
                  transform: `scale(${boxScale})`,
                  opacity: boxOpacity,
                  background: COLORS.bgCard,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 16,
                  padding: "28px 30px",
                  textAlign: "center",
                  backdropFilter: "blur(10px)",
                  width: 280,
                  boxShadow: `0 0 30px ${COLORS.accentGlow}11`,
                }}
              >
                <div style={{ fontSize: 64, marginBottom: 12 }}>{box.icon}</div>
                <div
                  style={{
                    fontFamily: FONTS.body,
                    fontSize: 30,
                    fontWeight: 800,
                    color: COLORS.text,
                    letterSpacing: -0.5,
                  }}
                >
                  {box.label}
                </div>
                {box.sub && (
                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 20,
                      color: COLORS.textMuted,
                      marginTop: 10,
                    }}
                  >
                    {box.sub}
                  </div>
                )}
              </div>
            );
          })}

          {/* Droplet spec callouts hugging the Droplet box left/right */}
          {[
            { label: "8 GB RAM",      reveal: CUE.ramSpec,       x: 300, y: 270 },
            { label: "4 vCPUs",       reveal: CUE.vcpuSpec,      x: 300, y: 350 },
            { label: "Ubuntu 24.04",  reveal: CUE.ubuntuSpec,    x: 790, y: 270 },
            { label: "Bangalore 🇮🇳", reveal: CUE.bangaloreSpec, x: 790, y: 350 },
          ].map((s) => (
            <div
              key={s.label}
              style={{
                position: "absolute",
                left: s.x,
                top: s.y,
                fontFamily: FONTS.mono,
                fontSize: 22,
                fontWeight: 600,
                color: COLORS.accent,
                background: "rgba(0,212,255,0.10)",
                border: `1px solid ${COLORS.accent}55`,
                borderRadius: 10,
                padding: "10px 20px",
                boxShadow: `0 0 16px ${COLORS.accentGlow}33`,
                opacity: interpolate(
                  frame,
                  [s.reveal, s.reveal + 14],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
                transform: `translateX(${interpolate(
                  frame,
                  [s.reveal, s.reveal + 14],
                  [-12, 0],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )}px)`,
              }}
            >
              {s.label}
            </div>
          ))}

        </div>

        {/* Phase 2: 50-turn conversation + topics + facts (910 → 1390f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.conversationStart, CUE.conversationStart + 20, CUE.factsRevealEnd - 10, CUE.factsRevealEnd + 10],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: "50px 80px",
          }}
        >
          {/* Small section label */}
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 30,
              fontWeight: 700,
              color: COLORS.textMuted,
              letterSpacing: 6,
              textTransform: "uppercase",
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.conversationStart + 10, CUE.conversationStart + 35],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            50-turn conversation
          </div>

          {/* Topic chips with embedded facts that surface at "but hidden" */}
          <div
            style={{
              display: "flex",
              gap: 18,
              justifyContent: "center",
              marginTop: 60,
              flexWrap: "wrap",
            }}
          >
            {TOPICS.map((t) => (
              <div
                key={t.label}
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 26,
                  color: COLORS.text,
                  background: COLORS.bgCard,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 32,
                  padding: "14px 28px",
                  opacity: interpolate(
                    frame,
                    [t.reveal, t.reveal + 15, CUE.butHidden, CUE.butHidden + 30],
                    [0, 1, 1, 0.15],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  ),
                  transform: `translateY(${interpolate(
                    frame,
                    [t.reveal, t.reveal + 15],
                    [12, 0],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  )}px) scale(${interpolate(
                    frame,
                    [CUE.butHidden, CUE.butHidden + 25],
                    [1, 0.85],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  )})`,
                }}
              >
                {t.label}
              </div>
            ))}
          </div>

          {/* Magnifying-glass "x-ray" beat at "but hidden" */}
          <div
            style={{
              position: "absolute",
              top: 240,
              left: 0,
              right: 0,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.butHidden, CUE.butHidden + 20, CUE.factsRevealStart + 10, CUE.factsRevealStart + 30],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <div style={{ fontSize: 72 }}>🔍</div>
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 22,
                color: COLORS.accent,
                marginTop: 12,
                letterSpacing: 4,
                textTransform: "uppercase",
                textShadow: `0 0 20px ${COLORS.accentGlow}`,
              }}
            >
              10 facts hidden inside
            </div>
          </div>

          {/* Prominent timeline bar */}
          <div
            style={{
              position: "absolute",
              top: 420,
              left: 100,
              right: 100,
              height: 6,
              background: COLORS.border,
              borderRadius: 3,
              opacity: interpolate(
                frame,
                [CUE.factsRevealStart - 20, CUE.factsRevealStart],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${interpolate(
                  frame,
                  [CUE.factsRevealStart, CUE.factsRevealStart + 60],
                  [0, 100],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )}%`,
                background: `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.neonGreen})`,
                borderRadius: 3,
              }}
            />
          </div>

          {/* Turn-axis markers (1, 10, 20, 30, 40, 50) */}
          {[1, 10, 20, 30, 40, 50].map((turn) => (
            <div
              key={turn}
              style={{
                position: "absolute",
                top: 438,
                left: `${100 + ((turn - 1) / 49) * (1920 - 200)}px`,
                transform: "translateX(-50%)",
                fontFamily: FONTS.mono,
                fontSize: 20,
                fontWeight: 600,
                color: COLORS.textMuted,
                opacity: interpolate(
                  frame,
                  [CUE.factsRevealStart, CUE.factsRevealStart + 30],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
              }}
            >
              {turn}
            </div>
          ))}

          {/* Fact pins on timeline (big & glowing, no text labels here) */}
          {SEEDED_FACTS.map((f, i) => {
            const pinFrame = CUE.factsRevealStart + i * 10;
            const pinOpacity = interpolate(frame, [pinFrame, pinFrame + 15], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const pinY = interpolate(frame, [pinFrame, pinFrame + 15], [-15, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const xPos = 100 + ((f.turn - 1) / 49) * (1920 - 200);

            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  top: 411,
                  left: xPos - 12,
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  background: COLORS.accent,
                  opacity: pinOpacity,
                  transform: `translateY(${pinY}px)`,
                  boxShadow: `0 0 22px ${COLORS.accentGlow}, 0 0 4px ${COLORS.accent}`,
                  border: `2px solid #0a0a0f`,
                }}
              />
            );
          })}

          {/* Fact cards in 2×5 grid BELOW the timeline */}
          <div
            style={{
              position: "absolute",
              top: 500,
              left: 60,
              right: 60,
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gridTemplateRows: "repeat(2, 1fr)",
              gap: 20,
            }}
          >
            {SEEDED_FACTS.map((f, i) => {
              const cardFrame = CUE.factsRevealStart + i * 10;
              const cardOpacity = interpolate(
                frame,
                [cardFrame, cardFrame + 18],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );
              const cardY = interpolate(
                frame,
                [cardFrame, cardFrame + 18],
                [16, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );
              return (
                <div
                  key={i}
                  style={{
                    opacity: cardOpacity,
                    transform: `translateY(${cardY}px)`,
                    background: COLORS.bgCard,
                    border: `1px solid ${COLORS.accent}33`,
                    borderRadius: 12,
                    padding: "18px 20px",
                    backdropFilter: "blur(8px)",
                    boxShadow: `0 0 18px ${COLORS.accentGlow}11`,
                    minHeight: 110,
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "flex-start",
                  }}
                >
                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 18,
                      fontWeight: 700,
                      color: COLORS.accent,
                      letterSpacing: 1,
                      textTransform: "uppercase",
                      marginBottom: 10,
                    }}
                  >
                    Turn {f.turn}
                  </div>
                  <div
                    style={{
                      fontFamily: FONTS.body,
                      fontSize: 20,
                      fontWeight: 500,
                      color: COLORS.text,
                      lineHeight: 1.35,
                    }}
                  >
                    {f.fact}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Phase 3: Quiz markers + memory decay curve (1390 → 1814f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.atTurns15_50, CUE.atTurns15_50 + 20, CUE.decayEnd - 10, CUE.decayEnd + 10],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: "50px 80px",
          }}
        >
          {/* === TIMELINE WITH BIG QUIZ MARKERS (top of phase 3) === */}

          {/* Timeline bar */}
          <div
            style={{
              position: "absolute",
              top: 340,
              left: 100,
              right: 100,
              height: 8,
              background: COLORS.border,
              borderRadius: 4,
            }}
          >
            <div
              style={{
                height: "100%",
                width: "100%",
                background: `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.neonGreen})`,
                borderRadius: 4,
                opacity: 0.55,
              }}
            />
          </div>

          {/* Turn axis markers (1, 15, 50) below the bar */}
          {[1, 15, 50].map((turn) => (
            <div
              key={turn}
              style={{
                position: "absolute",
                top: 360,
                left: `${100 + ((turn - 1) / 49) * (1920 - 200)}px`,
                transform: "translateX(-50%)",
                fontFamily: FONTS.mono,
                fontSize: 26,
                fontWeight: 700,
                color: COLORS.textMuted,
              }}
            >
              {turn}
            </div>
          ))}

          {/* BIG QUIZ markers above the bar */}
          {[15, 50].map((turn, i) => {
            const quizFrame = CUE.pauseAndQuiz + i * 80;
            const quizOpacity = interpolate(
              frame,
              [quizFrame, quizFrame + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const pulse =
              frame >= quizFrame
                ? 0.6 + 0.4 * Math.sin((frame - quizFrame) * 0.15)
                : 0;
            const xPos = 100 + ((turn - 1) / 49) * (1920 - 200);
            return (
              <div
                key={turn}
                style={{
                  position: "absolute",
                  top: 140,
                  left: xPos - 130,
                  width: 260,
                  textAlign: "center",
                  opacity: quizOpacity,
                }}
              >
                <div style={{ fontSize: 72, marginBottom: 8 }}>❓</div>
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 36,
                    fontWeight: 800,
                    color: COLORS.neonGreen,
                    background: "rgba(0,255,136,0.14)",
                    border: `2px solid rgba(0,255,136,0.55)`,
                    borderRadius: 14,
                    padding: "14px 28px",
                    letterSpacing: 3,
                    boxShadow: `0 0 ${28 + pulse * 24}px rgba(0,255,136,${0.35 + pulse * 0.35})`,
                  }}
                >
                  QUIZ
                </div>
              </div>
            );
          })}

          {/* === BIG MEMORY DECAY CURVE === */}
          <div
            style={{
              position: "absolute",
              top: 460,
              left: 0,
              right: 0,
              opacity: interpolate(
                frame,
                [CUE.memoryDecayCurve, CUE.memoryDecayCurve + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <div
              style={{
                fontFamily: FONTS.body,
                fontSize: 40,
                fontWeight: 700,
                color: COLORS.accent,
                textAlign: "center",
                marginBottom: 24,
                textShadow: `0 0 24px ${COLORS.accentGlow}`,
              }}
            >
              ↘ Memory Decay Curve
            </div>
            <svg
              width={1500}
              height={500}
              style={{ display: "block", margin: "0 auto" }}
              viewBox="0 0 1500 500"
            >
              {/* Axes */}
              <line x1={120} y1={60} x2={120} y2={430} stroke={COLORS.border} strokeWidth={2} />
              <line x1={120} y1={430} x2={1430} y2={430} stroke={COLORS.border} strokeWidth={2} />

              {/* Faint gridlines for readability */}
              {[0.25, 0.5, 0.75].map((g) => (
                <line
                  key={g}
                  x1={120}
                  y1={60 + g * 370}
                  x2={1430}
                  y2={60 + g * 370}
                  stroke={COLORS.border}
                  strokeWidth={1}
                  strokeDasharray="4,8"
                  opacity={0.4}
                />
              ))}

              {/* Decay curve */}
              <path
                d="M 150 75 Q 600 100 850 240 T 1400 400"
                stroke={COLORS.danger}
                strokeWidth={6}
                fill="none"
                strokeDasharray={2000}
                strokeDashoffset={interpolate(
                  frame,
                  [CUE.howMuchForget, CUE.howMuchForget + 70],
                  [2000, 0],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )}
                style={{ filter: `drop-shadow(0 0 12px ${COLORS.dangerGlow})` }}
              />

              {/* Y axis labels */}
              <text
                x={100}
                y={75}
                fontFamily={FONTS.mono}
                fontSize={26}
                fontWeight={700}
                fill={COLORS.text}
                textAnchor="end"
              >
                100%
              </text>
              <text
                x={100}
                y={430}
                fontFamily={FONTS.mono}
                fontSize={26}
                fontWeight={700}
                fill={COLORS.text}
                textAnchor="end"
              >
                0%
              </text>

              {/* X axis labels */}
              <text
                x={150}
                y={475}
                fontFamily={FONTS.mono}
                fontSize={24}
                fill={COLORS.textMuted}
              >
                turn 1
              </text>
              <text
                x={1400}
                y={475}
                fontFamily={FONTS.mono}
                fontSize={24}
                fill={COLORS.textMuted}
                textAnchor="end"
              >
                turn 50
              </text>

              {/* "recall %" Y-axis title */}
              <text
                x={50}
                y={245}
                fontFamily={FONTS.mono}
                fontSize={22}
                fontWeight={600}
                fill={COLORS.textMuted}
                transform="rotate(-90, 50, 245)"
                textAnchor="middle"
              >
                recall
              </text>
            </svg>
          </div>
        </div>

        {/* Phase 4: The math (1824 → 2176f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.eachBackend5x, CUE.eachBackend5x + 20],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* 4×5 grid of run-dots — concrete visualization of scale */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "220px repeat(5, 120px)",
              gridTemplateRows: "repeat(4, 120px)",
              gap: 20,
              marginBottom: 60,
              opacity: interpolate(
                frame,
                [CUE.eachBackend5x, CUE.eachBackend5x + 15, CUE.thatsMath - 5, CUE.thatsMath + 25],
                [0, 1, 1, 0.4],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            {BACKENDS.map((b, bi) => (
              <React.Fragment key={b}>
                {/* Backend label */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "flex-end",
                    paddingRight: 24,
                    fontFamily: FONTS.mono,
                    fontSize: 34,
                    fontWeight: 800,
                    color: BACKEND_COLORS[b],
                    textShadow: `0 0 14px ${BACKEND_COLORS[b]}55`,
                  }}
                >
                  {b}
                </div>
                {/* 5 run dots */}
                {Array.from({ length: 5 }).map((_, ri) => {
                  const dotFrame = CUE.eachBackend5x + 30 + (bi * 5 + ri) * 6;
                  const dotOpacity = interpolate(
                    frame,
                    [dotFrame, dotFrame + 12],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  );
                  const dotScale = interpolate(
                    frame,
                    [dotFrame, dotFrame + 12],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  );
                  return (
                    <div
                      key={ri}
                      style={{
                        width: 120,
                        height: 120,
                        borderRadius: 22,
                        background: `linear-gradient(135deg, ${BACKEND_COLORS[b]}, ${BACKEND_COLORS[b]}88)`,
                        opacity: dotOpacity,
                        transform: `scale(${dotScale})`,
                        boxShadow: `0 0 24px ${BACKEND_COLORS[b]}77`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: FONTS.mono,
                        fontSize: 48,
                        fontWeight: 800,
                        color: "#fff",
                      }}
                    >
                      ▶
                    </div>
                  );
                })}
              </React.Fragment>
            ))}
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 28,
              fontFamily: FONTS.mono,
              fontSize: 56,
              color: COLORS.text,
              opacity: interpolate(
                frame,
                [CUE.thatsMath, CUE.thatsMath + 15],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            {[
              { value: 4, label: "backends", reveal: CUE.fourBackends, color: COLORS.accent },
              { value: 5, label: "runs", reveal: CUE.fiveRuns, color: COLORS.accent },
              { value: 50, label: "turns", reveal: CUE.fiftyTurns, color: COLORS.accent },
            ].map((stat, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 28 }}>
                {i > 0 && (
                  <span
                    style={{
                      color: COLORS.textMuted,
                      fontSize: 40,
                      opacity: interpolate(frame, [stat.reveal - 10, stat.reveal + 5], [0, 1], {
                        extrapolateLeft: "clamp",
                        extrapolateRight: "clamp",
                      }),
                    }}
                  >
                    ×
                  </span>
                )}
                <GlassCard startFrame={stat.reveal} padding={28}>
                  <div style={{ textAlign: "center", minWidth: 160 }}>
                    <AnimatedCounter
                      value={stat.value}
                      startFrame={stat.reveal + 8}
                      fontSize={64}
                      color={stat.color}
                    />
                    <div
                      style={{
                        fontFamily: FONTS.body,
                        fontSize: 22,
                        fontWeight: 600,
                        color: COLORS.textMuted,
                        marginTop: 6,
                      }}
                    >
                      {stat.label}
                    </div>
                  </div>
                </GlassCard>
              </div>
            ))}
          </div>

          {/* = 1000+ LLM calls */}
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 40,
              color: COLORS.text,
              marginTop: 60,
              display: "flex",
              alignItems: "center",
              gap: 20,
              opacity: interpolate(
                frame,
                [CUE.equalsAtLeast, CUE.equalsAtLeast + 15],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            =
            <AnimatedCounter
              value={1000}
              startFrame={CUE.thousandLLMCalls}
              fontSize={64}
              color={COLORS.neonGreen}
              suffix="+"
            />
            <span style={{ color: COLORS.neonGreen, textShadow: `0 0 20px rgba(0,255,136,0.4)` }}>
              LLM calls
            </span>
          </div>
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
