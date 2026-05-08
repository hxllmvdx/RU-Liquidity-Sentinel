import { MetricCard } from "@/components/common/MetricCard";
import { formatMetricValue } from "@/shared/lib/format";
import type { BacktestMetric } from "@/shared/types/backtest";

export function BacktestMetrics({ metrics }: { metrics: BacktestMetric[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {metrics.map((metric) => (
        <MetricCard key={metric.name} label={metric.name} value={formatMetricValue(metric.value, metric.unit)} />
      ))}
    </div>
  );
}
