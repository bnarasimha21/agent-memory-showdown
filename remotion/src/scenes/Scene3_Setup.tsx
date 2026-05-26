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
import { AnimatedCounter } from "../components/AnimatedCounter";
import { FadeTransition } from "../components/FadeTransition";
import { SEEDED_FACTS } from "../data/benchmarkData";

// Cue points synced to public/audio/scene03.wav (whisper word-level, 30fps).
const CUE = {
  intro: 0,                  // 0.00s "Here"
  introEnd: 70,              // 2.30s end "works"
  dropletReveal: 70,         // 2.30s "I spun up"
  ramSpec: 146,              // 4.87s "8 gigs of RAM"
  vcpuSpec: 197,             // 6.56s "4 vCPUs"
  ubuntuSpec: 227,           // 7.55s "Ubuntu 24.04"
  bangaloreSpec: 308,        // 10.25s "Bangalore"
  qdrantReveal: 354,         // 11.81s "Qdrant"
  postgresReveal: 396,       // 13.20s "postgres"
  pgvectorTag: 471,          // 15.70s "PG vector extension"
  llmReveal: 521,            // 17.35s "The LLM is"
  claudeName: 538,           // 17.93s "Claude"
  doInferenceLink: 614,      // 20.51s "DigitalOcean serverless"
  embeddingsReveal: 700,     // 23.33s "Embeddings"
  modelName: 826,            // 27.52s "all-MiniLM-L6-v2"
  infraEnd: 910,             // 30.34s (next phase starts)
  conversationStart: 910,    // 30.34s "The benchmark generates"
  topicTravel: 1046,         // 34.88s
  topicTech: 1083,           // 36.13s
  topicPersonal: 1114,       // 37.15s
  topicWork: 1145,           // 38.16s
  topicChatbot: 1184,        // 39.68s
  butHidden: 1234,           // 41.12s "But hidden"
  factsRevealStart: 1268,    // 42.27s pins start appearing
  factsRevealEnd: 1390,      // 46.32s
  atTurns15_50: 1390,        // 46.32s "At turns 15 and 50"
  pauseAndQuiz: 1474,        // 49.14s "the benchmark pauses"
  quizzesAI: 1542,           // 51.39s "quizzes the AI"
  memoryDecayCurve: 1634,    // 54.48s "This builds the memory decay curve"
  howMuchForget: 1719,       // 57.30s "How much"
  decayEnd: 1814,            // 60.45s
  eachBackend5x: 1824,       // 60.80s "Each backend runs 5 times"
  statsReliable: 1899,       // 63.32s
  thatsMath: 1955,           // 65.03s "That's"
  fourBackends: 1970,        // 65.66s "four backends"
  fiveRuns: 2016,            // 67.22s "five runs"
  fiftyTurns: 2045,          // 68.16s "50 turns"
  equalsAtLeast: 2070,       // 68.99s "equal to at least"
  thousandLLMCalls: 2104,    // 70.13s "1000 LLM calls"
  end: 2176,                 // 72.52s
};

// Infrastructure boxes with reveal cues
const INFRA_BOXES = [
  {
    key: "droplet",
    label: "DO Droplet",
    sub: "Bangalore · Ubuntu 24.04",
    icon: "☁️",
    x: 580,
    y: 150,
    reveal: CUE.dropletReveal,
  },
  {
    key: "qdrant",
    label: "Qdrant",
    sub: "Docker container",
    icon: "📦",
    x: 280,
    y: 420,
    reveal: CUE.qdrantReveal,
  },
  {
    key: "postgres",
    label: "PostgreSQL 16",
    sub: "+ pgvector extension",
    icon: "🐘",
    x: 580,
    y: 420,
    reveal: CUE.postgresReveal,
  },
  {
    key: "claude",
    label: "Claude 4.5 Sonnet",
    sub: "DO Serverless Inference",
    icon: "🧠",
    x: 1180,
    y: 150,
    reveal: CUE.llmReveal,
  },
  {
    key: "embeddings",
    label: "Embeddings",
    sub: "all-MiniLM-L6-v2 · 384-dim",
    icon: "🔢",
    x: 1180,
    y: 420,
    reveal: CUE.embeddingsReveal,
  },
];

