import { SectionCard } from "@/components/common/SectionCard";
import { StatusBadge } from "@/features/dashboard/components/StatusBadge";
import { formatDateLabel, formatLsi } from "@/shared/lib/format";
import type { ForecastPoint } from "@/shared/types/dashboard";

export function ForecastCards({ forecast }: { forecast: ForecastPoint[] }) {
  return (
    <SectionCard title="Forecast" description="Короткий горизонт предупреждения на 1d, 3d и 7d. Это сигнал раннего внимания, а не факт будущего события.">
      <div className="grid gap-4 md:grid-cols-3">
        {forecast.map((item) => (
          <div className="rounded-2xl border bg-slate-50 p-4" key={item.horizon}>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-primary">{item.horizon}</p>
              <StatusBadge status={item.status} />
            </div>
            <p className="mt-4 text-3xl font-semibold">{formatLsi(item.lsi)}</p>
            <p className="mt-2 text-sm text-muted">{formatDateLabel(item.target_date)}</p>
            <p className="mt-1 text-sm text-muted">Confidence {Math.round(item.confidence * 100)}%</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
