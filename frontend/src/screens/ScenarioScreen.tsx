import { PageHeader } from "@/components/common/PageHeader";
import { ScenarioForm } from "@/features/scenario/components/ScenarioForm";

export function ScenarioScreen() {
  return (
    <div className="space-y-6">
      <PageHeader title="Сценарный симулятор" description="Слой what-if для проверки чувствительности индекса к шокам по отдельным модулям и источникам ликвидностного давления." />
      <ScenarioForm />
    </div>
  );
}
