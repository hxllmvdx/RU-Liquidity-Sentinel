"use client";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { ModuleCard } from "@/features/modules/components/ModuleCard";
import { useModules } from "@/features/modules/hooks/useModules";

export function ModulesScreen() {
  const { modulesQuery, snapshotQuery } = useModules();

  if (modulesQuery.isLoading || snapshotQuery.isLoading) {
    return <LoadingState label="Loading modules snapshot..." />;
  }

  if (modulesQuery.error || snapshotQuery.error || !modulesQuery.data || !snapshotQuery.data) {
    return (
      <ErrorState
        message={(modulesQuery.error as Error)?.message ?? (snapshotQuery.error as Error)?.message ?? "Modules are unavailable."}
        onRetry={() => {
          void modulesQuery.refetch();
          void snapshotQuery.refetch();
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Modules overview" description="Карточки пяти основных модулей стресс-мониторинга: от резервов и репо до налоговой недели и потоков казначейства." />
      <div className="grid gap-6 xl:grid-cols-2">
        {modulesQuery.data.modules.map((module) => (
          <ModuleCard
            key={module.module_id}
            module={module}
            snapshot={snapshotQuery.data.modules.find((item) => item.module_id === module.module_id)}
          />
        ))}
      </div>
    </div>
  );
}
