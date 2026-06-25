import { Composition, Sequence } from "remotion";
import { Scene1_Hook } from "./scenes/Scene1_Hook";
import { Scene2_Problem } from "./scenes/Scene2_Problem";
import { Scene3_Setup } from "./scenes/Scene3_Setup";
import { Scene4_Recall } from "./scenes/Scene4_Recall";
import { Scene5_Latency } from "./scenes/Scene5_Latency";
import { Scene6_Cost } from "./scenes/Scene6_Cost";
import { Scene7_QdrantVsPgvector } from "./scenes/Scene7_QdrantVsPgvector";
import { Scene8_Surprise } from "./scenes/Scene8_Surprise";
import { Scene9_Recommendations } from "./scenes/Scene9_Recommendations";
import { Scene10_Closing } from "./scenes/Scene10_Closing";
import { ShortVertical, ShortVerticalTight, CUE_TIGHT } from "./ShortVertical";
import { FPS, WIDTH, HEIGHT } from "./styles/theme";

const SCENES = [
  { id: "Scene1-Hook", component: Scene1_Hook, duration: 718 },
  { id: "Scene2-Problem", component: Scene2_Problem, duration: 1962 },
  { id: "Scene3-Setup", component: Scene3_Setup, duration: 2051 },
  { id: "Scene4-Recall", component: Scene4_Recall, duration: 2106 },
  { id: "Scene5-Latency", component: Scene5_Latency, duration: 1981 },
  { id: "Scene6-Cost", component: Scene6_Cost, duration: 1557 },
  { id: "Scene7-QdrantVsPgvector", component: Scene7_QdrantVsPgvector, duration: 1406 },
  { id: "Scene8-Surprise", component: Scene8_Surprise, duration: 1175 },
  { id: "Scene9-Recommendations", component: Scene9_Recommendations, duration: 1498 },
  { id: "Scene10-Closing", component: Scene10_Closing, duration: 740 },
] as const;

const TOTAL_DURATION = SCENES.reduce((sum, s) => sum + s.duration, 0);

const FullVideo: React.FC = () => {
  let offset = 0;
  return (
    <>
      {SCENES.map((scene) => {
        const from = offset;
        offset += scene.duration;
        const SceneComponent = scene.component;
        return (
          <Sequence key={scene.id} from={from} durationInFrames={scene.duration} name={scene.id}>
            <SceneComponent />
          </Sequence>
        );
      })}
    </>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Full video composition */}
      <Composition
        id="AgentMemoryShowdown"
        component={FullVideo}
        durationInFrames={TOTAL_DURATION}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />

      {/* 45s vertical short-form cut for X (1080x1920) */}
      <Composition
        id="ShortVertical"
        component={ShortVertical}
        durationInFrames={1350}
        fps={FPS}
        width={1080}
        height={1920}
      />

      {/* Tightened music-only cut (~28s) — gaps removed, no narration sync */}
      <Composition
        id="ShortVerticalTight"
        component={ShortVerticalTight}
        durationInFrames={CUE_TIGHT.end}
        fps={FPS}
        width={1080}
        height={1920}
      />

      {/* Individual scene compositions for preview/debugging */}
      {SCENES.map((scene) => {
        const SceneComponent = scene.component;
        return (
          <Composition
            key={scene.id}
            id={scene.id}
            component={SceneComponent}
            durationInFrames={scene.duration}
            fps={FPS}
            width={WIDTH}
            height={HEIGHT}
          />
        );
      })}
    </>
  );
};
