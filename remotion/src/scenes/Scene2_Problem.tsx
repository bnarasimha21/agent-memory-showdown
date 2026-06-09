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

// Cue points synced to public/audio/scene02.wav (whisper word-level, 30fps).
// Audio trimmed 0.6s at start, end at 71.10s (shift -18 frames from original).
const CUE = {
  introStart: 0,
  introEnd: 60,
  fourWaysStart: 70,
  recallWord: 260,    // ~9.28s — "recall"
  speedWord: 287,     // ~10.17s — "speed"
  costWord: 297,      // ~10.51s — "cost"
  weDiscuss: 312,     // ~11.00s — "We will"
  fourOfThese: 342,   // ~12.00s — "four methods"
  setupEnd: 383,

  // Buffer
  bufferReveal: 383,           // ~13.36s — "Buffer"
  bufferJustPass: 462,         // ~16.00s — "Just pass"
  bufferEntire: 484,           // ~16.72s — "entire"
  bufferIntoPrompt: 534,       // ~18.40s — "into the prompt"
  bufferWorksGreat: 563,       // ~19.36s — "Works great"
  bufferContextWindow: 604,    // ~20.73s — "context window"
  bufferExplodes: 633,         // ~21.71s — "explodes"
  bufferAPIBill: 663,          // ~22.69s — "API bill"
  bufferRoof: 709,             // ~24.24s — "roof"
  bufferEnd: 731,

  // Summary
  summaryReveal: 731,          // ~24.96s — "Summary memory"
  summaryWord: 757,            // ~25.84s — "an LLM"
  summaryCompresses: 777,      // ~26.51s — "compresses"
  summarySoundsClever: 907,    // ~30.84s — "Sounds clever"
  summaryWhatHappens: 946,     // ~32.15s — "what happens"
  summaryFlightDate: 1018,     // ~34.53s — "flight date"
  summaryIsntWorth: 1048,      // ~35.53s — "worth keeping"
  summaryEnd: 1088,

  // Qdrant
  qdrantReveal: 1088,          // ~36.88s — "Vector memory"
  qdrantVectorMem: 1121,       // ~37.98s — "with qdrant"
  qdrantEmbed: 1159,           // ~39.22s — "embed every"
  qdrantQueryTime: 1247,       // ~42.16s — "query time"
  qdrantPullBack: 1268,        // ~42.86s — "pull back"
  qdrantSnippets: 1353,        // ~45.71s — "snippets"
  qdrantSurgical: 1378,        // ~46.52s — "surgical"
  qdrantEnd: 1444,

  // pgvector
  pgvecReveal: 1444,           // ~48.72s — "Vector memory"
  pgvecWord: 1491,             // ~50.30s — "PG vector"
  pgvecSameIdea: 1520,         // ~51.28s — "same idea"
  pgvecPostgres: 1557,         // ~52.51s — "PostgreSQL"
  pgvecExtension: 1618,        // ~54.52s — "extension"
  pgvecInsteadOf: 1634,        // ~55.07s — "Instead of"
  pgvecOneLess: 1716,          // ~57.80s — "One less"
  pgvecToManage: 1748,         // ~58.86s — "to manage"
  pgvecEnd: 1774,

  // Closing
  questionAppear: 1774,        // ~59.72s — "The question"
  whoSurvives: 1928,           // ~64.86s — "whose arrives"
  end: 1962,                   // 66.13s × 30fps audio length
};

const BACKENDS_META = [
  { name: "buffer",   icon: "📋", reveal: CUE.bufferReveal },
  { name: "summary",  icon: "📝", reveal: CUE.summaryReveal },
  { name: "qdrant",   icon: "🔍", reveal: CUE.qdrantReveal },
  { name: "pgvector", icon: "🐘", reveal: CUE.pgvecReveal },
] as const;

