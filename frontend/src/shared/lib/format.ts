import { format } from "date-fns";

export function formatLsi(value?: number | null) {
  return value == null || Number.isNaN(value) ? "н/д" : value.toFixed(1);
}

export function formatPercent(value?: number | null) {
  if (value == null || Number.isNaN(value)) {
    return "н/д";
  }

  return `${(value * 100).toFixed(0)}%`;
}

export function formatContributionPercent(value?: number | null) {
  return value == null || Number.isNaN(value) ? "н/д" : `${value.toFixed(1)}%`;
}

export function formatDateLabel(value?: string | null) {
  if (!value) {
    return "н/д";
  }

  return format(new Date(value), "yyyy-MM-dd");
}

export function formatMetricValue(value: number | string, unit?: string) {
  return `${value}${unit ? ` ${unit}` : ""}`;
}
