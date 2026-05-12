import { cn } from "@/shared/lib/cn";
import { STATUS_LABELS, STATUS_STYLES } from "@/shared/lib/status";
import type { Status } from "@/shared/types/common";

export function StatusBadge({ status }: { status: Status }) {
  return <span className={cn("inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold", STATUS_STYLES[status])}>{STATUS_LABELS[status]}</span>;
}
