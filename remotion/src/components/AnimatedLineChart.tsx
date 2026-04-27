import { interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";

type Series = {
  label: string;
  data: number[];
  color?: string;
};

type Props = {
  series: Series[];
  startFrame?: number;
  drawDuration?: number;
  chartWidth?: number;
  chartHeight?: number;
  xLabels?: string[];
  yMax?: number;
  yLabel?: string;
  xLabel?: string;
  style?: React.CSSProperties;
};

export const AnimatedLineChart: React.FC<Props> = ({
  series,
  startFrame = 0,
  drawDuration = 90,
  chartWidth = 1200,
  chartHeight = 500,
  xLabels,
  yMax: yMaxProp,
  yLabel,
  xLabel,
  style,
}) => {
  const frame = useCurrentFrame();
  const relFrame = frame - startFrame;

  if (relFrame < 0) return null;

  const pad = { top: 20, right: 40, bottom: 60, left: 80 };
  const w = chartWidth - pad.left - pad.right;
  const h = chartHeight - pad.top - pad.bottom;

  const allValues = series.flatMap((s) => s.data);
  const yMax = yMaxProp ?? Math.max(...allValues) * 1.1;

  const toX = (i: number, total: number) => pad.left + (i / (total - 1)) * w;
  const toY = (v: number) => pad.top + h - (v / yMax) * h;

  const chartOpacity = interpolate(relFrame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ position: "relative", ...style }}>
      <svg width={chartWidth} height={chartHeight} style={{ opacity: chartOpacity }}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct) => (
          <line
            key={pct}
            x1={pad.left}
            y1={toY(yMax * pct)}
            x2={chartWidth - pad.right}
            y2={toY(yMax * pct)}
            stroke={COLORS.border}
            strokeWidth={1}
          />
        ))}

        {/* Axes */}
        <line
          x1={pad.left}
          y1={pad.top}
          x2={pad.left}
          y2={pad.top + h}
          stroke={COLORS.textDim}
          strokeWidth={1}
        />
        <line
          x1={pad.left}
          y1={pad.top + h}
          x2={chartWidth - pad.right}
          y2={pad.top + h}
          stroke={COLORS.textDim}
          strokeWidth={1}
        />

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct) => (
          <text
            key={pct}
            x={pad.left - 10}
            y={toY(yMax * pct) + 4}
            textAnchor="end"
            fill={COLORS.textMuted}
            fontFamily={FONTS.mono}
            fontSize={14}
          >
            {(yMax * pct).toFixed(0)}
          </text>
        ))}

        {/* X-axis labels */}
        {xLabels &&
          xLabels.map((label, i) => (
            <text
              key={i}
              x={toX(i, xLabels.length)}
              y={pad.top + h + 30}
              textAnchor="middle"
              fill={COLORS.textMuted}
              fontFamily={FONTS.mono}
              fontSize={14}
            >
              {label}
            </text>
          ))}

        {/* Series lines */}
        {series.map((s, si) => {
          const delay = si * 10;
          const progress = interpolate(
            relFrame - delay,
            [0, drawDuration],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          const total = s.data.length;
          const visibleCount = Math.floor(progress * total);
          const color = s.color ?? BACKEND_COLORS[s.label] ?? COLORS.accent;

          const points: string[] = [];
          for (let i = 0; i <= visibleCount && i < total; i++) {
            points.push(`${toX(i, total)},${toY(s.data[i])}`);
          }

          if (visibleCount < total - 1) {
            const frac = progress * total - visibleCount;
            const x =
              toX(visibleCount, total) +
              frac * (toX(visibleCount + 1, total) - toX(visibleCount, total));
            const y =
              toY(s.data[visibleCount]) +
              frac *
                (toY(s.data[Math.min(visibleCount + 1, total - 1)]) -
                  toY(s.data[visibleCount]));
            points.push(`${x},${y}`);
          }

          return (
            <g key={si}>
              <polyline
                points={points.join(" ")}
                fill="none"
                stroke={color}
                strokeWidth={3}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {/* Glow */}
              <polyline
                points={points.join(" ")}
                fill="none"
                stroke={color}
                strokeWidth={8}
                strokeLinejoin="round"
                strokeLinecap="round"
                opacity={0.2}
              />
            </g>
          );
        })}

        {/* Legend */}
        {series.map((s, i) => {
          const color = s.color ?? BACKEND_COLORS[s.label] ?? COLORS.accent;
          const lx = chartWidth - pad.right - 160;
          const ly = pad.top + 20 + i * 28;
          return (
            <g key={i}>
              <rect x={lx} y={ly - 6} width={20} height={4} rx={2} fill={color} />
              <text
                x={lx + 28}
                y={ly}
                fill={COLORS.text}
                fontFamily={FONTS.mono}
                fontSize={15}
              >
                {s.label}
              </text>
            </g>
          );
        })}

        {/* Axis labels */}
        {yLabel && (
          <text
            x={20}
            y={chartHeight / 2}
            fill={COLORS.textMuted}
            fontFamily={FONTS.body}
            fontSize={16}
            textAnchor="middle"
            transform={`rotate(-90, 20, ${chartHeight / 2})`}
          >
            {yLabel}
          </text>
        )}
        {xLabel && (
          <text
            x={chartWidth / 2}
            y={chartHeight - 8}
            fill={COLORS.textMuted}
            fontFamily={FONTS.body}
            fontSize={16}
            textAnchor="middle"
          >
            {xLabel}
          </text>
        )}
      </svg>
    </div>
  );
};
