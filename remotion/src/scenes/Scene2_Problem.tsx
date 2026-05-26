import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { GlassCard } from "../components/GlassCard";
import { BackendBadge } from "../components/BackendBadge";
import { AnimatedText } from "../components/AnimatedText";
import { FadeTransition } from "../components/FadeTransition";

const BACKENDS_INFO = [
  {
    name: "buffer",
    title: "Buffer Memory",
    desc: "Pass the entire conversation history into the prompt",
    strength: "Perfect recall (short-term)",
    weakness: "Context explodes, costs skyrocket",
    icon: "📋",
  },
  {
    name: "summary",
    title: "Summary Memory",
    desc: "LLM compresses conversation into a running summary",
    strength: "Lower token usage",
    weakness: "Lossy. Facts get summarized away",
    icon: "📝",
  },
  {
    name: "qdrant",
    title: "Vector Memory (Qdrant)",
    desc: "Embed messages, retrieve semantically relevant snippets",
    strength: "Fast, accurate, low cost",
    weakness: "Requires Qdrant service",
    icon: "🔍",
  },
  {
    name: "pgvector",
    title: "Vector Memory (pgvector)",
    desc: "Same idea, using PostgreSQL with pgvector extension",
    strength: "SQL-native, zero extra infra",
    weakness: "Slightly slower at massive scale",
    icon: "🐘",
  },
];

// Cue points synced to public/audio/scene02.wav (whisper word-level, 30fps).
const CUE = {
  introStart: 2,       // 0.08s "For"
  introEnd: 100,       // 3.17s end of "LangChain."
  titleStart: 110,     // 3.7s "LangChain gives..."
  weDiscuss: 351,      // 11.70s "We will discuss"
  titleEnd: 433,       // 14.10s end of "four of these"
  bufferReveal: 433,   // 14.42s "Buffer"
  bufferOverflowStart: 657, // 21.88s "context window"
  bufferExplodes: 687, // 22.90s "explodes"
  bufferEnd: 773,      // 25.54s end of "through the roof"
  summaryReveal: 773,  // 25.76s "The second one"
  summaryWarning: 985, // 32.82s "It sounds clever"
  summaryEnd: 1165,    // 38.50s end of "isn't worth keeping"
  qdrantReveal: 1165,  // 38.82s "Third is"
  qdrantEnd: 1551,     // 51.70s end of "surgical, efficient"
  pgvectorReveal: 1551,// 51.70s "Fourth is"
  pgvectorEnd: 1922,   // 63.77s end of "one less service to manage"
  questionAppear: 1922,// 64.08s "The question is"
  whoSurvives: 2099,   // 69.84s "who survives"
  end: 2138,           // 71.24s
};

