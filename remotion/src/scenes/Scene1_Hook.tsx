import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";
import { ChatBubble } from "../components/ChatBubble";
import { AnimatedText } from "../components/AnimatedText";
import { FadeTransition } from "../components/FadeTransition";

// Results-table teaser data (shown blurred behind "So I built a benchmark")
const TEASER_BACKENDS = ["buffer", "summary", "qdrant", "pgvector"] as const;
const TEASER_ROWS = [
  { metric: "Recall @ Turn 50",   values: ["90%",     "42%",    "82%",    "82%"] },
  { metric: "Avg Latency / Turn", values: ["10.3s",   "36.0s",  "7.0s",   "7.0s"] },
  { metric: "Cost / 1K Convos",   values: ["$4,303",  "$2,256", "$418",   "$416"] },
  { metric: "Total Tokens / Run", values: ["717K",    "376K",   "70K",    "69K"] },
  { metric: "Wall Clock (5 runs)",values: ["45 min",  "3 hrs",  "32 min", "32 min"] },
];

// Cue points synced to public/audio/scene01.wav (whisper word-level timestamps, 30fps).
// Audio trimmed by 0.6s at start, end at 25.78s (shift -18 frames from original).
const CUE = {
  mostStart: 0,       // 0.33s "Most"
  cantRemember: 19,    // 1.35s "cannot"
  hookEnd: 116,        // 4.56s end of first sentence
  chatStart: 116,      // 4.56s "You ..."
  msg1Start: 117,      // 4.60s user msg 1 starts ("You tell it your dog's name")
  msg2Start: 191,      // 7.06s user msg 2 starts ("you tell it you are allergic")
  msg3Start: 267,      // 9.61s user msg 3 starts ("you share your flight")
  twentyTurns: 321,    // 11.41s "20 turns later"
  questionMsg: 358,    // 12.63s "What's my dog's name?"
  failMsg: 384,        // 13.50s bot fails
  redFlash: 389,       // ~13.67s red flash (kept ≤ chatEnd-14 so the flash fade range stays monotonic)
  chatEnd: 404,        // 14.17s chat fades
  theQuestion: 410,    // 14.36s "The question"
  whichArch: 495,      // 17.19s "It's which"
  benchmark: 573,      // 19.80s "So I built"
  titleStart: 641,     // 22.08s "This is"
  showdownWord: 703,   // 24.14s "showdown"
  end: 718,            // 24.73s audio end (742 frames @30fps)
};

