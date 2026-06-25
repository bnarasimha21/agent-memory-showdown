import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "./styles/theme";
import { AnimatedText } from "./components/AnimatedText";
import { AnimatedCounter } from "./components/AnimatedCounter";

// 45s vertical (1080x1920 @30fps = 1350 frames) short-form cut for X / Shorts / Reels.
// Beats timed to the stitched voiceover (Variant A); captions are burned in so
// it also reads silent (Variant B). Audio is muxed in post, not embedded here.
//
// CUE_VO is locked to the recorded narration — do NOT shift these values or the
// VOICEOVER variant goes out of sync. Used by the 45s <ShortVertical /> cut.
export const CUE_VO = {
  hook: 8,            // 0.27s
  premise: 180,       // 6.0s
  recall: 330,        // 11.0s
  recallBuffer: 345,  // 11.5s
  recallVector: 450,  // 15.0s
  recallSummary: 594, // 19.8s
  recallTag: 640,     // 21.3s "less than half"
  cost: 720,          // 24.0s
  cost10x: 885,       // 29.5s
  takeaway: 1080,     // 36.0s
  cta: 1260,          // 42.0s
  end: 1350,          // 45.0s
};

type CueMap = typeof CUE_VO;

// CUE_TIGHT packs the beats back-to-back with only a short hold after each beat's
// animation finishes — kills the narration-shaped dead air. Used by the MUSIC cut
// (<ShortVerticalTight />, ~28s). NOT for voiceover: there is no narration to sync to.
export const CUE_TIGHT: CueMap = {
  hook: 8,
  premise: 168,
  recall: 280,
  recallBuffer: 295,
  recallVector: 325,
  recallSummary: 360,
  recallTag: 395,
  cost: 460,
  cost10x: 555,
  takeaway: 620,
  cta: 730,
  end: 830,
};

