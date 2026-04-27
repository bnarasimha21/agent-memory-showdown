import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../styles/theme";

type Props = {
  children: React.ReactNode;
  startFrame?: number;
  width?: number | string;
  padding?: number;
  borderColor?: string;
  glowColor?: string;
  style?: React.CSSProperties;
};

export const GlassCard: React.FC<Props> = ({
  children,
  startFrame = 0,
  width = "auto",
  padding = 32,
  borderColor = COLORS.border,
  glowColor,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const relFrame = frame - startFrame;

  if (relFrame < 0) return null;

  const scale = spring({
    frame: relFrame,
    fps,
    config: { damping: 15, stiffness: 120, mass: 0.8 },
  });

  const opacity = interpolate(relFrame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width,
        padding,
        background: COLORS.bgCard,
        backdropFilter: "blur(20px)",
        border: `1px solid ${borderColor}`,
        borderRadius: 16,
        opacity,
        transform: `scale(${scale})`,
        boxShadow: glowColor
          ? `0 0 40px ${glowColor}, inset 0 0 40px rgba(0,0,0,0.3)`
          : "0 4px 30px rgba(0,0,0,0.3)",
        ...style,
      }}
    >
      {children}
    </div>
  );
};
