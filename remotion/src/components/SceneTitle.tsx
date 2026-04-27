import { interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "../styles/theme";

type Props = {
  title: string;
  subtitle?: string;
  startFrame?: number;
  style?: React.CSSProperties;
};

export const SceneTitle: React.FC<Props> = ({
  title,
  subtitle,
  startFrame = 0,
  style,
}) => {
  const frame = useCurrentFrame();
  const relFrame = frame - startFrame;

  if (relFrame < 0) return null;

  const opacity = interpolate(relFrame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  const y = interpolate(relFrame, [0, 20], [-20, 0], {
    extrapolateRight: "clamp",
  });
  const lineWidth = interpolate(relFrame, [10, 35], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ opacity, transform: `translateY(${y}px)`, ...style }}>
      <h1
        style={{
          fontFamily: FONTS.body,
          fontSize: 52,
          fontWeight: 700,
          color: COLORS.text,
          margin: 0,
          letterSpacing: -1,
        }}
      >
        {title}
      </h1>
      <div
        style={{
          width: `${lineWidth}%`,
          height: 3,
          background: `linear-gradient(90deg, ${COLORS.accent}, transparent)`,
          marginTop: 12,
          borderRadius: 2,
        }}
      />
      {subtitle && (
        <p
          style={{
            fontFamily: FONTS.body,
            fontSize: 24,
            color: COLORS.textMuted,
            marginTop: 16,
            fontWeight: 400,
          }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
};
