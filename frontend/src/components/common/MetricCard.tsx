import { StatusBadge } from "@/features/dashboard/components/StatusBadge";
import type { Status } from "@/shared/types/common";

export function MetricCard({
  label,
  value,
  hint,
  status
}: {
  label: string;
  value: string;
  hint?: string;
  status?: Status;
}) {
  return (
    <div className="rounded-2xl border bg-slate-50/70 p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-muted">{label}</p>
        {status ? <StatusBadge status={status} /> : null}
      </div>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
      {hint ? <p className="mt-2 text-sm text-muted">{hint}</p> : null}
    </div>
  );
}