// Shared helpers
const fadeWindow = (frame: number, start: number, end: number, holdFor = 0) => {
  return interpolate(
    frame,
    [start - 8, start + 12, end - 12 - holdFor, end + 4],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
};

export const Scene2_Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene02.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, #0d1420 0%, ${COLORS.bg} 70%)`,
          padding: 60,
        }}
      >
        {/* ─── Phase 1: LangChain intro (0 → 100f) ─────────────────── */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            opacity: fadeWindow(frame, 0, CUE.introEnd),
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 24,
              color: COLORS.textMuted,
              letterSpacing: 5,
              textTransform: "uppercase",
              marginBottom: 32,
            }}
          >
            For this experiment
          </div>
          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 140,
              fontWeight: 800,
              color: COLORS.text,
              letterSpacing: -4,
              textShadow: `0 0 60px ${COLORS.accentGlow}`,
              opacity: interpolate(frame, [45, 60], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              transform: `scale(${interpolate(frame, [45, 70], [0.85, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })})`,
            }}
          >
            🦜 LangChain
          </div>
        </div>

        {/* ─── Phase 2: Four strategies teaser (110 → 433f) ─────────── */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            opacity: fadeWindow(frame, CUE.fourWaysStart, CUE.setupEnd),
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 22,
              color: COLORS.textMuted,
              letterSpacing: 6,
              textTransform: "uppercase",
              marginBottom: 28,
            }}
          >
            Four memory strategies
          </div>

          {/* Trade-off criteria chips — pop in as narrator says each word */}
          <div style={{ display: "flex", gap: 30, marginBottom: 40 }}>
            {[
              { label: "Recall",   icon: "🧠", reveal: CUE.recallWord, color: "#7eb6ff" },
              { label: "Speed",    icon: "⚡", reveal: CUE.speedWord,  color: "#ffd166" },
              { label: "Cost",     icon: "💰", reveal: CUE.costWord,   color: "#9affd0" },
            ].map((c) => {
              const popScale = spring({
                frame: Math.max(0, frame - c.reveal),
                fps,
                config: { damping: 9, stiffness: 150 },
              });
              const opacity = interpolate(
                frame,
                [c.reveal, c.reveal + 12],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );
              return (
                <div
                  key={c.label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 14,
                    padding: "14px 28px",
                    background: `${c.color}1a`,
                    border: `1px solid ${c.color}66`,
                    borderRadius: 999,
                    boxShadow: `0 0 24px ${c.color}33`,
                    opacity,
                    transform: `scale(${0.6 + 0.4 * popScale})`,
                  }}
                >
                  <span style={{ fontSize: 32 }}>{c.icon}</span>
                  <span
                    style={{
                      fontFamily: FONTS.body,
                      fontSize: 26,
                      fontWeight: 700,
                      color: c.color,
                      letterSpacing: 0.5,
                    }}
                  >
                    {c.label}
                  </span>
                </div>
              );
            })}
          </div>

          <div style={{ display: "flex", gap: 50 }}>
            {BACKENDS_META.map((b, i) => {
              const lightUp = CUE.fourWaysStart + 90 + i * 50;
              const isLit = frame >= lightUp;
              const scale = spring({
                frame: Math.max(0, frame - lightUp),
                fps,
                config: { damping: 12, stiffness: 110 },
              });
              return (
                <div
                  key={b.name}
                  style={{
                    width: 200,
                    height: 200,
                    borderRadius: 24,
                    background: COLORS.bgCard,
                    border: `2px solid ${isLit ? BACKEND_COLORS[b.name] : COLORS.border}`,
                    boxShadow: isLit ? `0 0 32px ${BACKEND_COLORS[b.name]}55` : "none",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    transform: `scale(${0.85 + 0.15 * scale})`,
                    opacity: interpolate(frame, [lightUp, lightUp + 12], [0.3, 1], {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                    }),
                    transition: "border 0.3s",
                  }}
                >
                  <div style={{ fontSize: 72 }}>{b.icon}</div>
                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 22,
                      fontWeight: 700,
                      color: BACKEND_COLORS[b.name],
                      marginTop: 12,
                    }}
                  >
                    {b.name}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ─── Phase 3: BUFFER demo (433 → 773f) ────────────────────── */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: fadeWindow(frame, CUE.bufferReveal, CUE.bufferEnd),
          }}
        >
          <BufferDemo frame={frame} fps={fps} />
        </div>

        {/* ─── Phase 4: SUMMARY demo (773 → 1165f) ──────────────────── */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: fadeWindow(frame, CUE.summaryReveal, CUE.summaryEnd),
          }}
        >
          <SummaryDemo frame={frame} fps={fps} />
        </div>

        {/* ─── Phase 5: QDRANT demo (1165 → 1551f) ──────────────────── */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: fadeWindow(frame, CUE.qdrantReveal, CUE.qdrantEnd),
          }}
        >
          <QdrantDemo frame={frame} fps={fps} />
        </div>

        {/* ─── Phase 6: PGVECTOR demo (1551 → 1922f) ────────────────── */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: fadeWindow(frame, CUE.pgvecReveal, CUE.pgvecEnd),
          }}
        >
          <PgvectorDemo frame={frame} fps={fps} />
        </div>

        {/* ─── Phase 7: Closing question (1922 → 2138f) ─────────────── */}
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
              fontSize: 22,
              color: COLORS.textMuted,
              letterSpacing: 5,
              textTransform: "uppercase",
              marginBottom: 28,
            }}
          >
            The Test
          </div>
          <AnimatedText
            text="50 turns. 10 planted facts."
            startFrame={CUE.questionAppear + 30}
            fontSize={64}
            fontWeight={700}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={70}
          />
          <AnimatedText
            text="Who survives?"
            startFrame={CUE.whoSurvives}
            fontSize={84}
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