export const Scene1_Hook: React.FC = () => {
  const frame = useCurrentFrame();

  const titleScale = interpolate(frame, [CUE.titleStart, CUE.titleStart + 30], [0.85, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleOpacity = interpolate(frame, [CUE.titleStart, CUE.titleStart + 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const underlineWidth = interpolate(
    frame,
    [CUE.titleStart + 25, CUE.showdownWord],
    [0, 100],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const glitchOffset =
    frame > CUE.titleStart + 5 && frame < CUE.titleStart + 25 && frame % 4 < 2
      ? Math.sin(frame * 0.8) * 3
      : 0;

  return (
    <FadeTransition durationFrames={CUE.end}>
      <Audio src={staticFile("audio/scene01.wav")} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 40%, #0f1520 0%, ${COLORS.bg} 70%)`,
          padding: 80,
          justifyContent: "center",
        }}
      >
        {/* Phase 1: Hook headline (0 → 142f) */}
        <div
          style={{
            position: "absolute",
            left: 120,
            right: 120,
            top: 380,
            opacity: interpolate(
              frame,
              [0, 10, CUE.hookEnd - 8, CUE.hookEnd + 4],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <AnimatedText
            text="Most chatbots"
            startFrame={CUE.mostStart}
            fontSize={64}
            fontWeight={700}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={22}
          />
          <AnimatedText
            text="can't remember what you said five minutes ago."
            startFrame={CUE.cantRemember}
            fontSize={56}
            fontWeight={700}
            color={COLORS.accent}
            glow
            textAlign="center"
            mode="wordByWord"
            durationFrames={90}
            style={{ marginTop: 20 }}
          />
        </div>

        {/* Phase 2: Chat demo (142 → 446f) */}
        <div
          style={{
            opacity: interpolate(
              frame,
              [CUE.chatStart, CUE.chatStart + 12, CUE.chatEnd - 8, CUE.chatEnd + 6],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            position: "absolute",
            top: 110,
            left: 220,
            right: 220,
          }}
        >
          <div
            style={{
              background: COLORS.bgCard,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 16,
              padding: 28,
              backdropFilter: "blur(20px)",
              position: "relative",
            }}
          >
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 18,
                color: COLORS.textMuted,
                marginBottom: 20,
                display: "flex",
                gap: 10,
                alignItems: "center",
              }}
            >
              <span style={{ width: 14, height: 14, borderRadius: "50%", background: "#ff5f57" }} />
              <span style={{ width: 14, height: 14, borderRadius: "50%", background: "#febc2e" }} />
              <span style={{ width: 14, height: 14, borderRadius: "50%", background: "#28c840" }} />
              <span style={{ marginLeft: 14 }}>AI Chat</span>
            </div>

            <ChatBubble
              text="My dog's name is Baxter."
              sender="user"
              startFrame={CUE.msg1Start}
              typewriter
              typewriterDuration={40}
            />
            <ChatBubble
              text="I'm allergic to shellfish."
              sender="user"
              startFrame={CUE.msg2Start}
              typewriter
              typewriterDuration={35}
            />
            <ChatBubble
              text="My flight to Tokyo is March 15th."
              sender="user"
              startFrame={CUE.msg3Start}
              typewriter
              typewriterDuration={40}
            />

            {/* "20 turns later" divider */}
            <div
              style={{
                opacity: interpolate(
                  frame,
                  [CUE.twentyTurns, CUE.twentyTurns + 12],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
                textAlign: "center",
                fontFamily: FONTS.mono,
                fontSize: 20,
                color: COLORS.textMuted,
                padding: "16px 0",
                letterSpacing: 4,
              }}
            >
              · · · 20 turns later · · ·
            </div>

            <ChatBubble
              text="What's my dog's name?"
              sender="user"
              startFrame={CUE.questionMsg}
              typewriter
              typewriterDuration={20}
            />
            <ChatBubble
              text="I'm sorry, I don't have any information about your dog."
              sender="bot"
              startFrame={CUE.failMsg}
              typewriter
              typewriterDuration={22}
            />

            {/* Red flash on bot failure */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                borderRadius: 16,
                border: `2px solid ${COLORS.danger}`,
                opacity: interpolate(
                  frame,
                  [CUE.redFlash, CUE.redFlash + 6, CUE.redFlash + 14, CUE.chatEnd],
                  [0, 0.7, 0.7, 0],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
                pointerEvents: "none",
                boxShadow: `0 0 40px ${COLORS.dangerGlow}`,
              }}
            />
          </div>
        </div>

        {/* Phase 2.5: Blurred results-table teaser behind narration (446 → 670f) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "flex-end",
            paddingBottom: 70,
            opacity: interpolate(
              frame,
              [CUE.chatEnd - 4, CUE.theQuestion + 20, CUE.titleStart - 30, CUE.titleStart - 8],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            pointerEvents: "none",
            zIndex: 0,
          }}
        >
          {/* "Coming up" tag */}
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 18,
              color: COLORS.accent,
              letterSpacing: 6,
              textTransform: "uppercase",
              marginBottom: 18,
              opacity: 0.85,
              textShadow: `0 0 16px ${COLORS.accentGlow}`,
            }}
          >
            ↓ Coming up
          </div>

          {/* Blurred table */}
          <div
            style={{
              filter: "blur(3.5px)",
              opacity: 0.7,
              transform: `scale(${interpolate(
                frame,
                [CUE.chatEnd, CUE.benchmark],
                [0.94, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              )})`,
            }}
          >
            <div
              style={{
                background: COLORS.bgCard,
                border: `1px solid ${COLORS.border}`,
                borderRadius: 16,
                overflow: "hidden",
              }}
            >
              {/* Header row */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "340px repeat(4, 220px)",
                  background: "rgba(255,255,255,0.05)",
                  borderBottom: `1px solid ${COLORS.border}`,
                }}
              >
                <div
                  style={{
                    padding: "22px 28px",
                    fontFamily: FONTS.mono,
                    fontSize: 22,
                    color: COLORS.textMuted,
                    fontWeight: 700,
                    letterSpacing: 1,
                  }}
                >
                  Metric
                </div>
                {TEASER_BACKENDS.map((b) => (
                  <div
                    key={b}
                    style={{
                      padding: "22px 24px",
                      fontFamily: FONTS.mono,
                      fontSize: 26,
                      fontWeight: 700,
                      color: BACKEND_COLORS[b],
                      textAlign: "center",
                    }}
                  >
                    {b}
                  </div>
                ))}
              </div>

              {/* Data rows */}
              {TEASER_ROWS.map((row, i) => (
                <div
                  key={i}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "340px repeat(4, 220px)",
                    borderBottom:
                      i < TEASER_ROWS.length - 1 ? `1px solid ${COLORS.border}` : "none",
                  }}
                >
                  <div
                    style={{
                      padding: "20px 28px",
                      fontFamily: FONTS.body,
                      fontSize: 22,
                      color: COLORS.textMuted,
                    }}
                  >
                    {row.metric}
                  </div>
                  {row.values.map((v, vi) => (
                    <div
                      key={vi}
                      style={{
                        padding: "20px 24px",
                        fontFamily: FONTS.mono,
                        fontSize: 26,
                        fontWeight: 600,
                        color: COLORS.text,
                        textAlign: "center",
                      }}
                    >
                      {v}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Phase 3: The question (446 → 611f) */}
        <div
          style={{
            position: "absolute",
            left: 120,
            right: 120,
            top: 180,
            opacity: interpolate(
              frame,
              [CUE.chatEnd, CUE.theQuestion - 4, CUE.benchmark - 8, CUE.benchmark + 4],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            zIndex: 1,
          }}
        >
          <AnimatedText
            text="The question isn't whether memory matters."
            startFrame={CUE.theQuestion}
            fontSize={42}
            color={COLORS.textMuted}
            textAlign="center"
            mode="wordByWord"
            durationFrames={70}
          />
          <AnimatedText
            text="It's which memory architecture actually works."
            startFrame={CUE.whichArch}
            fontSize={48}
            fontWeight={700}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={85}
            style={{ marginTop: 24 }}
          />
        </div>

        {/* Phase 4: Benchmark line (611 → 682f) */}
        <div
          style={{
            position: "absolute",
            left: 120,
            right: 120,
            top: 480,
            opacity: interpolate(
              frame,
              [CUE.benchmark, CUE.benchmark + 8, CUE.titleStart - 6, CUE.titleStart + 2],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <AnimatedText
            text="So I built a benchmark to find out."
            startFrame={CUE.benchmark}
            fontSize={44}
            fontWeight={600}
            color={COLORS.neonGreen}
            glow
            glowColor="rgba(0,255,136,0.3)"
            textAlign="center"
            mode="wordByWord"
            durationFrames={65}
          />
        </div>

        {/* Phase 5: Title card (682 → 777f) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            opacity: titleOpacity,
            transform: `scale(${titleScale}) translateX(${glitchOffset}px)`,
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 20,
              color: COLORS.accent,
              letterSpacing: 8,
              textTransform: "uppercase",
              marginBottom: 24,
            }}
          >
            Benchmark
          </div>
          <h1
            style={{
              fontFamily: FONTS.body,
              fontSize: 96,
              fontWeight: 800,
              color: COLORS.text,
              margin: 0,
              textAlign: "center",
              letterSpacing: -2,
              textShadow: `0 0 60px ${COLORS.accentGlow}`,
            }}
          >
            Agent Memory
            <br />
            Showdown
          </h1>
          <div
            style={{
              width: `${underlineWidth}%`,
              maxWidth: 600,
              height: 4,
              background: `linear-gradient(90deg, transparent, ${COLORS.accent}, transparent)`,
              marginTop: 24,
              borderRadius: 2,
            }}
          />
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 26,
              color: COLORS.textMuted,
              marginTop: 36,
              letterSpacing: 1,
              opacity: interpolate(
                frame,
                [CUE.showdownWord, CUE.showdownWord + 10],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
            }}
          >
            4 backends · 50 turns · 1,000 LLM calls
          </div>
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
