import { interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "../styles/theme";

type Props = {
  text: string;
  startFrame?: number;
  durationFrames?: number;
  mode?: "typewriter" | "fadeIn" | "wordByWord";
  fontSize?: number;
  color?: string;
  glow?: boolean;
  glowColor?: string;
  fontFamily?: string;
  fontWeight?: number;
  lineHeight?: number;
  textAlign?: React.CSSProperties["textAlign"];
  style?: React.CSSProperties;
};

export const AnimatedText: React.FC<Props> = ({
  text,
  startFrame = 0,
  durationFrames = 30,
  mode = "fadeIn",
  fontSize = 32,
  color = COLORS.text,
  glow = false,
  glowColor = COLORS.accentGlow,
  fontFamily = FONTS.body,
  fontWeight = 400,
  lineHeight = 1.5,
  textAlign = "left",
  style,
}) => {
  const frame = useCurrentFrame();
  const relFrame = frame - startFrame;

  if (relFrame < 0) return null;

  if (mode === "typewriter") {
    const charCount = Math.floor(
      interpolate(relFrame, [0, durationFrames], [0, text.length], {
        extrapolateRight: "clamp",
      })
    );
    const displayed = text.slice(0, charCount);
    const showCursor = relFrame < durationFrames + 15 && relFrame % 15 < 10;

    return (
      <div
        style={{
          fontSize,
          fontFamily: FONTS.mono,
          color,
          fontWeight,
          lineHeight,
          textAlign,
          textShadow: glow ? `0 0 20px ${glowColor}` : undefined,
          whiteSpace: "pre-wrap",
          ...style,
        }}
      >
        {displayed}
        {showCursor && (
          <span style={{ color: COLORS.accent, fontWeight: 100 }}>▌</span>
        )}
      </div>
    );
  }

  if (mode === "wordByWord") {
    // Smooth whole-line fade + subtle scale.
    // (Kept the "wordByWord" mode name so existing scenes auto-upgrade,
    // but this now renders the entire line as one polished reveal instead
    // of jittery per-word staggering.)
    const revealDuration = Math.min(20, Math.max(12, durationFrames / 4));
    const opacity = interpolate(
      relFrame,
      [0, revealDuration],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
    const scale = interpolate(
      relFrame,
      [0, revealDuration],
      [0.97, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );

    return (
      <div
        style={{
          fontSize,
          fontFamily,
          color,
          fontWeight,
          lineHeight,
          textAlign,
          opacity,
          transform: `scale(${scale})`,
          transformOrigin: "center",
          textShadow: glow ? `0 0 20px ${glowColor}` : undefined,
          ...style,
        }}
      >
        {text}
      </div>
    );
  }

  const opacity = interpolate(relFrame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  const y = interpolate(relFrame, [0, 20], [20, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        fontSize,
        fontFamily,
        color,
        fontWeight,
        lineHeight,
        textAlign,
        opacity,
        transform: `translateY(${y}px)`,
        textShadow: glow ? `0 0 20px ${glowColor}` : undefined,
        ...style,
      }}
    >
      {text}
    </div>
  );
};
