import { MetricCard } from "@/components/common/MetricCard";
import { StatusBadge } from "@/features/dashboard/components/StatusBadge";
import { cn } from "@/shared/lib/cn";
import { formatDateLabel, formatLsi } from "@/shared/lib/format";
import { getStatusTone } from "@/shared/lib/status";
import type { DashboardResponse } from "@/shared/types/dashboard";

export function LsiHeroCard({ dashboard }: { dashboard: DashboardResponse }) {
  const progress = Math.min(Math.max(dashboard.lsi, 0), 100);

  return (
    <div className={cn("rounded-[28px] border-2 bg-white p-6 shadow-panel", getStatusTone(dashboard.status))}>
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">Current LSI</p>
            <StatusBadge status={dashboard.status} />
          </div>
          <p className="mt-4 text-6xl font-semibold leading-none">{formatLsi(dashboard.lsi)}</p>
          <p className="mt-3 max-w-xl text-sm leading-6 text-muted">
            Индекс отражает совокупный стресс ликвидности рублёвого денежного рынка. Оранжевые элементы подсвечивают зоны раннего внимания, не перегружая основной синий визуальный язык.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:w-[420px]">
          <MetricCard label="Calculation date" value={formatDateLabel(dashboard.date)} />
          <MetricCard label="Confidence" value={`${Math.round(dashboard.confidence * 100)}%`} />
        </div>
      </div>
      <div className="mt-6 space-y-2">
        <div className="flex items-center justify-between text-xs font-medium uppercase tracking-[0.18em] text-muted">
          <span>LSI gauge</span>
          <span>{formatLsi(dashboard.lsi)}/100</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-primary-soft">
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${progress}%` }} />
        </div>
      </div>
    </div>
  );
}
