import type { ModuleContribution } from "@/shared/types/dashboard";
import type { LsiHistoryPoint } from "@/shared/types/lsi";

export interface BacktestMetric {
  name: string;
  value: number | string;
  unit?: string;
}

export interface BacktestEvent {
  date?: string;
  title?: string;
  description?: string;
  severity?: string;
}

export interface BacktestRange {
  from: string;
  to: string;
}

export interface BacktestResponse {
  episode: string;
  range: BacktestRange;
  lsi_history: LsiHistoryPoint[];
  metrics: BacktestMetric[];
  events: BacktestEvent[];
  average_contributions: ModuleContribution[];
  conclusion: string;
}

export interface BacktestParams {
  episode?: string;
  from?: string;
  to?: string;
  include_shap?: boolean;
  include_module_breakdown?: boolean;
}
