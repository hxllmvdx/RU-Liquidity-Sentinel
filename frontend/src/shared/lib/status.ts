import type { Status } from "@/shared/types/common";

export const STATUS_LABELS: Record<Status, string> = {
  green: "Green",
  yellow: "Yellow",
  red: "Red",
  unspecified: "Unspecified"
};

export const STATUS_STYLES: Record<Status, string> = {
  green: "border-success/20 bg-success/10 text-success",
  yellow: "border-caution/20 bg-accent/10 text-accent",
  red: "border-danger/20 bg-danger/10 text-danger",
  unspecified: "border-slate-200 bg-slate-100 text-slate-600"
};

export function getStatusTone(status: Status) {
  if (status === "red") return "border-danger";
  if (status === "yellow") return "border-accent";
  if (status === "green") return "border-success";
  return "border-border";
}
