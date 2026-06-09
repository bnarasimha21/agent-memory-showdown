import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { COLORS, FONTS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { FadeTransition } from "../components/FadeTransition";

// Cue points synced to public/audio/scene09.wav (whisper word-level, 30fps).
const CUE = {
  intro: 0,                    // 0.00s "So"
  whatShouldUse: 7,           // 0.49s
  introEnd: 74,                // 2.73s
  productionChatbots: 75,      // 2.78s "For production"
  bufferShort: 400,            // 13.60s "For short conversations"
  alreadyPostgres: 700,        // 23.60s "If you already done PostgreSQL"
  millionsVectors: 928,        // 31.19s
  summarySkip: 1048,           // 35.20s "And summary memory"
  destroysDetails: 1231,       // 41.29s
  fortyTwoPctRecall: 1348,     // 45.20s
  forgottenMore: 1419,         // 47.57s
  end: 1498,                   // 50.47s
};

const RECS = [
  {
    useCase: "Production chatbot (cost-sensitive)",
    backend: "pgvector / qdrant",
    color: COLORS.qdrant,
    icon: "💰",
    detail: "82% recall at 1/10th the cost",
    reveal: CUE.productionChatbots,
  },
  {
    useCase: "Short conversations (< 15 turns)",
    backend: "buffer",
    color: COLORS.buffer,
    icon: "⚡",
    detail: "Simple, perfect recall, low cost at small scale",
    reveal: CUE.bufferShort,
  },
  {
    useCase: "Already running PostgreSQL",
    backend: "pgvector",
    color: COLORS.pgvector,
    icon: "🐘",
    detail: "Zero extra infrastructure. Just add the extension.",
    reveal: CUE.alreadyPostgres,
  },
  {
    useCase: "Millions of vectors at scale",
    backend: "qdrant",
    color: COLORS.qdrant,
    icon: "🔍",
    detail: "Purpose-built vector search engine",
    reveal: CUE.millionsVectors,
  },
  {
    useCase: "NOT recommended",
    backend: "summary",
    color: COLORS.danger,
    icon: "⛔",
    detail: "42% recall, slowest, destroys details",
    reveal: CUE.summarySkip,
  },
];

export const Scene9_Recommendations: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene09.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 40%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        <AnimatedText
          text="What should you actually use?"
          startFrame={CUE.intro}
          fontSize={48}
          fontWeight={700}
          textAlign="center"
          mode="wordByWord"
          durationFrames={60}
        />

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 20,
            maxWidth: 1300,
            margin: "60px auto 0",
          }}
        >
          {RECS.map((rec, i) => {
            const cardStart = rec.reveal;
            const isLast = i === RECS.length - 1;

            const cardOpacity = interpolate(
              frame,
              [cardStart, cardStart + 20],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const slideX = interpolate(
              frame,
              [cardStart, cardStart + 20],
              [-40, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );

            // Highlight the card while its narration is playing
            const nextReveal = i < RECS.length - 1 ? RECS[i + 1].reveal : CUE.end;
            const isActive = frame >= cardStart && frame < nextReveal;

            return (
              <div
                key={i}
                style={{
                  opacity: cardOpacity,
                  transform: `translateX(${slideX}px) scale(${isActive ? 1.015 : 1})`,
                  transition: "transform 0.3s",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 24,
                    padding: "22px 32px",
                    background: isLast ? "rgba(255,68,68,0.06)" : COLORS.bgCard,
                    border: `1px solid ${
                      isLast
                        ? COLORS.danger + "44"
                        : isActive
                        ? `${rec.color}88`
                        : COLORS.border
                    }`,
                    borderRadius: 14,
                    backdropFilter: "blur(10px)",
                    boxShadow: isActive ? `0 0 30px ${rec.color}33` : undefined,
                  }}
                >
                  <div style={{ fontSize: 40, flexShrink: 0 }}>{rec.icon}</div>

                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontFamily: FONTS.body,
                        fontSize: 28,
                        color: COLORS.text,
                        fontWeight: 700,
                        marginBottom: 8,
                      }}
                    >
                      {rec.useCase}
                    </div>
                    <div
                      style={{
                        fontFamily: FONTS.body,
                        fontSize: 24,
                        color: COLORS.textMuted,
                      }}
                    >
                      {rec.detail}
                    </div>
                  </div>

                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 22,
                      fontWeight: 700,
                      color: rec.color,
                      padding: "8px 20px",
                      background: `${rec.color}15`,
                      border: `1px solid ${rec.color}44`,
                      borderRadius: 10,
                      textDecoration: isLast ? "line-through" : undefined,
                      textShadow: isLast ? undefined : `0 0 12px ${rec.color}55`,
                    }}
                  >
                    {rec.backend}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Closing tagline that appears with the summary card */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 50,
            textAlign: "center",
            opacity: interpolate(
              frame,
              [CUE.forgottenMore, CUE.forgottenMore + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 30,
              fontWeight: 700,
              color: COLORS.danger,
              textShadow: `0 0 18px ${COLORS.dangerGlow}`,
            }}
          >
            Summary forgets more than it remembers.
          </div>
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