const fade = (frame: number, a: number, b: number, c: number, d: number) =>
  interpolate(frame, [a, b, c, d], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const rise = (frame: number, at: number, dur = 14) =>
  interpolate(frame, [at, at + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const RECALL = [
  { b: "buffer", v: 90 },
  { b: "qdrant", v: 82 },
  { b: "pgvector", v: 82 },
  { b: "summary", v: 42 },
];
const COST = [
  { b: "buffer", v: 4303 },
  { b: "summary", v: 2256 },
  { b: "qdrant", v: 418 },
  { b: "pgvector", v: 416 },
];

// ---- Deterministic particle field (no Math.random at render time) ----
const PARTICLES = Array.from({ length: 34 }, (_, i) => {
  // simple LCG so positions are stable across every frame + render
  const s = (i * 1103515245 + 12345) & 0x7fffffff;
  const r1 = ((s >> 4) % 1000) / 1000;
  const r2 = ((s >> 9) % 1000) / 1000;
  const r3 = ((s >> 14) % 1000) / 1000;
  return {
    x: r1 * 100,
    baseY: r2 * 100,
    size: 2 + r3 * 4,
    speed: 0.6 + r2 * 1.6,
    phase: r1 * Math.PI * 2,
  };
});

const Background: React.FC<{ frame: number }> = ({ frame }) => {
  const gridShift = (frame * 0.25) % 60;
  return (
    <AbsoluteFill>
      {/* base radial */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 90% 60% at 50% 30%, #141a30 0%, ${COLORS.bg} 65%)`,
        }}
      />
      {/* subtle drifting grid */}
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(rgba(0,212,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.05) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
          backgroundPosition: `0px ${gridShift}px`,
          maskImage:
            "radial-gradient(ellipse 80% 70% at 50% 45%, black 30%, transparent 80%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 80% 70% at 50% 45%, black 30%, transparent 80%)",
        }}
      />
      {/* floating particles */}
      {PARTICLES.map((p, i) => {
        const y = (p.baseY - ((frame * p.speed) / 30) * 8 + 200) % 100;
        const twinkle = 0.25 + 0.25 * (1 + Math.sin(frame / 14 + p.phase)) ;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${p.x}%`,
              top: `${y}%`,
              width: p.size,
              height: p.size,
              borderRadius: "50%",
              background: COLORS.accent,
              opacity: twinkle,
              boxShadow: `0 0 ${p.size * 3}px ${COLORS.accent}`,
            }}
          />
        );
      })}
      {/* vignette */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse 75% 65% at 50% 45%, transparent 55%, rgba(0,0,0,0.55) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

// Persistent top kicker + bottom progress/brand chrome.
const Chrome: React.FC<{ frame: number; chromeOpacity: number; endFrame: number }> = ({
  frame,
  chromeOpacity,
  endFrame,
}) => {
  const progress = interpolate(frame, [0, endFrame], [0, 100], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ opacity: chromeOpacity, pointerEvents: "none" }}>
      {/* top kicker */}
      <div
        style={{
          position: "absolute",
          top: 90,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 14,
        }}
      >
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: COLORS.accent,
            boxShadow: `0 0 14px ${COLORS.accent}`,
          }}
        />
        <span
          style={{
            fontFamily: FONTS.mono,
            fontSize: 26,
            fontWeight: 700,
            letterSpacing: 4,
            color: COLORS.textMuted,
          }}
        >
          AGENT MEMORY SHOWDOWN
        </span>
      </div>
      {/* bottom progress bar */}
      <div
        style={{
          position: "absolute",
          bottom: 56,
          left: 80,
          right: 80,
          height: 6,
          borderRadius: 999,
          background: "rgba(255,255,255,0.08)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${progress}%`,
            background: `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.neonGreen})`,
            boxShadow: `0 0 16px ${COLORS.accentGlow}`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

const Chip: React.FC<{ name: string; fontSize?: number }> = ({
  name,
  fontSize = 30,
}) => (
  <span
    style={{
      fontFamily: FONTS.mono,
      fontSize,
      fontWeight: 700,
      color: BACKEND_COLORS[name],
      border: `2px solid ${BACKEND_COLORS[name]}66`,
      background: `${BACKEND_COLORS[name]}14`,
      borderRadius: 999,
      padding: "8px 22px",
      display: "inline-block",
    }}
  >
    {name}
  </span>
);

// One animated metric row (used by both Recall and Cost beats).
const MetricRow: React.FC<{
  name: string;
  frame: number;
  fps: number;
  start: number;
  pct: number; // bar fill % of track
  value: number;
  prefix?: string;
  suffix?: string;
  highlight?: boolean;
}> = ({ name, frame, fps, start, pct, value, prefix, suffix, highlight }) => {
  const grow = spring({
    frame: Math.max(0, frame - start),
    fps,
    config: { damping: 18, stiffness: 60 },
  });
  const color = highlight ? COLORS.danger : BACKEND_COLORS[name];
  const barBg = highlight
    ? `linear-gradient(90deg, ${COLORS.summary}, ${COLORS.danger})`
    : `linear-gradient(90deg, ${BACKEND_COLORS[name]}88, ${BACKEND_COLORS[name]})`;
  return (
    <div
      style={{
        opacity: rise(frame, start - 6, 14),
        display: "flex",
        alignItems: "center",
        gap: 22,
        background: COLORS.bgCard,
        border: `1px solid ${color}33`,
        borderRadius: 18,
        padding: "16px 22px",
      }}
    >
      <div style={{ width: 200, flexShrink: 0 }}>
        <Chip name={name} fontSize={28} />
      </div>
      <div
        style={{
          flex: 1,
          height: 64,
          background: "rgba(255,255,255,0.05)",
          borderRadius: 12,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct * grow}%`,
            background: barBg,
            borderRadius: 12,
            boxShadow: `0 0 22px ${color}66`,
          }}
        />
      </div>
      <div style={{ width: 190, textAlign: "right", flexShrink: 0 }}>
        <AnimatedCounter
          value={value}
          startFrame={start}
          durationFrames={34}
          prefix={prefix}
          suffix={suffix}
          fontSize={52}
          fontWeight={800}
          color={color}
        />
      </div>
    </div>
  );
};

export const ShortVertical: React.FC<{ cue?: CueMap }> = ({ cue = CUE_VO }) => {
  const CUE = cue;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const intro = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const outro = interpolate(frame, [CUE.end - 12, CUE.end], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // hide chrome during the final CTA card so it reads as a clean end frame
  const chromeOpacity =
    Math.min(intro, outro) * (1 - rise(frame, CUE.cta, 14));

  // shared centered-beat wrapper styling
  const beat: React.CSSProperties = {
    padding: "0 70px",
    justifyContent: "center",
    alignItems: "center",
  };

  return (
    <AbsoluteFill style={{ fontFamily: FONTS.body }}>
      <AbsoluteFill style={{ opacity: Math.min(intro, outro) }}>
        <Background frame={frame} />
      </AbsoluteFill>

      <Chrome frame={frame} chromeOpacity={chromeOpacity} endFrame={CUE.end} />

      <AbsoluteFill style={{ opacity: Math.min(intro, outro) }}>
        {/* ===== BEAT 1 — HOOK ===== */}
        <AbsoluteFill
          style={{
            ...beat,
            opacity: fade(frame, 0, 10, CUE.premise - 14, CUE.premise + 6),
            gap: 70,
          }}
        >
          <AnimatedText
            text="Most chatbots forget what you told them 5 minutes ago."
            startFrame={CUE.hook}
            fontSize={66}
            fontWeight={800}
            color={COLORS.text}
            textAlign="center"
            mode="wordByWord"
            durationFrames={40}
            style={{ lineHeight: 1.15 }}
          />
          <div
            style={{
              width: "100%",
              display: "flex",
              flexDirection: "column",
              gap: 22,
            }}
          >
            {(
              [
                { t: "My dog's name is Baxter.", who: "user", at: CUE.hook + 30 },
                { t: "I'm allergic to shellfish.", who: "user", at: CUE.hook + 50 },
                { kind: "divider", t: "50 turns later", at: CUE.hook + 74 },
                { t: "What's my dog's name?", who: "user", at: CUE.hook + 92 },
                { t: "I don't have that information.", who: "bot", at: CUE.hook + 112 },
              ] as Array<{
                t: string;
                who?: "user" | "bot";
                kind?: "divider";
                at: number;
              }>
            ).map((m, i) => {
              if (m.kind === "divider") {
                return (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 18,
                      margin: "6px 0",
                      opacity: rise(frame, m.at, 10),
                    }}
                  >
                    <div
                      style={{
                        flex: 1,
                        height: 1,
                        background: `linear-gradient(90deg, transparent, ${COLORS.border})`,
                      }}
                    />
                    <span
                      style={{
                        fontFamily: FONTS.mono,
                        fontSize: 26,
                        letterSpacing: 2,
                        color: COLORS.textMuted,
                        whiteSpace: "nowrap",
                      }}
                    >
                      ⋯ {m.t} ⋯
                    </span>
                    <div
                      style={{
                        flex: 1,
                        height: 1,
                        background: `linear-gradient(90deg, ${COLORS.border}, transparent)`,
                      }}
                    />
                  </div>
                );
              }
              return (
                <div
                  key={i}
                  style={{
                    alignSelf: m.who === "user" ? "flex-end" : "flex-start",
                    maxWidth: "82%",
                    opacity: rise(frame, m.at, 10),
                    transform: `translateY(${interpolate(
                      frame,
                      [m.at, m.at + 10],
                      [14, 0],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    )}px)`,
                    background:
                      m.who === "user"
                        ? "rgba(0,212,255,0.12)"
                        : "rgba(255,68,68,0.12)",
                    border: `1px solid ${
                      m.who === "user" ? COLORS.accent : COLORS.danger
                    }55`,
                    color: COLORS.text,
                    borderRadius: 22,
                    borderBottomRightRadius: m.who === "user" ? 6 : 22,
                    borderBottomLeftRadius: m.who === "bot" ? 6 : 22,
                    padding: "20px 26px",
                    fontSize: 36,
                    fontWeight: 500,
                  }}
                >
                  {m.t}
                </div>
              );
            })}
          </div>
        </AbsoluteFill>

        {/* ===== BEAT 2 — THE TEST ===== */}
        <AbsoluteFill
          style={{
            ...beat,
            opacity: fade(frame, CUE.premise, CUE.premise + 14, CUE.recall - 14, CUE.recall + 6),
            gap: 64,
          }}
        >
          <AnimatedText
            text="So we benchmarked 4 ways to give an AI agent memory."
            startFrame={CUE.premise + 6}
            fontSize={60}
            fontWeight={800}
            textAlign="center"
            mode="wordByWord"
            durationFrames={36}
            style={{ lineHeight: 1.15 }}
          />
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 22,
              justifyContent: "center",
            }}
          >
            {["buffer", "summary", "qdrant", "pgvector"].map((b, i) => (
              <div
                key={b}
                style={{
                  opacity: rise(frame, CUE.premise + 30 + i * 10, 15),
                  transform: `scale(${interpolate(
                    frame,
                    [CUE.premise + 30 + i * 10, CUE.premise + 45 + i * 10],
                    [0.8, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  )})`,
                }}
              >
                <Chip name={b} fontSize={40} />
              </div>
            ))}
          </div>
          <div
            style={{
              display: "flex",
              gap: 18,
              flexWrap: "wrap",
              justifyContent: "center",
              opacity: rise(frame, CUE.premise + 70, 20),
            }}
          >
            {["50 turns", "10 planted facts", "1,000 LLM calls"].map((s) => (
              <span
                key={s}
                style={{
                  fontFamily: FONTS.mono,
                  fontSize: 30,
                  color: COLORS.textMuted,
                  border: `1px solid ${COLORS.border}`,
                  background: COLORS.bgCard,
                  borderRadius: 999,
                  padding: "10px 24px",
                }}
              >
                {s}
              </span>
            ))}
          </div>
        </AbsoluteFill>

        {/* ===== BEAT 3 — RECALL ===== */}
        <AbsoluteFill
          style={{
            ...beat,
            opacity: fade(frame, CUE.recall, CUE.recall + 14, CUE.cost - 14, CUE.cost + 6),
            gap: 56,
          }}
        >
          <AnimatedText
            text="Recall @ turn 50"
            startFrame={CUE.recall + 4}
            fontSize={58}
            fontWeight={800}
            textAlign="center"
            mode="wordByWord"
            durationFrames={24}
          />
          <div
            style={{
              width: "100%",
              display: "flex",
              flexDirection: "column",
              gap: 24,
            }}
          >
            {RECALL.map((r) => {
              const start =
                r.b === "buffer"
                  ? CUE.recallBuffer
                  : r.b === "summary"
                  ? CUE.recallSummary
                  : CUE.recallVector;
              return (
                <MetricRow
                  key={r.b}
                  name={r.b}
                  frame={frame}
                  fps={fps}
                  start={start}
                  pct={r.v}
                  value={r.v}
                  suffix="%"
                  highlight={r.b === "summary"}
                />
              );
            })}
          </div>
          <div style={{ opacity: rise(frame, CUE.recallTag, 14) }}>
            <AnimatedText
              text="Summary remembered less than half."
              startFrame={CUE.recallTag}
              fontSize={48}
              fontWeight={800}
              color={COLORS.danger}
              glow
              glowColor={COLORS.dangerGlow}
              textAlign="center"
              mode="wordByWord"
              durationFrames={30}
            />
          </div>
        </AbsoluteFill>

        {/* ===== BEAT 4 — COST ===== */}
        <AbsoluteFill
          style={{
            ...beat,
            opacity: fade(frame, CUE.cost, CUE.cost + 14, CUE.takeaway - 14, CUE.takeaway + 6),
            gap: 56,
          }}
        >
          <AnimatedText
            text="Cost per 1,000 conversations"
            startFrame={CUE.cost + 4}
            fontSize={54}
            fontWeight={800}
            textAlign="center"
            mode="wordByWord"
            durationFrames={24}
          />
          <div
            style={{
              width: "100%",
              display: "flex",
              flexDirection: "column",
              gap: 24,
            }}
          >
            {COST.map((c, i) => (
              <MetricRow
                key={c.b}
                name={c.b}
                frame={frame}
                fps={fps}
                start={CUE.cost + 30 + i * 16}
                pct={(c.v / 4303) * 100}
                value={c.v}
                prefix="$"
              />
            ))}
          </div>
          <div style={{ opacity: rise(frame, CUE.cost10x, 14) }}>
            <AnimatedText
              text="Same recall. ~1/10th the cost."
              startFrame={CUE.cost10x}
              fontSize={54}
              fontWeight={800}
              color={COLORS.neonGreen}
              glow
              glowColor="rgba(0,255,136,0.3)"
              textAlign="center"
              mode="wordByWord"
              durationFrames={30}
            />
          </div>
        </AbsoluteFill>

        {/* ===== BEAT 5 — TAKEAWAY ===== */}
        <AbsoluteFill
          style={{
            ...beat,
            opacity: fade(frame, CUE.takeaway, CUE.takeaway + 14, CUE.cta - 14, CUE.cta + 6),
            gap: 36,
          }}
        >
          {[
            { t: "✓  Vector memory wins", c: COLORS.neonGreen },
            { t: "✗  Summary: worst of all worlds", c: COLORS.danger },
            { t: "Run PostgreSQL? pgvector is basically free.", c: COLORS.text },
          ].map((row, i) => (
            <div
              key={i}
              style={{
                width: "100%",
                opacity: rise(frame, CUE.takeaway + 10 + i * 22, 20),
                transform: `translateY(${interpolate(
                  frame,
                  [CUE.takeaway + 10 + i * 22, CUE.takeaway + 30 + i * 22],
                  [20, 0],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                )}px)`,
                background: COLORS.bgCard,
                border: `1px solid ${row.c}55`,
                borderLeft: `6px solid ${row.c}`,
                borderRadius: 20,
                padding: "32px 38px",
                fontSize: 48,
                fontWeight: 700,
                color: row.c,
                textAlign: "center",
              }}
            >
              {row.t}
            </div>
          ))}
        </AbsoluteFill>

        {/* ===== BEAT 6 — CTA + BRAND (clean end card) ===== */}
        <AbsoluteFill
          style={{
            opacity: rise(frame, CUE.cta, 14),
            justifyContent: "center",
            alignItems: "center",
            padding: "0 80px",
            gap: 46,
          }}
        >
          <AnimatedText
            text="Don't guess. Measure."
            startFrame={CUE.cta + 4}
            fontSize={88}
            fontWeight={900}
            color={COLORS.text}
            glow
            glowColor={COLORS.accentGlow}
            textAlign="center"
            mode="wordByWord"
            durationFrames={26}
          />
          {/* CTA text — not a button; the actual link lives in the post */}
          <div
            style={{
              opacity: rise(frame, CUE.cta + 30, 16),
              transform: `translateY(${interpolate(
                frame,
                [CUE.cta + 30, CUE.cta + 46],
                [14, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              )}px)`,
              fontSize: 44,
              fontWeight: 700,
              color: COLORS.text,
              textAlign: "center",
            }}
          >
            Full breakdown linked in the post 👇
          </div>
          {/* handle */}
          <div
            style={{
              opacity: rise(frame, CUE.cta + 50, 16),
              marginTop: 10,
            }}
          >
            <span
              style={{
                fontFamily: FONTS.mono,
                fontSize: 40,
                fontWeight: 700,
                color: COLORS.accent,
              }}
            >
              @digitalocean
            </span>
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Tightened, music-only cut (~28s) — same visuals, gaps removed.
export const ShortVerticalTight: React.FC = () => <ShortVertical cue={CUE_TIGHT} />;
