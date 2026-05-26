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
  elephant: 2,                  // 0.08s
  doesItMatter: 76,             // 2.56s
  questionEnd: 166,             // 5.54s
  atThisScale: 168,             // 5.60s
  noWord: 209,                  // 6.96s
  noEnd: 240,                   // ~8.0s buffer before stats
  qdrantLatency: 242,           // 8.07s Qdrant 7001ms
  pgvectorLatency: 339,         // 11.30s pgvector 7021ms
  recallRow: 458,               // 15.25s "82%"
  costRow: 505,                 // 16.82s "$418"
  cost416: 586,                 // 19.51s
  tokensRow: 606,               // 20.19s
  identical: 677,               // 22.57s
  statsEnd: 720,                // ~24s
  ifAlreadyPostgres: 725,       // 24.16s
  justAddPgv: 851,              // 28.34s
  zeroExtra: 914,               // 30.47s
  pgvecRecEnd: 1050,            // 35.00s
  ifScale: 1050,                // 35.00s "If you're building"
  millionsVectors: 1137,        // 37.91s
  qdrantPurpose: 1188,          // 39.61s
  edge: 1300,                   // 43.33s
  qdrantRecEnd: 1308,           // 43.63s
  butForPerSession: 1318,       // 43.92s
  pgvectorPragmatic: 1404,      // 46.79s
  end: 1472,                    // 49.03s
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
          <div style={{ fontSize: 100, marginBottom: 20 }}>🐘</div>
          <AnimatedText
            text="The elephant in the room:"
            startFrame={CUE.elephant + 5}
            fontSize={36}
            color={COLORS.textMuted}
            textAlign="center"
            mode="wordByWord"
            durationFrames={60}
          />
          <AnimatedText
            text="Does it matter which vector database you choose?"
            startFrame={CUE.doesItMatter}
            fontSize={42}
            fontWeight={700}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={80}
            style={{ marginTop: 18 }}
          />
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 120,
              fontWeight: 800,
              color: COLORS.danger,
              marginTop: 40,
              textShadow: `0 0 80px ${COLORS.dangerGlow}`,
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
            No.
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
              marginTop: 50,
              justifyContent: "center",
              alignItems: "flex-start",
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
                  <span style={{ fontFamily: FONTS.body, fontSize: 16, color: COLORS.textMuted }}>
                    {row.metric}
                  </span>
                  <span
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 18,
                      color: COLORS.text,
                      fontWeight: 600,
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
                height: 400,
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
                  <span style={{ fontFamily: FONTS.body, fontSize: 16, color: COLORS.textMuted }}>
                    {row.metric}
                  </span>
                  <span
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 18,
                      color: COLORS.text,
                      fontWeight: 600,
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
          <div style={{ fontSize: 80, marginBottom: 16 }}>🐘</div>
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 18,
              color: COLORS.pgvector,
              letterSpacing: 4,
              textTransform: "uppercase",
              marginBottom: 18,
            }}
          >
            Pick pgvector if...
          </div>
          <AnimatedText
            text="You already run PostgreSQL."
            startFrame={CUE.ifAlreadyPostgres + 8}
            fontSize={48}
            fontWeight={700}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={70}
          />
          <div style={{ display: "flex", gap: 24, marginTop: 40 }}>
            {[
              { label: "Zero extra infrastructure", reveal: CUE.zeroExtra },
              { label: "Zero operational burden", reveal: CUE.zeroExtra + 80 },
            ].map((p) => (
              <div
                key={p.label}
                style={{
                  fontFamily: FONTS.mono,
                  fontSize: 18,
                  color: COLORS.neonGreen,
                  background: "rgba(0,255,136,0.08)",
                  border: `1px solid rgba(0,255,136,0.3)`,
                  borderRadius: 10,
                  padding: "10px 20px",
                  opacity: interpolate(
                    frame,
                    [p.reveal, p.reveal + 15],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  ),
                  transform: `translateY(${interpolate(
                    frame,
                    [p.reveal, p.reveal + 15],
                    [10, 0],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  )}px)`,
                }}
              >
                ✓ {p.label}
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
          <div style={{ fontSize: 80, marginBottom: 16 }}>🔍</div>
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 18,
              color: COLORS.qdrant,
              letterSpacing: 4,
              textTransform: "uppercase",
              marginBottom: 18,
            }}
          >
            Pick Qdrant if...
          </div>
          <AnimatedText
            text="You scale to millions of vectors."
            startFrame={CUE.ifScale + 8}
            fontSize={48}
            fontWeight={700}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={80}
          />
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 22,
              color: COLORS.textMuted,
              textAlign: "center",
              marginTop: 30,
              maxWidth: 900,
              opacity: interpolate(
                frame,
                [CUE.qdrantPurpose, CUE.qdrantPurpose + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            Purpose-built architecture pays off across many users.
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
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 18,
              color: COLORS.textMuted,
              letterSpacing: 4,
              textTransform: "uppercase",
              marginBottom: 16,
            }}
          >
            For per-session memory
          </div>
          <AnimatedText
            text="pgvector is the pragmatic choice."
            startFrame={CUE.pgvectorPragmatic}
            fontSize={56}
            fontWeight={800}
            color={COLORS.pgvector}
            glow
            glowColor={COLORS.pgvectorGlow}
            textAlign="center"
            mode="wordByWord"
            durationFrames={60}
          />
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
