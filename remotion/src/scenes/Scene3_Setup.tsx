import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS } from "../styles/theme";
import { AnimatedText } from "../components/AnimatedText";
import { GlassCard } from "../components/GlassCard";
import { AnimatedCounter } from "../components/AnimatedCounter";
import { FadeTransition } from "../components/FadeTransition";
import { SEEDED_FACTS } from "../data/benchmarkData";

const INFRA_BOXES = [
  { label: "DO Droplet", sub: "8GB / 4vCPU", icon: "☁️", x: 400, y: 120 },
  { label: "Claude 4.5 Sonnet", sub: "DO Serverless Inference", icon: "🧠", x: 900, y: 120 },
  { label: "Qdrant", sub: "Docker container", icon: "📦", x: 250, y: 360 },
  { label: "PostgreSQL 16", sub: "pgvector extension", icon: "🐘", x: 700, y: 360 },
  { label: "Embeddings", sub: "all-MiniLM-L6-v2", icon: "🔢", x: 1100, y: 360 },
];

const CONNECTIONS = [
  { from: 0, to: 2 },
  { from: 0, to: 3 },
  { from: 0, to: 1 },
  { from: 1, to: 4 },
];

export const Scene3_Setup: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FadeTransition durationFrames={2250}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 60% 30%, #0d1825 0%, ${COLORS.bg} 70%)`,
          padding: 80,
        }}
      >
        {/* Phase 1: Architecture diagram (0-25s / 0-750f) */}
        <div
          style={{
            opacity: interpolate(frame, [0, 15, 700, 740], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: 60,
          }}
        >
          <AnimatedText
            text="Infrastructure"
            startFrame={0}
            fontSize={44}
            fontWeight={700}
            textAlign="center"
          />

          <svg
            width={1920}
            height={600}
            style={{ position: "absolute", top: 60, left: 0, pointerEvents: "none" }}
          >
            {CONNECTIONS.map((conn, i) => {
              const from = INFRA_BOXES[conn.from];
              const to = INFRA_BOXES[conn.to];
              const lineOpacity = interpolate(
                frame,
                [200 + i * 50, 230 + i * 50],
                [0, 0.4],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );
              return (
                <line
                  key={i}
                  x1={from.x + 100}
                  y1={from.y + 50}
                  x2={to.x + 100}
                  y2={to.y}
                  stroke={COLORS.accent}
                  strokeWidth={2}
                  opacity={lineOpacity}
                  strokeDasharray="8,4"
                />
              );
            })}
          </svg>

          {INFRA_BOXES.map((box, i) => {
            const boxScale = spring({
              frame: Math.max(0, frame - 60 - i * 40),
              fps,
              config: { damping: 14, stiffness: 100 },
            });
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: box.x,
                  top: box.y + 60,
                  transform: `scale(${boxScale})`,
                  background: COLORS.bgCard,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 12,
                  padding: "16px 24px",
                  textAlign: "center",
                  backdropFilter: "blur(10px)",
                  width: 200,
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 6 }}>{box.icon}</div>
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
                    marginTop: 4,
                  }}
                >
                  {box.sub}
                </div>
              </div>
            );
          })}
        </div>

        {/* Phase 2: Fact timeline (25-55s / 750-1650f) */}
        <div
          style={{
            opacity: interpolate(frame, [740, 770, 1600, 1640], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            padding: "60px 80px",
          }}
        >
          <AnimatedText
            text="10 Facts Hidden Across 50 Turns"
            startFrame={750}
            fontSize={40}
            fontWeight={700}
            textAlign="center"
          />

          {/* Timeline bar */}
          <div
            style={{
              position: "absolute",
              top: 200,
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
                width: `${interpolate(frame, [780, 900], [0, 100], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })}%`,
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
                top: 212,
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

          {/* Fact pins */}
          {SEEDED_FACTS.map((f, i) => {
            const pinFrame = 800 + i * 50;
            const pinOpacity = interpolate(frame, [pinFrame, pinFrame + 15], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const pinY = interpolate(frame, [pinFrame, pinFrame + 15], [-20, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const xPos = 100 + ((f.turn - 1) / 49) * (1920 - 200);
            const isEven = i % 2 === 0;

            return (
              <div key={i}>
                {/* Pin dot */}
                <div
                  style={{
                    position: "absolute",
                    top: 194,
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
                {/* Fact label */}
                <div
                  style={{
                    position: "absolute",
                    top: isEven ? 235 : 145,
                    left: xPos - 120,
                    width: 240,
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
                      fontSize: 14,
                      color: COLORS.text,
                      background: COLORS.bgCard,
                      border: `1px solid ${COLORS.border}`,
                      borderRadius: 8,
                      padding: "6px 10px",
                      lineHeight: 1.3,
                    }}
                  >
                    {f.fact}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Probe indicators */}
          {[15, 50].map((turn) => {
            const probeFrame = 1350;
            const probeOpacity = interpolate(
              frame,
              [probeFrame, probeFrame + 20],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            const xPos = 100 + ((turn - 1) / 49) * (1920 - 200);
            return (
              <div
                key={turn}
                style={{
                  position: "absolute",
                  top: 170,
                  left: xPos - 30,
                  width: 60,
                  textAlign: "center",
                  opacity: probeOpacity,
                }}
              >
                <div
                  style={{
                    fontFamily: FONTS.mono,
                    fontSize: 12,
                    color: COLORS.neonGreen,
                    background: "rgba(0,255,136,0.1)",
                    border: `1px solid rgba(0,255,136,0.3)`,
                    borderRadius: 6,
                    padding: "2px 8px",
                  }}
                >
                  QUIZ
                </div>
              </div>
            );
          })}
        </div>

        {/* Phase 3: Stats (55-75s / 1650-2250f) */}
        <div
          style={{
            opacity: interpolate(frame, [1640, 1670], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              gap: 60,
              marginTop: 40,
            }}
          >
            {[
              { label: "Backends", value: 4 },
              { label: "Runs each", value: 5 },
              { label: "Turns/run", value: 50 },
            ].map((stat, i) => (
              <GlassCard key={i} startFrame={1670 + i * 20} padding={40}>
                <div style={{ textAlign: "center" }}>
                  <AnimatedCounter
                    value={stat.value}
                    startFrame={1690 + i * 20}
                    fontSize={64}
                    color={COLORS.accent}
                  />
                  <div
                    style={{
                      fontFamily: FONTS.body,
                      fontSize: 20,
                      color: COLORS.textMuted,
                      marginTop: 8,
                    }}
                  >
                    {stat.label}
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>

          <div
            style={{
              fontFamily: FONTS.body,
              fontSize: 32,
              color: COLORS.text,
              marginTop: 60,
              textAlign: "center",
              opacity: interpolate(frame, [1800, 1830], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            = <AnimatedCounter value={1000} startFrame={1830} fontSize={40} color={COLORS.neonGreen} suffix="+" /> LLM calls
          </div>
        </div>
      </AbsoluteFill>
    </FadeTransition>
  );
};
