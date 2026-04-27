import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "../styles/theme";
import { ChatBubble } from "../components/ChatBubble";
import { AnimatedText } from "../components/AnimatedText";
import { FadeTransition } from "../components/FadeTransition";

export const Scene1_Hook: React.FC = () => {
  const frame = useCurrentFrame();

  const titleScale = interpolate(frame, [900, 930], [0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleOpacity = interpolate(frame, [900, 925], [0, 1], {
    extrapolateRight: "clamp",
  });
  const underlineWidth = interpolate(frame, [940, 1000], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const glitchOffset =
    frame > 920 && frame < 940 && frame % 4 < 2
      ? Math.sin(frame * 0.8) * 3
      : 0;

  return (
    <FadeTransition durationFrames={1350}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 40%, #0f1520 0%, ${COLORS.bg} 70%)`,
          padding: 80,
          justifyContent: "center",
        }}
      >
        {/* Phase 1: Chat demo (0-14s / 0-420f) */}
        <div
          style={{
            opacity: interpolate(frame, [0, 10, 400, 430], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            top: 120,
            left: 200,
            right: 200,
          }}
        >
          <div
            style={{
              background: COLORS.bgCard,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 16,
              padding: 32,
              backdropFilter: "blur(20px)",
            }}
          >
            <div
              style={{
                fontFamily: FONTS.mono,
                fontSize: 14,
                color: COLORS.textMuted,
                marginBottom: 24,
                display: "flex",
                gap: 8,
              }}
            >
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  background: "#ff5f57",
                  display: "inline-block",
                }}
              />
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  background: "#febc2e",
                  display: "inline-block",
                }}
              />
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  background: "#28c840",
                  display: "inline-block",
                }}
              />
              <span style={{ marginLeft: 12 }}>AI Chat</span>
            </div>

            <ChatBubble
              text="My dog's name is Baxter. He's a golden retriever!"
              sender="user"
              startFrame={30}
              typewriter
              typewriterDuration={45}
            />
            <ChatBubble
              text="That's wonderful! Golden retrievers are such loyal companions. Baxter is a great name!"
              sender="bot"
              startFrame={90}
              typewriter
              typewriterDuration={50}
            />

            {/* 20 turns later indicator */}
            <div
              style={{
                opacity: interpolate(frame, [160, 180], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
                textAlign: "center",
                fontFamily: FONTS.mono,
                fontSize: 16,
                color: COLORS.textMuted,
                padding: "16px 0",
                letterSpacing: 3,
              }}
            >
              · · · 20 turns later · · ·
            </div>

            <ChatBubble
              text="What's my dog's name?"
              sender="user"
              startFrame={210}
              typewriter
              typewriterDuration={25}
            />
            <ChatBubble
              text="I'm sorry, I don't have any information about your dog. Could you tell me more?"
              sender="bot"
              startFrame={270}
              typewriter
              typewriterDuration={50}
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
                  [330, 340, 355, 370],
                  [0, 0.6, 0.6, 0],
                  {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  }
                ),
                pointerEvents: "none",
                boxShadow: `0 0 40px ${COLORS.dangerGlow}`,
              }}
            />
          </div>
        </div>

        {/* Phase 2: Narration text (14-35s / 420-1050f) */}
        <div
          style={{
            position: "absolute",
            left: 120,
            right: 120,
            top: 200,
            opacity: interpolate(frame, [430, 450, 880, 900], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <AnimatedText
            text="Every AI chatbot has a dirty secret —"
            startFrame={440}
            fontSize={44}
            fontWeight={600}
            color={COLORS.text}
            mode="wordByWord"
            durationFrames={40}
          />
          <AnimatedText
            text="most of them can't remember what you said five minutes ago."
            startFrame={500}
            fontSize={44}
            fontWeight={600}
            color={COLORS.accent}
            glow
            mode="wordByWord"
            durationFrames={50}
            style={{ marginTop: 20 }}
          />

          <AnimatedText
            text="The question isn't whether memory matters —"
            startFrame={620}
            fontSize={36}
            color={COLORS.textMuted}
            mode="wordByWord"
            durationFrames={35}
            style={{ marginTop: 60 }}
          />
          <AnimatedText
            text="it's which memory architecture actually works."
            startFrame={680}
            fontSize={36}
            fontWeight={600}
            color={COLORS.text}
            mode="wordByWord"
            durationFrames={35}
            style={{ marginTop: 12 }}
          />

          <AnimatedText
            text="So I built a benchmark to find out."
            startFrame={780}
            fontSize={36}
            color={COLORS.neonGreen}
            glow
            glowColor="rgba(0,255,136,0.3)"
            mode="wordByWord"
            durationFrames={30}
            style={{ marginTop: 40 }}
          />
        </div>

        {/* Phase 3: Title card (35-45s / 1050-1350f) */}
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
              fontSize: 84,
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
              opacity: interpolate(frame, [1000, 1020], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            4 backends · 50 turns · 1,000 LLM calls
          </div>
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
