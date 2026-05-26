import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { COLORS, FONTS } from "../styles/theme";
import { ChatBubble } from "../components/ChatBubble";
import { AnimatedText } from "../components/AnimatedText";
import { FadeTransition } from "../components/FadeTransition";

// Cue points synced to public/audio/scene01.wav (whisper word-level timestamps, 30fps).
// Times in seconds → frames at 30fps.
const CUE = {
  mostStart: 2,        // 0.05s "Most"
  cantRemember: 47,    // 1.58s "cannot"
  hookEnd: 142,        // 4.72s end of first sentence
  chatStart: 142,      // 4.72s "You ..."
  msg1Start: 149,      // 4.96s user msg 1 starts
  msg2Start: 235,      // 7.83s user msg 2 starts
  msg3Start: 297,      // 9.91s user msg 3 starts
  twentyTurns: 358,    // 11.92s "20 turns later"
  questionMsg: 395,    // 13.16s "What's my dog's name?"
  failMsg: 419,        // 13.95s bot fails
  redFlash: 430,       // ~14.3s red flash
  chatEnd: 446,        // 14.88s chat fades
  theQuestion: 454,    // 15.14s "The question"
  whichArch: 524,      // 17.48s "It's which"
  benchmark: 611,      // 20.36s "So I built"
  titleStart: 682,     // 22.72s "This is"
  showdownWord: 763,   // 25.44s "showdown"
  end: 777,            // 25.888s audio end
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
                fontSize: 13,
                color: COLORS.textMuted,
                marginBottom: 18,
                display: "flex",
                gap: 8,
                alignItems: "center",
              }}
            >
              <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#ff5f57" }} />
              <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#febc2e" }} />
              <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#28c840" }} />
              <span style={{ marginLeft: 12 }}>AI Chat</span>
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
                fontSize: 15,
                color: COLORS.textMuted,
                padding: "14px 0",
                letterSpacing: 3,
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

        {/* Phase 3: The question (446 → 611f) */}
        <div
          style={{
            position: "absolute",
            left: 120,
            right: 120,
            top: 380,
            opacity: interpolate(
              frame,
              [CUE.chatEnd, CUE.theQuestion - 4, CUE.benchmark - 8, CUE.benchmark + 4],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
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
              fontSize: 14,
              color: COLORS.accent,
              letterSpacing: 6,
              textTransform: "uppercase",
              marginBottom: 20,
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
              fontSize: 18,
              color: COLORS.textMuted,
              marginTop: 32,
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
