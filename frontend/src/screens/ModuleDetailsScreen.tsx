"use client";

import { ActiveFlagsList } from "@/features/dashboard/components/ActiveFlagsList";
import { ModuleDetailsHeader } from "@/features/modules/components/ModuleDetailsHeader";
import { ModuleSignalsChart } from "@/features/modules/components/ModuleSignalsChart";
import { ModuleSignalsTable } from "@/features/modules/components/ModuleSignalsTable";
import { useModuleSignals } from "@/features/modules/hooks/useModuleSignals";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { MODULE_IDS } from "@/shared/config/modules";
import type { ModuleId } from "@/shared/types/common";

export function ModuleDetailsScreen({ id }: { id: string }) {
  const isValid = MODULE_IDS.includes(id as ModuleId);
  const moduleId = (isValid ? id : "M1_RESERVES") as ModuleId;
  const query = useModuleSignals(moduleId, "2022-02-01", "2022-03-31", isValid);

  if (!isValid) {
    return <ErrorState message={`Module id "${id}" is invalid.`} />;
  }

  if (query.isLoading) {
    return <LoadingState label="Loading module signals..." />;
  }

  if (query.error || !query.data) {
    return <ErrorState message={(query.error as Error)?.message ?? "Module signals are unavailable."} onRetry={() => void query.refetch()} />;
  }

  return (
    <div className="space-y-6">
      <ModuleDetailsHeader moduleId={moduleId} />
      {query.data.signals.length ? (
        <div className="grid gap-6">
          <ModuleSignalsChart signals={query.data.signals} />
          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <ModuleSignalsTable signals={query.data.signals} />
            <ActiveFlagsList flags={query.data.active_flags} />
          </div>
        </div>
      ) : (
        <EmptyState title="No signals found" description="Для выбранного диапазона нет сигналов. Попробуйте другой период или проверьте наличие данных в backend." />
      )}
    </div>
  );
}
