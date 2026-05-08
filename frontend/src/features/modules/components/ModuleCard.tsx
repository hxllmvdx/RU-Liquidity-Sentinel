import Link from "next/link";
import { SectionCard } from "@/components/common/SectionCard";
import { Button } from "@/components/ui/button";
import type { ModuleDefinition, ModuleSnapshot } from "@/shared/types/modules";

export function ModuleCard({
  module,
  snapshot
}: {
  module: ModuleDefinition;
  snapshot?: ModuleSnapshot;
}) {
  return (
    <SectionCard title={module.module_name} description={module.description}>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="rounded-full bg-primary-soft px-3 py-1 text-xs font-semibold text-primary">{module.module_id}</span>
          <span className="text-sm text-muted">Оценка {snapshot?.module_score?.toFixed(1) ?? "н/д"}</span>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted">Активные флаги</p>
          {snapshot?.active_flags?.length ? (
            snapshot.active_flags.map((flag) => (
              <div className="rounded-xl border bg-slate-50 px-3 py-2 text-sm" key={flag.flag_name}>
                {flag.flag_name}
              </div>
            ))
          ) : (
            <p className="text-sm text-muted">Для выбранного среза активных флагов нет.</p>
          )}
        </div>
        <Button asChild>
          <Link href={`/modules/${module.module_id}`}>Открыть модуль</Link>
        </Button>
      </div>
    </SectionCard>
  );
}