const CONNECTIONS = [
  { from: 0, to: 1, reveal: CUE.qdrantReveal + 10 },
  { from: 0, to: 2, reveal: CUE.postgresReveal + 10 },
  { from: 0, to: 3, reveal: CUE.doInferenceLink },
  { from: 0, to: 4, reveal: CUE.embeddingsReveal + 10 },
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
            text="Here's how the benchmark works."
            startFrame={CUE.intro + 2}
            fontSize={36}
            color={COLORS.textMuted}
            textAlign="center"
            mode="wordByWord"
            durationFrames={50}
            style={{
              opacity: interpolate(
                frame,
                [0, 10, 75, 100],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          />

          <AnimatedText
            text="Infrastructure"
            startFrame={90}
            fontSize={42}
            fontWeight={700}
            textAlign="center"
            style={{
              opacity: interpolate(
                frame,
                [90, 120, CUE.infraEnd - 25, CUE.infraEnd],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              marginBottom: 30,
            }}
          />

          {/* Connection lines */}
          <svg
            width={1920}
            height={700}
            style={{ position: "absolute", top: 100, left: 0, pointerEvents: "none" }}
          >
            {CONNECTIONS.map((conn, i) => {
              const from = INFRA_BOXES[conn.from];
              const to = INFRA_BOXES[conn.to];
              const opacity = interpolate(
                frame,
                [conn.reveal, conn.reveal + 20],
                [0, 0.5],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );
              return (
                <line
                  key={i}
                  x1={from.x + 100}
                  y1={from.y + 80}
                  x2={to.x + 100}
                  y2={to.y + 30}
                  stroke={COLORS.accent}
                  strokeWidth={2}
                  opacity={opacity}
                  strokeDasharray="8,4"
                />
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
                  borderRadius: 14,
                  padding: "18px 24px",
                  textAlign: "center",
                  backdropFilter: "blur(10px)",
                  width: 220,
                  boxShadow: `0 0 30px ${COLORS.accentGlow}11`,
                }}
              >
                <div style={{ fontSize: 32, marginBottom: 6 }}>{box.icon}</div>
                <div
                  style={{
                    fontFamily: FONTS.body,
                    fontSize: 18,
                    fontWeight: 600,
                    color: COLORS.text,
                  }}
                >
                  {box.label}
                </div>
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 12,
                    color: COLORS.textMuted,
                    marginTop: 6,
                  }}
                >
                  {box.sub}
                </div>
              </div>
            );
          })}

          {/* Droplet spec callouts that pop in next to the Droplet box */}
          {[
            { label: "8 GB RAM", reveal: CUE.ramSpec, x: 470, y: 110 },
            { label: "4 vCPUs", reveal: CUE.vcpuSpec, x: 470, y: 160 },
            { label: "Ubuntu 24.04", reveal: CUE.ubuntuSpec, x: 820, y: 110 },
            { label: "Bangalore 🇮🇳", reveal: CUE.bangaloreSpec, x: 820, y: 160 },
          ].map((s) => (
            <div
              key={s.label}
              style={{
                position: "absolute",
                left: s.x,
                top: s.y,
                fontFamily: FONTS.mono,
                fontSize: 14,
                color: COLORS.accent,
                background: "rgba(0,212,255,0.08)",
                border: `1px solid ${COLORS.accent}44`,
                borderRadius: 6,
                padding: "4px 10px",
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

          {/* pgvector tag highlight on postgres box */}
          {frame >= CUE.pgvectorTag && (
            <div
              style={{
                position: "absolute",
                left: INFRA_BOXES[2].x + 230,
                top: INFRA_BOXES[2].y + 130,
                fontFamily: FONTS.mono,
                fontSize: 13,
                color: COLORS.neonGreen,
                background: "rgba(0,255,136,0.10)",
                border: `1px solid ${COLORS.neonGreen}44`,
                borderRadius: 6,
                padding: "4px 10px",
                opacity: interpolate(
                  frame,
                  [CUE.pgvectorTag, CUE.pgvectorTag + 15],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
              }}
            >
              + pgvector ext
            </div>
          )}
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
          <AnimatedText
            text="Synthetic 50-Turn Conversation"
            startFrame={CUE.conversationStart + 10}
            fontSize={42}
            fontWeight={700}
            textAlign="center"
          />

          {/* Topic chips */}
          <div
            style={{
              display: "flex",
              gap: 16,
              justifyContent: "center",
              marginTop: 50,
              flexWrap: "wrap",
            }}
          >
            {TOPICS.map((t) => (
              <div
                key={t.label}
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 22,
                  color: COLORS.text,
                  background: COLORS.bgCard,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 28,
                  padding: "10px 22px",
                  opacity: interpolate(
                    frame,
                    [t.reveal, t.reveal + 15, CUE.butHidden, CUE.butHidden + 30],
                    [0, 1, 1, 0.25],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  ),
                  transform: `translateY(${interpolate(
                    frame,
                    [t.reveal, t.reveal + 15],
                    [12, 0],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  )}px)`,
                }}
              >
                {t.label}
              </div>
            ))}
          </div>

          {/* "But hidden..." tagline */}
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 28,
              color: COLORS.accent,
              textAlign: "center",
              marginTop: 30,
              opacity: interpolate(
                frame,
                [CUE.butHidden, CUE.butHidden + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              textShadow: `0 0 20px ${COLORS.accentGlow}`,
            }}
          >
            But hidden inside: 10 specific facts.
          </div>

          {/* Timeline */}
          <div
            style={{
              position: "absolute",
              top: 460,
              left: 100,
              right: 100,
              height: 4,
              background: COLORS.border,
              borderRadius: 2,
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
                borderRadius: 2,
              }}
            />
          </div>

          {/* Turn markers */}
          {[1, 10, 20, 30, 40, 50].map((turn) => (
            <div
              key={turn}
              style={{
                position: "absolute",
                top: 472,
                left: `${100 + ((turn - 1) / 49) * (1920 - 200)}px`,
                transform: "translateX(-50%)",
                fontFamily: FONTS.mono,
                fontSize: 12,
                color: COLORS.textDim,
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

          {/* Fact pins (10 facts) */}
          {SEEDED_FACTS.map((f, i) => {
            const pinFrame = CUE.factsRevealStart + i * 12;
            const pinOpacity = interpolate(frame, [pinFrame, pinFrame + 15], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const pinY = interpolate(frame, [pinFrame, pinFrame + 15], [-15, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const xPos = 100 + ((f.turn - 1) / 49) * (1920 - 200);
            const isEven = i % 2 === 0;

            return (
              <div key={i}>
                <div
                  style={{
                    position: "absolute",
                    top: 454,
                    left: xPos - 6,
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background: COLORS.accent,
                    opacity: pinOpacity,
                    transform: `translateY(${pinY}px)`,
                    boxShadow: `0 0 12px ${COLORS.accentGlow}`,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: isEven ? 500 : 380,
                    left: xPos - 100,
                    width: 200,
                    textAlign: "center",
                    opacity: pinOpacity,
                    transform: `translateY(${pinY}px)`,
                  }}
                >
                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 11,
                      color: COLORS.accent,
                      marginBottom: 3,
                    }}
                  >
                    Turn {f.turn}
                  </div>
                  <div
                    style={{
                      fontFamily: FONTS.body,
                      fontSize: 12,
                      color: COLORS.text,
                      background: COLORS.bgCard,
                      border: `1px solid ${COLORS.border}`,
                      borderRadius: 8,
                      padding: "6px 8px",
                      lineHeight: 1.3,
                    }}
                  >
                    {f.fact}
                  </div>
                </div>
              </div>
            );
          })}
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
          <AnimatedText
            text="Quiz the AI. Build the decay curve."
            startFrame={CUE.atTurns15_50 + 10}
            fontSize={42}
            fontWeight={700}
            textAlign="center"
          />

          {/* Mini timeline with QUIZ markers */}
          <div
            style={{
              position: "absolute",
              top: 300,
              left: 100,
              right: 100,
              height: 4,
              background: COLORS.border,
              borderRadius: 2,
            }}
          >
            <div
              style={{
                height: "100%",
                width: "100%",
                background: `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.neonGreen})`,
                borderRadius: 2,
                opacity: 0.5,
              }}
            />
          </div>

          {[1, 15, 50].map((turn) => (
            <div
              key={turn}
              style={{
                position: "absolute",
                top: 312,
                left: `${100 + ((turn - 1) / 49) * (1920 - 200)}px`,
                transform: "translateX(-50%)",
                fontFamily: FONTS.mono,
                fontSize: 12,
                color: COLORS.textDim,
              }}
            >
              {turn}
            </div>
          ))}

          {[15, 50].map((turn, i) => {
            const quizFrame = CUE.pauseAndQuiz + i * 80;
            const quizOpacity = interpolate(
              frame,
              [quizFrame, quizFrame + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const xPos = 100 + ((turn - 1) / 49) * (1920 - 200);
            return (
              <div
                key={turn}
                style={{
                  position: "absolute",
                  top: 240,
                  left: xPos - 45,
                  width: 90,
                  textAlign: "center",
                  opacity: quizOpacity,
                }}
              >
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 14,
                    fontWeight: 700,
                    color: COLORS.neonGreen,
                    background: "rgba(0,255,136,0.12)",
                    border: `1px solid rgba(0,255,136,0.4)`,
                    borderRadius: 8,
                    padding: "4px 10px",
                    boxShadow: `0 0 16px rgba(0,255,136,0.3)`,
                  }}
                >
                  QUIZ
                </div>
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 12,
                    color: COLORS.textMuted,
                    marginTop: 4,
                  }}
                >
                  Turn {turn}
                </div>
              </div>
            );
          })}

          {/* Sketch memory decay curve */}
          <div
            style={{
              position: "absolute",
              top: 420,
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
                fontSize: 26,
                color: COLORS.accent,
                textAlign: "center",
                marginBottom: 16,
                textShadow: `0 0 20px ${COLORS.accentGlow}`,
              }}
            >
              ↘ Memory Decay Curve
            </div>
            <svg width={900} height={200} style={{ display: "block", margin: "0 auto" }}>
              <line x1={50} y1={180} x2={850} y2={180} stroke={COLORS.border} strokeWidth={1} />
              <line x1={50} y1={20} x2={50} y2={180} stroke={COLORS.border} strokeWidth={1} />
              <path
                d={`M 100 30 Q 350 40 450 90 T 800 170`}
                stroke={COLORS.danger}
                strokeWidth={3}
                fill="none"
                strokeDasharray={1500}
                strokeDashoffset={interpolate(
                  frame,
                  [CUE.howMuchForget, CUE.howMuchForget + 70],
                  [1500, 0],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )}
              />
              <text x={70} y={30} fontFamily={FONTS.mono} fontSize={12} fill={COLORS.textMuted}>100%</text>
              <text x={70} y={180} fontFamily={FONTS.mono} fontSize={12} fill={COLORS.textMuted}>0%</text>
              <text x={70} y={195} fontFamily={FONTS.mono} fontSize={12} fill={COLORS.textMuted}>turn 1</text>
              <text x={780} y={195} fontFamily={FONTS.mono} fontSize={12} fill={COLORS.textMuted}>turn 50</text>
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
          <AnimatedText
            text="Each backend runs 5 times."
            startFrame={CUE.eachBackend5x + 5}
            fontSize={36}
            color={COLORS.textMuted}
            textAlign="center"
            mode="wordByWord"
            durationFrames={50}
            style={{ marginBottom: 60 }}
          />

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 28,
              fontFamily: FONTS.mono,
              fontSize: 56,
              color: COLORS.text,
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
                        fontSize: 16,
                        color: COLORS.textMuted,
                        marginTop: 4,
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
