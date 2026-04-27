import { BACKEND_COLORS, BACKEND_GLOWS } from "../styles/theme";
import { FONTS } from "../styles/theme";

type Props = {
  name: string;
  fontSize?: number;
  style?: React.CSSProperties;
};

export const BackendBadge: React.FC<Props> = ({
  name,
  fontSize = 16,
  style,
}) => {
  const color = BACKEND_COLORS[name] ?? "#888";
  const glow = BACKEND_GLOWS[name] ?? "transparent";

  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 14px",
        borderRadius: 20,
        background: `${color}22`,
        border: `1px solid ${color}66`,
        color,
        fontFamily: FONTS.mono,
        fontSize,
        fontWeight: 600,
        boxShadow: `0 0 12px ${glow}`,
        ...style,
      }}
    >
      {name}
    </span>
  );
};
