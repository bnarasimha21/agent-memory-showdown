import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS, BACKEND_COLORS } from "../styles/theme";

type BarData = {
  label: string;
  value: number;
  displayValue?: string;
  color?: string;
};

type Props = {
  data: BarData[];
  startFrame?: number;
  maxValue?: number;
  barWidth?: number;
  chartHeight?: number;
  chartWidth?: number;
  showValues?: boolean;
  valuePrefix?: string;
  valueSuffix?: string;
  errorBars?: number[];
  style?: React.CSSProperties;
};

export const AnimatedBarChart: React.FC<Props> = ({
  data,
  startFrame = 0,
  maxValue: maxProp,
  barWidth = 120,
  chartHeight = 500,
  chartWidth = 900,
  showValues = true,
  valuePrefix = "",
  valueSuffix = "",
  errorBars,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const relFrame = frame - startFrame;

  if (relFrame < 0) return null;

  const maxVal = maxProp ?? Math.max(...data.map((d) => d.value)) * 1.15;
  const gap = (chartWidth - data.length * barWidth) / (data.length + 1);

  return (
    <div style={{ position: "relative", width: chartWidth, height: chartHeight + 80, ...style }}>
      {/* Y-axis line */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: 1,
          height: chartHeight,
          background: COLORS.border,
        }}
      />
      {/* X-axis line */}
      <div
        style={{
          position: "absolute",
          left: 0,
          bottom: 60,
          width: chartWidth,
          height: 1,
          background: COLORS.border,
        }}
      />

      {data.map((d, i) => {
        const barDelay = i * 8;
        const barProgress = spring({
          frame: Math.max(0, relFrame - barDelay),
          fps,
          config: { damping: 14, stiffness: 80, mass: 1 },
        });
        const barHeight = (d.value / maxVal) * chartHeight * barProgress;
        const x = gap + i * (barWidth + gap);
        const color = d.color ?? BACKEND_COLORS[d.label] ?? COLORS.accent;

        const valueOpacity = interpolate(
          relFrame,
          [barDelay + 15, barDelay + 25],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        return (
          <div key={i}>
            {/* Bar */}
            <div
              style={{
                position: "absolute",
                left: x,
                bottom: 61,
                width: barWidth,
                height: barHeight,
                background: `linear-gradient(180deg, ${color}, ${color}88)`,
                borderRadius: "6px 6px 0 0",
                boxShadow: `0 0 20px ${color}44`,
              }}
            />

            {/* Error bar */}
            {errorBars && errorBars[i] !== undefined && barProgress > 0.9 && (
              <>
                <div
                  style={{
                    position: "absolute",
                    left: x + barWidth / 2 - 1,
                    bottom: 61 + barHeight - (errorBars[i] / maxVal) * chartHeight,
                    width: 2,
                    height: (errorBars[i] / maxVal) * chartHeight * 2,
                    background: COLORS.text,
                    opacity: valueOpacity * 0.6,
                  }}
                />
                {[-1, 1].map((dir) => (
                  <div
                    key={dir}
                    style={{
                      position: "absolute",
                      left: x + barWidth / 2 - 8,
                      bottom:
                        61 +
                        barHeight +
                        (dir * errorBars[i] / maxVal) * chartHeight -
                        1,
                      width: 16,
                      height: 2,
                      background: COLORS.text,
                      opacity: valueOpacity * 0.6,
                    }}
                  />
                ))}
              </>
            )}

            {/* Value label */}
            {showValues && (
              <div
                style={{
                  position: "absolute",
                  left: x,
                  bottom: 61 + barHeight + 10,
                  width: barWidth,
                  textAlign: "center",
                  fontFamily: FONTS.mono,
                  fontSize: 30,
                  fontWeight: 800,
                  color,
                  opacity: valueOpacity,
                  textShadow: `0 0 14px ${color}55`,
                }}
              >
                {d.displayValue ?? `${valuePrefix}${d.value.toLocaleString()}${valueSuffix}`}
              </div>
            )}

            {/* Label */}
            <div
              style={{
                position: "absolute",
                left: x,
                bottom: 16,
                width: barWidth,
                textAlign: "center",
                fontFamily: FONTS.mono,
                fontSize: 24,
                fontWeight: 600,
                color: COLORS.text,
                opacity: interpolate(relFrame, [0, 15], [0, 1], {
                  extrapolateRight: "clamp",
                }),
              }}
            >
              {d.label}
            </div>
          </div>
        );
      })}
    </div>
  );
};
