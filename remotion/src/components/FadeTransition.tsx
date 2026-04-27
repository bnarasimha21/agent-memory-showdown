import { interpolate, useCurrentFrame } from "remotion";

type Props = {
  children: React.ReactNode;
  durationFrames: number;
  fadeInFrames?: number;
  fadeOutFrames?: number;
};

export const FadeTransition: React.FC<Props> = ({
  children,
  durationFrames,
  fadeInFrames = 15,
  fadeOutFrames = 15,
}) => {
  const frame = useCurrentFrame();

  let opacity: number;
  if (fadeOutFrames === 0) {
    opacity = interpolate(frame, [0, fadeInFrames], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (fadeInFrames === 0) {
    opacity = interpolate(
      frame,
      [durationFrames - fadeOutFrames, durationFrames],
      [1, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else {
    opacity = interpolate(
      frame,
      [0, fadeInFrames, durationFrames - fadeOutFrames, durationFrames],
      [0, 1, 1, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  }

  return <div style={{ opacity, width: "100%", height: "100%" }}>{children}</div>;
};
