import { MetricCard } from "@/components/common/MetricCard";
import { formatDateLabel, formatLsi } from "@/shared/lib/format";
import type { ForecastPoint } from "@/shared/types/dashboard";

export function ForecastOverview({ forecast }: { forecast: ForecastPoint[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {forecast.map((point) => (
        <MetricCard
          hint={`Целевая дата ${formatDateLabel(point.target_date)} | Уверенность ${Math.round(point.confidence * 100)}%`}
          key={point.horizon}
          label={`Прогноз ${point.horizon}`}
          status={point.status}
          value={formatLsi(point.lsi)}
        />
      ))}
    </div>
  );
}
