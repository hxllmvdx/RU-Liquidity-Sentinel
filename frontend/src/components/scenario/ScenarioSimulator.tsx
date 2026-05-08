import { ScenarioResult } from "./ScenarioResult";
import { ScenarioSlider } from "./ScenarioSlider";

export function ScenarioSimulator() {
  return (
    <div className="grid gap-4">
      <ScenarioSlider />
      <ScenarioResult />
    </div>
  );
}
