import { MetricCard } from "@/components/common/MetricCard";
import { SectionCard } from "@/components/common/SectionCard";
import { formatLsi } from "@/shared/lib/format";
import type { ScenarioResponse } from "@/shared/types/scenario";

export function ScenarioResultCard({ result }: { result: ScenarioResponse }) {
  return (
    <SectionCard title="Scenario result" description="Сравнение базового и сценарного состояния после применения шоков.">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Base LSI" value={formatLsi(result.base_lsi)} status={result.base_status} />
        <MetricCard label="Scenario LSI" value={formatLsi(result.scenario_lsi)} status={result.scenario_status} />
        <MetricCard label="Delta LSI" value={formatLsi(result.delta_lsi)} />
      </div>
      <p className="mt-4 text-sm leading-6 text-muted">{result.explanation}</p>
    </SectionCard>
  );
}
