import { PageHeader } from "@/components/common/PageHeader";
import { ScenarioForm } from "@/features/scenario/components/ScenarioForm";

export function ScenarioScreen() {
  return (
    <div className="space-y-6">
      <PageHeader title="Scenario simulator" description="What-if слой для проверки чувствительности индекса к шокам по отдельным модулям и источникам ликвидностного давления." />
      <ScenarioForm />
    </div>
  );
}
