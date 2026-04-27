import { interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "../styles/theme";

type Props = {
  text: string;
  sender: "user" | "bot";
  startFrame?: number;
  typewriter?: boolean;
  typewriterDuration?: number;
  style?: React.CSSProperties;
};

export const ChatBubble: React.FC<Props> = ({
  text,
  sender,
  startFrame = 0,
  typewriter = false,
  typewriterDuration = 30,
  style,
}) => {
  const frame = useCurrentFrame();
  const relFrame = frame - startFrame;

  if (relFrame < 0) return null;

  const opacity = interpolate(relFrame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
  });
  const slideX = interpolate(relFrame, [0, 10], [sender === "user" ? 30 : -30, 0], {
    extrapolateRight: "clamp",
  });

  const displayText = typewriter
    ? text.slice(
        0,
        Math.floor(
          interpolate(relFrame, [0, typewriterDuration], [0, text.length], {
            extrapolateRight: "clamp",
          })
        )
      )
    : text;

  const isUser = sender === "user";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        opacity,
        transform: `translateX(${slideX}px)`,
        marginBottom: 12,
        ...style,
      }}
    >
      <div
        style={{
          maxWidth: 600,
          padding: "14px 20px",
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          background: isUser ? COLORS.accent + "22" : COLORS.bgCard,
          border: `1px solid ${isUser ? COLORS.accent + "44" : COLORS.border}`,
          color: COLORS.text,
          fontFamily: FONTS.body,
          fontSize: 22,
          lineHeight: 1.5,
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontFamily: FONTS.mono,
            color: isUser ? COLORS.accent : COLORS.textMuted,
            textTransform: "uppercase",
            letterSpacing: 1,
            display: "block",
            marginBottom: 6,
          }}
        >
          {isUser ? "You" : "AI Assistant"}
        </span>
        {displayText}
        {typewriter && relFrame < typewriterDuration + 15 && relFrame % 15 < 10 && (
          <span style={{ color: COLORS.accent }}>▌</span>
        )}
      </div>
    </div>
  );
};
