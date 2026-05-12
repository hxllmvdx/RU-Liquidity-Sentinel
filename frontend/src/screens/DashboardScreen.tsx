"use client";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { ActiveFlagsList } from "@/features/dashboard/components/ActiveFlagsList";
import { AutoCommentCard } from "@/features/dashboard/components/AutoCommentCard";
import { ConfidenceCard } from "@/features/dashboard/components/ConfidenceCard";
import { LsiHeroCard } from "@/features/dashboard/components/LsiHeroCard";
import { LsiHistoryChart } from "@/features/dashboard/components/LsiHistoryChart";
import { ModuleContributionChart } from "@/features/dashboard/components/ModuleContributionChart";
import { ShapDriversTable } from "@/features/dashboard/components/ShapDriversTable";
import { useDashboard } from "@/features/dashboard/hooks/useDashboard";

export function DashboardScreen() {
  const { dashboardQuery, historyQuery } = useDashboard();

  if (dashboardQuery.isLoading || historyQuery.isLoading) {
    return <LoadingState label="Загрузка среза дашборда..." />;
  }

  if (dashboardQuery.error || historyQuery.error || !dashboardQuery.data || !historyQuery.data) {
    return (
      <ErrorState
        message={(dashboardQuery.error as Error)?.message ?? (historyQuery.error as Error)?.message ?? "Данные дашборда недоступны."}
        onRetry={() => {
          void dashboardQuery.refetch();
          void historyQuery.refetch();
        }}
      />
    );
  }

  const dashboard = dashboardQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Дашборд стресса ликвидности"
        description="Главный монитор текущего состояния рублёвого денежного рынка: LSI, недельная динамика, вклад модулей, рассчитанные драйверы, активные флаги и автокомментарий аналитика."
      />
      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <LsiHeroCard dashboard={dashboard} />
        <ConfidenceCard confidence={dashboard.confidence} />
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <LsiHistoryChart points={historyQuery.data.points} />
        <ModuleContributionChart contributions={dashboard.contributions} />
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <ShapDriversTable shapValues={dashboard.shap_values} />
        <ActiveFlagsList flags={dashboard.active_flags} />
      </div>
      <AutoCommentCard comment={dashboard.auto_comment} />
    </div>
  );
}
