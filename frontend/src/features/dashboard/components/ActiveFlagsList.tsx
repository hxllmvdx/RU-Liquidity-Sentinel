import { SectionCard } from "@/components/common/SectionCard";
import type { ActiveFlag } from "@/shared/types/dashboard";

export function ActiveFlagsList({ flags }: { flags: ActiveFlag[] }) {
  return (
    <SectionCard title="Активные флаги" description="Открытые флаги стресса по модулям с относительной силой сигнала.">
      <div className="space-y-3">
        {flags.map((flag) => (
          <div className="rounded-2xl border bg-slate-50 p-4" key={`${flag.module_id}-${flag.flag_name}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-semibold">{flag.flag_name}</p>
                <p className="text-sm text-muted">{flag.module_id}</p>
              </div>
              <span className="rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
                Сила {(flag.severity * 100).toFixed(0)}%
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted">{flag.description}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
