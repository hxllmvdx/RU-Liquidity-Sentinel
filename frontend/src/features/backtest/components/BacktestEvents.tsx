import { SectionCard } from "@/components/common/SectionCard";
import type { ModuleContribution } from "@/shared/types/dashboard";

export function BacktestEvents({
  contributions,
  conclusion
}: {
  contributions: ModuleContribution[];
  conclusion: string;
}) {
  return (
    <SectionCard title="Средние вклады и вывод" description="Средние вклады модулей помогают понять структуру стресса в выбранном эпизоде.">
      <div className="space-y-3">
        {contributions.map((contribution) => (
          <div className="flex items-center justify-between rounded-xl border bg-slate-50 px-4 py-3 text-sm" key={contribution.module_id}>
            <span>{contribution.module_name}</span>
            <span className="font-semibold">{contribution.contribution_percent.toFixed(1)}%</span>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm leading-6 text-muted">{conclusion}</p>
    </SectionCard>
  );
}
