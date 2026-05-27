import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { COLORS, FONTS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { GlassCard } from "../components/GlassCard";
import { FadeTransition } from "../components/FadeTransition";

// Cue points synced to public/audio/scene07.wav (whisper word-level, 30fps).
const CUE = {
  elephant: 0,                  // 0.08s
  doesItMatter: 61,             // 2.56s
  questionEnd: 151,             // 5.54s
  atThisScale: 153,             // 5.60s
  noWord: 194,                  // 6.96s
  noEnd: 225,                   // ~8.0s buffer before stats
  qdrantLatency: 227,           // 8.07s Qdrant 7001ms
  pgvectorLatency: 324,         // 11.30s pgvector 7021ms
  recallRow: 443,               // 15.25s "82%"
  costRow: 490,                 // 16.82s "$418"
  cost416: 571,                 // 19.51s
  tokensRow: 591,               // 20.19s
  identical: 662,               // 22.57s
  statsEnd: 705,                // ~24s
  ifAlreadyPostgres: 710,       // 24.16s
  justAddPgv: 836,              // 28.34s
  zeroExtra: 899,               // 30.47s
  pgvecRecEnd: 1035,            // 35.00s
  ifScale: 1035,                // 35.00s "If you're building"
  millionsVectors: 1122,        // 37.91s
  qdrantPurpose: 1173,          // 39.61s
  edge: 1285,                   // 43.33s
  qdrantRecEnd: 1293,           // 43.63s
  butForPerSession: 1303,       // 43.92s
  pgvectorPragmatic: 1389,      // 46.79s
  end: 1449,                    // 49.03s
};

// Comparison rows aligned with narration cues
const COMPARISON = [
  { metric: "Avg Latency", qdrant: "7,001 ms", pgvector: "7,021 ms", reveal: 242 },
  { metric: "Recall @ 50", qdrant: "82%", pgvector: "82%", reveal: 458 },
  { metric: "Cost / 1K", qdrant: "$418", pgvector: "$416", reveal: 505 },
  { metric: "Tokens / Run", qdrant: "69,595", pgvector: "69,366", reveal: 606 },
];

export const Scene7_QdrantVsPgvector: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene07.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* Phase 1: "Elephant in the room" question + dramatic "NO" (0 → 240f) */}
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
              [0, 10, CUE.noEnd - 10, CUE.noEnd + 8],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          {/* Big elephant with subtle glow */}
          <div
            style={{
              fontSize: 160,
              marginBottom: 4,
              filter: `drop-shadow(0 0 36px rgba(196,78,82,0.35))`,
            }}
          >
            🐘
          </div>

          {/* Eyebrow tag */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              marginBottom: 30,
              opacity: interpolate(
                frame,
                [CUE.elephant + 5, CUE.elephant + 25],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <div
              style={{
                width: 40,
                height: 2,
                background: COLORS.textMuted,
                opacity: 0.5,
              }}
            />
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 22,
                fontWeight: 700,
                color: COLORS.textMuted,
                letterSpacing: 8,
                textTransform: "uppercase",
              }}
            >
              The elephant in the room
            </div>
            <div
              style={{
                width: 40,
                height: 2,
                background: COLORS.textMuted,
                opacity: 0.5,
              }}
            />
          </div>

          {/* The question */}
          <AnimatedText
            text="Does it matter which vector database you choose?"
            startFrame={CUE.doesItMatter}
            fontSize={52}
            fontWeight={800}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={80}
            style={{ letterSpacing: -1, marginBottom: 40 }}
          />

          {/* The verdict: "No." with stamped emphasis */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              opacity: interpolate(
                frame,
                [CUE.noWord, CUE.noWord + 10],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              transform: `scale(${interpolate(
                frame,
                [CUE.noWord, CUE.noWord + 15],
                [0.7, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              )})`,
            }}
          >
            <div
              style={{
                fontFamily: FONTS.body,
                fontSize: 160,
                fontWeight: 900,
                color: COLORS.danger,
                textShadow: `0 0 80px ${COLORS.dangerGlow}, 0 0 30px ${COLORS.danger}55`,
                lineHeight: 1,
                letterSpacing: -4,
              }}
            >
              No.
            </div>
            {/* Stamped horizontal rule */}
            <div
              style={{
                width: 220,
                height: 4,
                background: COLORS.danger,
                marginTop: 10,
                borderRadius: 2,
                boxShadow: `0 0 18px ${COLORS.dangerGlow}`,
                opacity: interpolate(
                  frame,
                  [CUE.noWord + 12, CUE.noWord + 30],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
                transform: `scaleX(${interpolate(
                  frame,
                  [CUE.noWord + 12, CUE.noWord + 30],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )})`,
              }}
            />
          </div>

          {/* Subline filling the dead space */}
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 26,
              fontWeight: 500,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 36,
              maxWidth: 1200,
              opacity: interpolate(
                frame,
                [CUE.noWord + 30, CUE.noWord + 55],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            At this benchmark scale, qdrant <span style={{ color: COLORS.text, fontWeight: 700 }}>≈</span> pgvector on every metric.
          </div>
        </div>

        {/* Phase 2: Side-by-side comparison (240 → 720f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.noEnd, CUE.noEnd + 15, CUE.statsEnd - 10, CUE.statsEnd + 8],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            padding: "50px 80px",
          }}
        >
          <AnimatedText
            text="At this scale, identical."
            startFrame={CUE.noEnd + 5}
            fontSize={42}
            fontWeight={700}
            textAlign="center"
          />

          <div
            style={{
              display: "flex",
              gap: 40,
              marginTop: 160,
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            {/* Qdrant side */}
            <GlassCard
              startFrame={CUE.noEnd + 10}
              width={420}
              padding={32}
              glowColor={COLORS.qdrantGlow}
            >
              <div
                style={{
                  fontFamily: FONTS.mono,
                  fontSize: 32,
                  fontWeight: 700,
                  color: COLORS.qdrant,
                  textAlign: "center",
                  marginBottom: 24,
                }}
              >
                🔍 Qdrant
              </div>
              {COMPARISON.map((row, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "12px 0",
                    borderBottom: `1px solid ${COLORS.border}`,
                    opacity: interpolate(
                      frame,
                      [row.reveal, row.reveal + 15],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                >
                  <span style={{ fontFamily: FONTS.body, fontSize: 26, color: COLORS.textMuted }}>
                    {row.metric}
                  </span>
                  <span
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 30,
                      color: COLORS.text,
                      fontWeight: 700,
                    }}
                  >
                    {row.qdrant}
                  </span>
                </div>
              ))}
            </GlassCard>

            {/* VS */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                opacity: interpolate(frame, [CUE.noEnd + 20, CUE.noEnd + 40], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              <div
                style={{
                  fontFamily: FONTS.body,
                  fontSize: 48,
                  fontWeight: 800,
                  color: COLORS.textDim,
                  textShadow: `0 0 30px ${COLORS.accentGlow}`,
                }}
              >
                ≈
              </div>
            </div>

            {/* pgvector side */}
            <GlassCard
              startFrame={CUE.noEnd + 25}
              width={420}
              padding={32}
              glowColor={COLORS.pgvectorGlow}
            >
              <div
                style={{
                  fontFamily: FONTS.mono,
                  fontSize: 32,
                  fontWeight: 700,
                  color: COLORS.pgvector,
                  textAlign: "center",
                  marginBottom: 24,
                }}
              >
                🐘 pgvector
              </div>
              {COMPARISON.map((row, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "12px 0",
                    borderBottom: `1px solid ${COLORS.border}`,
                    opacity: interpolate(
                      frame,
                      [row.reveal, row.reveal + 15],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                >
                  <span style={{ fontFamily: FONTS.body, fontSize: 26, color: COLORS.textMuted }}>
                    {row.metric}
                  </span>
                  <span
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 30,
                      color: COLORS.text,
                      fontWeight: 700,
                    }}
                  >
                    {row.pgvector}
                  </span>
                </div>
              ))}
            </GlassCard>
          </div>

          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 80,
              textAlign: "center",
              opacity: interpolate(
                frame,
                [CUE.identical, CUE.identical + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 22,
                color: COLORS.neonGreen,
                letterSpacing: 2,
                textTransform: "uppercase",
                textShadow: `0 0 16px rgba(0,255,136,0.4)`,
              }}
            >
              ✓ Nearly identical
            </div>
          </div>
        </div>

        {/* Phase 3: pgvector recommendation (725 → 1050f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.ifAlreadyPostgres, CUE.ifAlreadyPostgres + 15, CUE.pgvecRecEnd - 10, CUE.pgvecRecEnd + 5],
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
          <div
            style={{
              fontSize: 140,
              marginBottom: 8,
              filter: `drop-shadow(0 0 40px ${COLORS.pgvectorGlow})`,
            }}
          >
            🐘
          </div>
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 22,
              fontWeight: 700,
              color: COLORS.pgvector,
              letterSpacing: 8,
              textTransform: "uppercase",
              marginBottom: 28,
            }}
          >
            Pick pgvector if
          </div>
          <AnimatedText
            text="You already run PostgreSQL."
            startFrame={CUE.ifAlreadyPostgres + 8}
            fontSize={68}
            fontWeight={800}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={70}
            style={{ letterSpacing: -1 }}
          />

          {/* Polished feature cards */}
          <div style={{ display: "flex", gap: 32, marginTop: 64 }}>
            {[
              { label: "Zero extra infrastructure", reveal: CUE.zeroExtra },
              { label: "Zero operational burden", reveal: CUE.zeroExtra + 80 },
            ].map((p) => (
              <div
                key={p.label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 18,
                  background:
                    "linear-gradient(135deg, rgba(0,255,136,0.10), rgba(0,255,136,0.04))",
                  border: `1px solid rgba(0,255,136,0.35)`,
                  borderRadius: 16,
                  padding: "20px 32px",
                  boxShadow: `0 0 28px rgba(0,255,136,0.12)`,
                  opacity: interpolate(
                    frame,
                    [p.reveal, p.reveal + 15],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  ),
                  transform: `translateY(${interpolate(
                    frame,
                    [p.reveal, p.reveal + 15],
                    [16, 0],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  )}px)`,
                }}
              >
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: "50%",
                    background: COLORS.neonGreen,
                    color: "#0a0a0f",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: FONTS.body,
                    fontSize: 22,
                    fontWeight: 800,
                    boxShadow: `0 0 18px ${COLORS.neonGreen}66`,
                    flexShrink: 0,
                  }}
                >
                  ✓
                </div>
                <div
                  style={{
                    fontFamily: FONTS.body,
                    fontSize: 24,
                    fontWeight: 600,
                    color: COLORS.text,
                  }}
                >
                  {p.label}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Phase 4: Qdrant recommendation (1050 → 1308f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.ifScale, CUE.ifScale + 15, CUE.qdrantRecEnd - 10, CUE.qdrantRecEnd + 5],
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
          <div
            style={{
              fontSize: 140,
              marginBottom: 8,
              filter: `drop-shadow(0 0 40px ${COLORS.qdrantGlow})`,
            }}
          >
            🔍
          </div>
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 22,
              fontWeight: 700,
              color: COLORS.qdrant,
              letterSpacing: 8,
              textTransform: "uppercase",
              marginBottom: 28,
            }}
          >
            Pick Qdrant if
          </div>
          <AnimatedText
            text="You scale to millions of vectors."
            startFrame={CUE.ifScale + 8}
            fontSize={68}
            fontWeight={800}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={80}
            style={{ letterSpacing: -1 }}
          />

          {/* Polished feature card */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 18,
              background: `linear-gradient(135deg, ${COLORS.qdrant}22, ${COLORS.qdrant}0c)`,
              border: `1px solid ${COLORS.qdrant}55`,
              borderRadius: 16,
              padding: "20px 32px",
              marginTop: 56,
              boxShadow: `0 0 28px ${COLORS.qdrantGlow}`,
              opacity: interpolate(
                frame,
                [CUE.qdrantPurpose, CUE.qdrantPurpose + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              transform: `translateY(${interpolate(
                frame,
                [CUE.qdrantPurpose, CUE.qdrantPurpose + 20],
                [16, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              )}px)`,
            }}
          >
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: "50%",
                background: COLORS.qdrant,
                color: "#0a0a0f",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: FONTS.body,
                fontSize: 22,
                fontWeight: 800,
                boxShadow: `0 0 18px ${COLORS.qdrant}88`,
                flexShrink: 0,
              }}
            >
              ⚡
            </div>
            <div
              style={{
                fontFamily: FONTS.body,
                fontSize: 24,
                fontWeight: 600,
                color: COLORS.text,
              }}
            >
              Purpose-built for vector search at scale
            </div>
          </div>
        </div>

        {/* Phase 5: Final verdict (1318 → 1472f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.butForPerSession, CUE.butForPerSession + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.6), rgba(0,0,0,0.85))`,
          }}
        >
          {/* Verdict stamp emblem */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              marginBottom: 32,
            }}
          >
            <div
              style={{
                width: 4,
                height: 28,
                background: COLORS.pgvector,
                borderRadius: 2,
                boxShadow: `0 0 14px ${COLORS.pgvectorGlow}`,
              }}
            />
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 22,
                fontWeight: 700,
                color: COLORS.pgvector,
                letterSpacing: 8,
                textTransform: "uppercase",
              }}
            >
              For per-session memory
            </div>
            <div
              style={{
                width: 4,
                height: 28,
                background: COLORS.pgvector,
                borderRadius: 2,
                boxShadow: `0 0 14px ${COLORS.pgvectorGlow}`,
              }}
            />
          </div>

          {/* Verdict headline */}
          <AnimatedText
            text="pgvector is the pragmatic choice."
            startFrame={CUE.pgvectorPragmatic}
            fontSize={76}
            fontWeight={800}
            color={COLORS.pgvector}
            glow
            glowColor={COLORS.pgvectorGlow}
            textAlign="center"
            mode="wordByWord"
            durationFrames={60}
            style={{ letterSpacing: -1.5 }}
          />

        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
