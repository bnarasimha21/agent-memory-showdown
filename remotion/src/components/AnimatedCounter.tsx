import { interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "../styles/theme";

type Props = {
  value: number;
  startFrame?: number;
  durationFrames?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  fontSize?: number;
  color?: string;
  fontFamily?: string;
  fontWeight?: number;
  formatCommas?: boolean;
  style?: React.CSSProperties;
};

export const AnimatedCounter: React.FC<Props> = ({
  value,
  startFrame = 0,
  durationFrames = 40,
  prefix = "",
  suffix = "",
  decimals = 0,
  fontSize = 48,
  color = COLORS.text,
  fontFamily = FONTS.mono,
  fontWeight = 700,
  formatCommas = true,
  style,
}) => {
  const frame = useCurrentFrame();
  const relFrame = frame - startFrame;

  if (relFrame < 0) return null;

  const progress = interpolate(relFrame, [0, durationFrames], [0, 1], {
    extrapolateRight: "clamp",
  });

  const eased = 1 - Math.pow(1 - progress, 3);
  const current = eased * value;
  const formatted = formatCommas
    ? current.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ",")
    : current.toFixed(decimals);

  const opacity = interpolate(relFrame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <span
      style={{
        fontSize,
        fontFamily,
        fontWeight,
        color,
        opacity,
        ...style,
      }}
    >
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
};
