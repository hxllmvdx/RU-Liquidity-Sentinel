"use client";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { ForecastChart } from "@/features/forecast/components/ForecastChart";
import { ForecastOverview } from "@/features/forecast/components/ForecastOverview";
import { ForecastTable } from "@/features/forecast/components/ForecastTable";
import { useForecast } from "@/features/forecast/hooks/useForecast";

export function ForecastScreen() {
  const { dashboardQuery, historyQuery } = useForecast();

  if (dashboardQuery.isLoading || historyQuery.isLoading) {
    return <LoadingState label="Loading forecast..." />;
  }

  if (dashboardQuery.error || historyQuery.error || !dashboardQuery.data || !historyQuery.data) {
    return (
      <ErrorState
        message={(dashboardQuery.error as Error)?.message ?? (historyQuery.error as Error)?.message ?? "Forecast data is unavailable."}
        onRetry={() => {
          void dashboardQuery.refetch();
          void historyQuery.refetch();
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Forecast workspace" description="Короткий прогноз LSI на горизонтах 1d, 3d и 7d. Используйте этот экран как early warning, а не как утверждение о будущем факте." />
      <ForecastOverview forecast={dashboardQuery.data.forecast} />
      <ForecastChart forecast={dashboardQuery.data.forecast} history={historyQuery.data.points} />
      <ForecastTable forecast={dashboardQuery.data.forecast} />
    </div>
  );
}