export const Scene2_Problem: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene02.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 30% 60%, #0d1420 0%, ${COLORS.bg} 70%)`,
          padding: 80,
        }}
      >
        {/* Phase 1: LangChain intro (0 → 100f) */}
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
              [0, 10, CUE.introEnd - 10, CUE.introEnd + 6],
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
              marginBottom: 28,
              opacity: interpolate(frame, [CUE.introStart, CUE.introStart + 18], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            For this experiment
          </div>
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 120,
              fontWeight: 800,
              color: COLORS.text,
              letterSpacing: -3,
              textShadow: `0 0 60px ${COLORS.accentGlow}`,
              opacity: interpolate(frame, [CUE.introStart + 45, CUE.introStart + 60], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              transform: `scale(${interpolate(
                frame,
                [CUE.introStart + 45, CUE.introStart + 70],
                [0.85, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              )})`,
            }}
          >
            🦜 LangChain
          </div>
        </div>

        {/* Phase 2: Title + four cards (100 → 1922f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.titleStart, CUE.titleStart + 12, CUE.questionAppear - 20, CUE.questionAppear + 10],
              [0, 1, 1, 0.3],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: 60,
          }}
        >
          <AnimatedText
            text="Four Memory Strategies"
            startFrame={CUE.titleStart}
            fontSize={48}
            fontWeight={700}
            textAlign="center"
            style={{ marginBottom: 8 }}
          />
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 22,
              color: COLORS.textMuted,
              textAlign: "center",
              marginBottom: 40,
              opacity: interpolate(
                frame,
                [CUE.titleStart + 30, CUE.titleStart + 50],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            Trade-offs between recall, speed, and cost.
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 28,
              maxWidth: 1600,
              margin: "0 auto",
              marginTop: 10,
            }}
          >
            {BACKENDS_INFO.map((b, i) => {
              const revealFrame = [
                CUE.bufferReveal,
                CUE.summaryReveal,
                CUE.qdrantReveal,
                CUE.pgvectorReveal,
              ][i];
              const color = BACKEND_COLORS[b.name];

              // Active highlight: each card glows during its narration window
              const activeEnd = [
                CUE.bufferEnd,
                CUE.summaryEnd,
                CUE.qdrantEnd,
                CUE.pgvectorEnd,
              ][i];
              const isActive = frame >= revealFrame && frame < activeEnd;

              return (
                <div
                  key={b.name}
                  style={{
                    transform: `scale(${isActive ? 1.02 : 1})`,
                    transition: "transform 0.3s",
                  }}
                >
                  <GlassCard
                    startFrame={revealFrame}
                    glowColor={isActive ? `${color}88` : `${color}33`}
                    padding={28}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 14 }}>
                      <span style={{ fontSize: 32 }}>{b.icon}</span>
                      <div>
                        <BackendBadge name={b.name} fontSize={14} />
                        <div
                          style={{
                            fontFamily: FONTS.body,
                            fontSize: 24,
                            fontWeight: 600,
                            color: COLORS.text,
                            marginTop: 4,
                          }}
                        >
                          {b.title}
                        </div>
                      </div>
                    </div>
                    <div
                      style={{
                        fontFamily: FONTS.body,
                        fontSize: 18,
                        color: COLORS.textMuted,
                        marginBottom: 16,
                        lineHeight: 1.4,
                      }}
                    >
                      {b.desc}
                    </div>
                    <div style={{ display: "flex", gap: 12 }}>
                      <span
                        style={{
                          fontSize: 13,
                          fontFamily: FONTS.mono,
                          color: COLORS.neonGreen,
                          background: "rgba(0,255,136,0.08)",
                          padding: "3px 10px",
                          borderRadius: 6,
                        }}
                      >
                        + {b.strength}
                      </span>
                      <span
                        style={{
                          fontSize: 13,
                          fontFamily: FONTS.mono,
                          color: COLORS.danger,
                          background: "rgba(255,68,68,0.08)",
                          padding: "3px 10px",
                          borderRadius: 6,
                        }}
                      >
                        - {b.weakness}
                      </span>
                    </div>

                    {/* Buffer-only: mini context-window overflow at "explodes" cue */}
                    {b.name === "buffer" && (
                      <div
                        style={{
                          marginTop: 16,
                          opacity: interpolate(
                            frame,
                            [CUE.bufferOverflowStart, CUE.bufferOverflowStart + 20],
                            [0, 1],
                            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                          ),
                        }}
                      >
                        <div
                          style={{
                            fontFamily: FONTS.mono,
                            fontSize: 12,
                            color: COLORS.textMuted,
                            marginBottom: 6,
                          }}
                        >
                          Context Window
                        </div>
                        <div
                          style={{
                            width: "100%",
                            height: 14,
                            borderRadius: 6,
                            border: `1px solid ${
                              frame >= CUE.bufferExplodes ? COLORS.danger : COLORS.border
                            }`,
                            overflow: "hidden",
                            position: "relative",
                          }}
                        >
                          <div
                            style={{
                              height: "100%",
                              width: `${interpolate(
                                frame,
                                [CUE.bufferOverflowStart, CUE.bufferExplodes],
                                [10, 100],
                                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                              )}%`,
                              background:
                                frame >= CUE.bufferExplodes
                                  ? `linear-gradient(90deg, ${COLORS.buffer}, ${COLORS.danger})`
                                  : `linear-gradient(90deg, ${COLORS.buffer}88, ${COLORS.buffer})`,
                              boxShadow:
                                frame >= CUE.bufferExplodes
                                  ? `0 0 18px ${COLORS.dangerGlow}`
                                  : undefined,
                            }}
                          />
                        </div>
                        {frame >= CUE.bufferExplodes && (
                          <div
                            style={{
                              fontFamily: FONTS.mono,
                              fontSize: 13,
                              color: COLORS.danger,
                              marginTop: 8,
                              opacity: interpolate(
                                frame,
                                [CUE.bufferExplodes, CUE.bufferExplodes + 10],
                                [0, 1],
                                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                              ),
                              textShadow: `0 0 12px ${COLORS.dangerGlow}`,
                            }}
                          >
                            ⚠ OVERFLOW: tokens lost
                          </div>
                        )}
                      </div>
                    )}

                    {/* Summary-only: "fact dropped" warning when narrator hits the cue */}
                    {b.name === "summary" && frame >= CUE.summaryWarning && (
                      <div
                        style={{
                          marginTop: 16,
                          padding: "8px 12px",
                          borderRadius: 8,
                          background: "rgba(221,132,82,0.10)",
                          border: `1px solid ${COLORS.summary}44`,
                          fontFamily: FONTS.mono,
                          fontSize: 13,
                          color: COLORS.summary,
                          opacity: interpolate(
                            frame,
                            [CUE.summaryWarning, CUE.summaryWarning + 15],
                            [0, 1],
                            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                          ),
                        }}
                      >
                        ✂ "Flight date" dropped during compression
                      </div>
                    )}
                  </GlassCard>
                </div>
              );
            })}
          </div>
        </div>

        {/* Phase 3: Closing question (1922 → 2138f) */}
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
              [CUE.questionAppear, CUE.questionAppear + 20],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            background: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.65), rgba(0,0,0,0.85))`,
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 18,
              color: COLORS.textMuted,
              letterSpacing: 4,
              textTransform: "uppercase",
              marginBottom: 24,
            }}
          >
            The Test
          </div>
          <AnimatedText
            text="50 turns. 10 planted facts."
            startFrame={CUE.questionAppear + 30}
            fontSize={56}
            fontWeight={700}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={70}
          />
          <AnimatedText
            text="Who survives?"
            startFrame={CUE.whoSurvives}
            fontSize={72}
            fontWeight={800}
            color={COLORS.accent}
            glow
            textAlign="center"
            mode="wordByWord"
            durationFrames={30}
            style={{ marginTop: 30 }}
          />
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