// ═══════════════════════════════════════════════════════════════════════
// BUFFER DEMO: messages stream into a prompt that grows past its limit
// ═══════════════════════════════════════════════════════════════════════
const BufferDemo: React.FC<{ frame: number; fps: number }> = ({ frame, fps }) => {
  const MESSAGES = [
    "msg 1: My dog is Baxter.",
    "msg 2: Allergic to shellfish.",
    "msg 3: Flight on March 15.",
    "msg 4: Deadline April 30.",
    "msg 5: Wedding in Lake Como.",
    "msg 6: Reading G.E.B.",
    "msg 7: Wi-Fi: sunkist-42.",
    "msg 8: Take 10mg melatonin.",
  ];

  const explodes = frame >= CUE.bufferExplodes;
  const fillPct = interpolate(
    frame,
    [CUE.bufferJustPass, CUE.bufferContextWindow, CUE.bufferExplodes, CUE.bufferRoof],
    [0, 60, 100, 130],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Cost counter
  const costValue = Math.floor(
    interpolate(
      frame,
      [CUE.bufferAPIBill, CUE.bufferRoof + 20],
      [0, 4303],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    )
  );

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", padding: 60 }}>
      <BackendChyron name="buffer" icon="📋" tagline="pass entire history → prompt" />

      {/* LEFT: chat history */}
      <div style={{ position: "absolute", top: 260, left: 80, width: 540 }}>
        <PanelHeading>chat history</PanelHeading>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16 }}>
          {MESSAGES.slice(0, 6).map((msg, i) => {
            const msgFrame = CUE.bufferJustPass + i * 12;
            return (
              <ChatChip
                key={i}
                text={msg}
                startFrame={msgFrame}
                frame={frame}
                color={COLORS.text}
              />
            );
          })}
        </div>
      </div>

      {/* ARROW */}
      <div
        style={{
          position: "absolute",
          top: 580,
          left: 640,
          fontFamily: FONTS.mono,
          fontSize: 36,
          color: COLORS.accent,
          opacity: interpolate(frame, [CUE.bufferJustPass + 30, CUE.bufferJustPass + 60], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        →
      </div>

      {/* RIGHT: prompt container with context-window bar */}
      <div style={{ position: "absolute", top: 260, left: 720, width: 1080 }}>
        <PanelHeading>LLM prompt</PanelHeading>

        {/* Context-window fill bar */}
        <div
          style={{
            marginTop: 16,
            background: COLORS.bgCard,
            border: `2px solid ${explodes ? COLORS.danger : COLORS.border}`,
            borderRadius: 10,
            height: 28,
            position: "relative",
            overflow: "hidden",
            boxShadow: explodes ? `0 0 30px ${COLORS.dangerGlow}` : "none",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${Math.min(fillPct, 100)}%`,
              background: explodes
                ? `linear-gradient(90deg, ${COLORS.buffer}, ${COLORS.danger})`
                : `linear-gradient(90deg, ${COLORS.buffer}aa, ${COLORS.buffer})`,
              transition: "background 0.3s",
            }}
          />
          <div
            style={{
              position: "absolute",
              top: 0,
              right: 12,
              bottom: 0,
              display: "flex",
              alignItems: "center",
              fontFamily: FONTS.mono,
              fontSize: 18,
              fontWeight: 600,
              color: COLORS.text,
            }}
          >
            context window
          </div>
        </div>

        {/* Stacked messages inside the prompt */}
        <div
          style={{
            marginTop: 16,
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 12,
            padding: 18,
            minHeight: 460,
            position: "relative",
            overflow: explodes ? "visible" : "hidden",
          }}
        >
          {MESSAGES.map((msg, i) => {
            const msgFrame = CUE.bufferJustPass + 10 + i * 12;
            const yShift = i >= 6 && explodes ? (i - 5) * 14 : 0;
            return (
              <ChatChip
                key={i}
                text={msg}
                startFrame={msgFrame}
                frame={frame}
                color={COLORS.textMuted}
                small
                style={{
                  marginBottom: 8,
                  transform: `translateY(${yShift}px)`,
                }}
              />
            );
          })}
        </div>

        {/* OVERFLOW callout */}
        {explodes && (
          <div
            style={{
              position: "absolute",
              top: 80,
              right: 0,
              fontFamily: FONTS.mono,
              fontSize: 22,
              fontWeight: 700,
              color: COLORS.danger,
              textShadow: `0 0 20px ${COLORS.dangerGlow}`,
              opacity: interpolate(
                frame,
                [CUE.bufferExplodes, CUE.bufferExplodes + 12],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            ⚠ OVERFLOW
          </div>
        )}

        {/* Cost counter */}
        <div
          style={{
            position: "absolute",
            bottom: -80,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            gap: 16,
            alignItems: "center",
            opacity: interpolate(
              frame,
              [CUE.bufferAPIBill, CUE.bufferAPIBill + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <span style={{ fontFamily: FONTS.body, fontSize: 22, color: COLORS.textMuted }}>
            API bill / 1k convos
          </span>
          <span
            style={{
              fontFamily: FONTS.mono,
              fontSize: 44,
              fontWeight: 800,
              color: COLORS.danger,
              textShadow: `0 0 20px ${COLORS.dangerGlow}`,
            }}
          >
            ${costValue.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// SUMMARY DEMO: chat → LLM → summary, with one specific fact dropped
// ═══════════════════════════════════════════════════════════════════════
const SummaryDemo: React.FC<{ frame: number; fps: number }> = ({ frame, fps }) => {
  const MESSAGES = [
    "My dog is Baxter.",
    "Allergic to shellfish.",
    "Flight: March 15.",
    "Deadline April 30.",
    "Wedding in Lake Como.",
  ];

  const summaryAfter = frame > CUE.summaryFlightDate + 20;

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", padding: 60 }}>
      <BackendChyron name="summary" icon="📝" tagline="LLM compresses → running summary" />

      {/* Three columns: chat → LLM → summary */}
      <div
        style={{
          position: "absolute",
          top: 300,
          left: 80,
          right: 80,
          display: "grid",
          gridTemplateColumns: "1fr 220px 1fr",
          gap: 40,
          alignItems: "start",
        }}
      >
        {/* LEFT: chat */}
        <div>
          <PanelHeading>chat turns</PanelHeading>
          <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
            {MESSAGES.map((msg, i) => {
              const msgFrame = CUE.summaryWord + i * 18;
              return (
                <ChatChip
                  key={i}
                  text={msg}
                  startFrame={msgFrame}
                  frame={frame}
                  color={COLORS.text}
                />
              );
            })}
          </div>
        </div>

        {/* MIDDLE: LLM brain pumping */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            paddingTop: 60,
          }}
        >
          <div
            style={{
              fontSize: 100,
              transform: `scale(${1 + 0.08 * Math.sin(frame * 0.2)})`,
              filter: `drop-shadow(0 0 24px ${COLORS.summaryGlow})`,
            }}
          >
            🧠
          </div>
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 22,
              fontWeight: 700,
              color: COLORS.summary,
              marginTop: 16,
              letterSpacing: 4,
              textTransform: "uppercase",
            }}
          >
            compress
          </div>
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 36,
              color: COLORS.summary,
              marginTop: 10,
            }}
          >
            ↓
          </div>
        </div>

        {/* RIGHT: summary box */}
        <div>
          <PanelHeading>running summary</PanelHeading>
          <div
            style={{
              marginTop: 16,
              background: COLORS.bgCard,
              border: `2px solid ${COLORS.summary}66`,
              borderRadius: 12,
              padding: 24,
              minHeight: 360,
              fontFamily: FONTS.body,
              fontSize: 22,
              color: COLORS.text,
              lineHeight: 1.6,
              boxShadow: `0 0 24px ${COLORS.summaryGlow}33`,
            }}
          >
            {!summaryAfter ? (
              <>
                <span
                  style={{
                    opacity: interpolate(
                      frame,
                      [CUE.summaryCompresses + 30, CUE.summaryCompresses + 60],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                >
                  User has a dog named Baxter, is allergic to shellfish, has a{" "}
                </span>
                <span
                  style={{
                    background: "rgba(221,132,82,0.20)",
                    padding: "2px 6px",
                    borderRadius: 4,
                    opacity: interpolate(
                      frame,
                      [CUE.summaryCompresses + 60, CUE.summaryCompresses + 90],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                >
                  flight on March 15
                </span>
                <span
                  style={{
                    opacity: interpolate(
                      frame,
                      [CUE.summaryCompresses + 90, CUE.summaryCompresses + 120],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    ),
                  }}
                >
                  , and a deadline April 30. Wedding planned in Lake Como.
                </span>
              </>
            ) : (
              <>
                User has a dog named Baxter, is allergic to shellfish,{" "}
                <span
                  style={{
                    textDecoration: "line-through",
                    color: COLORS.danger,
                    background: "rgba(255,68,68,0.15)",
                    padding: "2px 6px",
                    borderRadius: 4,
                  }}
                >
                  flight on March 15
                </span>{" "}
                is planning travel, has a deadline April 30. Wedding planned.
              </>
            )}
          </div>

          {/* "Specific detail dropped" callout */}
          {summaryAfter && (
            <div
              style={{
                marginTop: 18,
                padding: "10px 16px",
                background: "rgba(255,68,68,0.10)",
                border: `1px solid ${COLORS.danger}66`,
                borderRadius: 10,
                fontFamily: FONTS.mono,
                fontSize: 18,
                color: COLORS.danger,
                textShadow: `0 0 12px ${COLORS.dangerGlow}`,
                opacity: interpolate(
                  frame,
                  [CUE.summaryFlightDate + 25, CUE.summaryFlightDate + 50],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
              }}
            >
              ✗ specific date lost during compression
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// QDRANT DEMO: messages embedded as 2D vector dots, nearest-K retrieved
// ═══════════════════════════════════════════════════════════════════════
const QdrantDemo: React.FC<{ frame: number; fps: number }> = ({ frame, fps }) => {
  // Pre-computed dot positions in a 2D "vector space" (relative %)
  const DOTS = [
    { x: 22, y: 30, label: "Baxter",     topic: "pets" },
    { x: 32, y: 35, label: "shellfish",  topic: "food" },
    { x: 65, y: 25, label: "Tokyo",      topic: "travel" },
    { x: 72, y: 30, label: "March 15",   topic: "travel" },
    { x: 50, y: 60, label: "deadline",   topic: "work" },
    { x: 38, y: 70, label: "G.E.B.",     topic: "books" },
    { x: 80, y: 65, label: "Lake Como",  topic: "travel" },
    { x: 28, y: 78, label: "melatonin",  topic: "health" },
  ];
  const TOPIC_COLOR: Record<string, string> = {
    pets:   "#7eb6ff",
    food:   "#ffb56b",
    travel: COLORS.qdrant,
    work:   "#c08cff",
    books:  "#ff8cb0",
    health: "#9affd0",
  };

  // Query dot (near "Tokyo" / "March 15")
  const QUERY = { x: 68, y: 28 };
  // Top-K = 3 nearest indices
  const TOP_K = [2, 3, 6]; // Tokyo, March 15, Lake Como

  const showQuery = frame >= CUE.qdrantQueryTime;
  const showRetrieval = frame >= CUE.qdrantPullBack;

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", padding: 60 }}>
      <BackendChyron name="qdrant" icon="🔍" tagline="embed → search → retrieve top-K" />

      {/* 2D vector space (center-left) */}
      <div
        style={{
          position: "absolute",
          top: 240,
          left: 80,
          width: 900,
          height: 700,
        }}
      >
        <PanelHeading>vector space</PanelHeading>
        <div
          style={{
            marginTop: 16,
            width: "100%",
            height: 640,
            background: "rgba(255,255,255,0.025)",
            border: `1px solid ${COLORS.border}`,
            borderRadius: 16,
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* faint grid */}
          <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.15 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <line key={`h${i}`} x1="0" y1={`${i * 12.5}%`} x2="100%" y2={`${i * 12.5}%`} stroke={COLORS.textDim} />
            ))}
            {Array.from({ length: 10 }).map((_, i) => (
              <line key={`v${i}`} x1={`${i * 10}%`} y1="0" x2={`${i * 10}%`} y2="100%" stroke={COLORS.textDim} />
            ))}
          </svg>

          {/* Embedded dots — appear one by one starting at "embed every message" */}
          {DOTS.map((dot, i) => {
            const dotStart = CUE.qdrantEmbed + i * 8;
            const opacity = interpolate(frame, [dotStart, dotStart + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const scale = spring({
              frame: Math.max(0, frame - dotStart),
              fps,
              config: { damping: 12, stiffness: 140 },
            });
            const isTopK = showRetrieval && TOP_K.includes(i);
            const c = TOPIC_COLOR[dot.topic];
            return (
              <div key={i}>
                <div
                  style={{
                    position: "absolute",
                    left: `${dot.x}%`,
                    top: `${dot.y}%`,
                    width: isTopK ? 28 : 20,
                    height: isTopK ? 28 : 20,
                    borderRadius: "50%",
                    background: c,
                    transform: `translate(-50%, -50%) scale(${scale})`,
                    opacity,
                    boxShadow: isTopK
                      ? `0 0 20px ${COLORS.neonGreen}, 0 0 4px ${COLORS.neonGreen}`
                      : `0 0 10px ${c}66`,
                    border: isTopK ? `2px solid ${COLORS.neonGreen}` : "none",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: `${dot.x}%`,
                    top: `calc(${dot.y}% + 24px)`,
                    transform: "translateX(-50%)",
                    fontFamily: FONTS.mono,
                    fontSize: 18,
                    color: isTopK ? COLORS.neonGreen : COLORS.text,
                    fontWeight: isTopK ? 800 : 600,
                    opacity,
                    whiteSpace: "nowrap",
                  }}
                >
                  {dot.label}
                </div>
              </div>
            );
          })}

          {/* Query dot + radius */}
          {showQuery && (
            <>
              {/* Search radius circle */}
              <div
                style={{
                  position: "absolute",
                  left: `${QUERY.x}%`,
                  top: `${QUERY.y}%`,
                  width: 240,
                  height: 240,
                  borderRadius: "50%",
                  border: `2px dashed ${COLORS.accent}`,
                  transform: "translate(-50%, -50%)",
                  opacity: interpolate(
                    frame,
                    [CUE.qdrantPullBack - 10, CUE.qdrantPullBack + 20],
                    [0, 0.7],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  ),
                  boxShadow: `inset 0 0 30px ${COLORS.accentGlow}`,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: `${QUERY.x}%`,
                  top: `${QUERY.y}%`,
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  background: COLORS.accent,
                  transform: `translate(-50%, -50%) scale(${spring({
                    frame: Math.max(0, frame - CUE.qdrantQueryTime),
                    fps,
                    config: { damping: 10, stiffness: 140 },
                  })})`,
                  boxShadow: `0 0 24px ${COLORS.accentGlow}, 0 0 4px ${COLORS.accent}`,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: `${QUERY.x}%`,
                  top: `calc(${QUERY.y}% - 42px)`,
                  transform: "translateX(-50%)",
                  fontFamily: FONTS.mono,
                  fontSize: 22,
                  fontWeight: 800,
                  color: COLORS.accent,
                  whiteSpace: "nowrap",
                  textShadow: `0 0 14px ${COLORS.accentGlow}`,
                }}
              >
                ▶ query
              </div>
            </>
          )}
        </div>
      </div>

      {/* RIGHT: retrieved snippets */}
      <div
        style={{
          position: "absolute",
          top: 240,
          right: 80,
          width: 480,
          opacity: interpolate(
            frame,
            [CUE.qdrantSnippets, CUE.qdrantSnippets + 20],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          ),
        }}
      >
        <PanelHeading>retrieved</PanelHeading>
        <div
          style={{
            marginTop: 16,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          {TOP_K.map((idx, i) => (
            <div
              key={idx}
              style={{
                padding: "16px 20px",
                background: "rgba(0,255,136,0.08)",
                border: `1px solid rgba(0,255,136,0.4)`,
                borderRadius: 10,
                fontFamily: FONTS.mono,
                fontSize: 20,
                color: "#fff",
                boxShadow: `0 0 16px rgba(0,255,136,0.2)`,
                opacity: interpolate(
                  frame,
                  [CUE.qdrantSnippets + i * 15, CUE.qdrantSnippets + 15 + i * 15],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
                transform: `translateX(${interpolate(
                  frame,
                  [CUE.qdrantSnippets + i * 15, CUE.qdrantSnippets + 15 + i * 15],
                  [20, 0],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )}px)`,
              }}
            >
              ✓ {DOTS[idx].label}
            </div>
          ))}
        </div>
        <div
          style={{
            marginTop: 24,
            fontFamily: FONTS.mono,
            fontSize: 18,
            color: COLORS.qdrant,
            letterSpacing: 2,
            textTransform: "uppercase",
            opacity: interpolate(
              frame,
              [CUE.qdrantSurgical, CUE.qdrantSurgical + 15],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          → only the relevant
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// PGVECTOR DEMO: same vectors, but inside an existing PostgreSQL table.
// "One less service" — a separate Qdrant container fades out.
// ═══════════════════════════════════════════════════════════════════════
const PgvectorDemo: React.FC<{ frame: number; fps: number }> = ({ frame, fps }) => {
  return (
    <div style={{ position: "relative", width: "100%", height: "100%", padding: 60 }}>
      <BackendChyron name="pgvector" icon="🐘" tagline="vectors live in PostgreSQL" />

      {/* "Same idea" callout */}
      <div
        style={{
          position: "absolute",
          top: 300,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: FONTS.mono,
          fontSize: 22,
          color: COLORS.textMuted,
          letterSpacing: 3,
          textTransform: "uppercase",
          opacity: interpolate(
            frame,
            [CUE.pgvecSameIdea, CUE.pgvecSameIdea + 20, CUE.pgvecPostgres - 10, CUE.pgvecPostgres + 10],
            [0, 1, 1, 0.4],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          ),
        }}
      >
        same vectors, different home
      </div>

      {/* Side-by-side: WITHOUT pgvector vs WITH pgvector */}
      <div
        style={{
          position: "absolute",
          top: 370,
          left: 80,
          right: 80,
          display: "grid",
          gridTemplateColumns: "1fr 120px 1fr",
          gap: 40,
          alignItems: "start",
        }}
      >
        {/* LEFT: "without" — 2 separate services */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.pgvecInsteadOf, CUE.pgvecInsteadOf + 20, CUE.pgvecOneLess + 60, CUE.pgvecOneLess + 100],
              [0, 1, 1, 0.35],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <PanelHeading>without pgvector</PanelHeading>
          <div style={{ display: "flex", flexDirection: "column", gap: 18, marginTop: 18 }}>
            <ServiceBox icon="🐘" label="PostgreSQL" sublabel="for your data" />
            <ServiceBox
              icon="🔍"
              label="Qdrant"
              sublabel="for your vectors"
              accent={COLORS.qdrant}
              strikethrough={frame >= CUE.pgvecOneLess + 30}
            />
          </div>
        </div>

        {/* MIDDLE: arrow */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: 380,
            opacity: interpolate(
              frame,
              [CUE.pgvecInsteadOf + 30, CUE.pgvecInsteadOf + 60],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 56,
              color: COLORS.accent,
              textShadow: `0 0 20px ${COLORS.accentGlow}`,
            }}
          >
            ➜
          </div>
        </div>

        {/* RIGHT: "with" — one service */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.pgvecExtension, CUE.pgvecExtension + 20],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <PanelHeading>with pgvector</PanelHeading>
          <div style={{ display: "flex", flexDirection: "column", gap: 18, marginTop: 18 }}>
            <ServiceBox
              icon="🐘"
              label="PostgreSQL"
              sublabel="data + vectors"
              accent={COLORS.pgvector}
              badge="+ pgvector"
              highlight
            />
            {/* placeholder space to align with left column */}
            <div style={{ height: 100, opacity: 0 }} />
          </div>

          {/* "One less service" callout */}
          <div
            style={{
              marginTop: 30,
              padding: "14px 22px",
              background: "rgba(0,255,136,0.08)",
              border: `1px solid rgba(0,255,136,0.4)`,
              borderRadius: 12,
              fontFamily: FONTS.mono,
              fontSize: 22,
              fontWeight: 700,
              color: COLORS.neonGreen,
              textAlign: "center",
              boxShadow: `0 0 20px rgba(0,255,136,0.2)`,
              opacity: interpolate(
                frame,
                [CUE.pgvecOneLess, CUE.pgvecOneLess + 20],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            ✓ one less service to manage
          </div>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// Shared helpers
// ═══════════════════════════════════════════════════════════════════════
const BackendChyron: React.FC<{ name: string; icon: string; tagline: string }> = ({
  name,
  icon,
  tagline,
}) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 18,
      padding: "12px 24px",
      background: COLORS.bgCard,
      border: `1px solid ${BACKEND_COLORS[name]}44`,
      borderRadius: 14,
      width: "fit-content",
      boxShadow: `0 0 24px ${BACKEND_COLORS[name]}22`,
    }}
  >
    <span style={{ fontSize: 44 }}>{icon}</span>
    <div>
      <div
        style={{
          fontFamily: FONTS.mono,
          fontSize: 30,
          fontWeight: 700,
          color: BACKEND_COLORS[name],
          letterSpacing: 1,
        }}
      >
        {name}
      </div>
      <div
        style={{
          fontFamily: FONTS.mono,
          fontSize: 20,
          color: COLORS.textMuted,
          marginTop: 4,
        }}
      >
        {tagline}
      </div>
    </div>
  </div>
);

const PanelHeading: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      fontFamily: FONTS.mono,
      fontSize: 20,
      color: COLORS.textMuted,
      letterSpacing: 5,
      textTransform: "uppercase",
    }}
  >
    {children}
  </div>
);

const ChatChip: React.FC<{
  text: string;
  startFrame: number;
  frame: number;
  color: string;
  small?: boolean;
  style?: React.CSSProperties;
}> = ({ text, startFrame, frame, color, small, style }) => {
  const opacity = interpolate(frame, [startFrame, startFrame + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const tx = interpolate(frame, [startFrame, startFrame + 12], [-16, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        padding: small ? "10px 16px" : "14px 20px",
        background: "rgba(255,255,255,0.04)",
        border: `1px solid ${COLORS.border}`,
        borderRadius: 10,
        fontFamily: FONTS.mono,
        fontSize: small ? 22 : 26,
        color,
        opacity,
        transform: `translateX(${tx}px)`,
        ...style,
      }}
    >
      {text}
    </div>
  );
};

const ServiceBox: React.FC<{
  icon: string;
  label: string;
  sublabel: string;
  accent?: string;
  badge?: string;
  highlight?: boolean;
  strikethrough?: boolean;
}> = ({ icon, label, sublabel, accent, badge, highlight, strikethrough }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 20,
      padding: "20px 24px",
      background: highlight
        ? "rgba(196,78,82,0.10)"
        : COLORS.bgCard,
      border: `2px solid ${highlight ? accent || COLORS.border : COLORS.border}`,
      borderRadius: 14,
      position: "relative",
      boxShadow: highlight ? `0 0 26px ${accent}55` : "none",
      opacity: strikethrough ? 0.35 : 1,
      textDecoration: strikethrough ? "line-through" : "none",
      transition: "opacity 0.3s",
    }}
  >
    <span style={{ fontSize: 48 }}>{icon}</span>
    <div>
      <div
        style={{
          fontFamily: FONTS.body,
          fontSize: 26,
          fontWeight: 700,
          color: accent || COLORS.text,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: FONTS.mono,
          fontSize: 20,
          color: COLORS.textMuted,
          marginTop: 4,
        }}
      >
        {sublabel}
      </div>
    </div>
    {badge && (
      <div
        style={{
          position: "absolute",
          top: -12,
          right: -12,
          padding: "6px 14px",
          background: COLORS.neonGreen,
          color: "#0a0a0f",
          borderRadius: 8,
          fontFamily: FONTS.mono,
          fontSize: 18,
          fontWeight: 800,
          boxShadow: `0 0 16px rgba(0,255,136,0.4)`,
        }}
      >
        {badge}
      </div>
    )}
    {strikethrough && (
      <div
        style={{
          position: "absolute",
          right: 16,
          top: 16,
          fontFamily: FONTS.mono,
          fontSize: 17,
          fontWeight: 800,
          color: COLORS.neonGreen,
          background: "rgba(0,255,136,0.10)",
          border: `1px solid rgba(0,255,136,0.4)`,
          borderRadius: 8,
          padding: "5px 12px",
        }}
      >
        removed
      </div>
    )}
  </div>
);
