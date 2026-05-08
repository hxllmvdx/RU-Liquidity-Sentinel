import type { ModuleId, Status } from "@/shared/types/common";

export interface ModuleContribution {
  module_id: ModuleId;
  module_name: string;
  contribution_value: number;
  contribution_percent: number;
}

export interface ShapValue {
  feature_name: string;
  module_id: ModuleId;
  value: number;
  abs_value: number;
}

export interface ActiveFlag {
  flag_name: string;
  module_id: ModuleId;
  description: string;
  severity: number;
}

export interface ForecastPoint {
  horizon: string;
  target_date: string;
  lsi: number;
  status: Status;
  confidence: number;
}

export interface DashboardResponse {
  date: string;
  lsi: number;
  status: Status;
  confidence: number;
  contributions: ModuleContribution[];
  shap_values: ShapValue[];
  active_flags: ActiveFlag[];
  forecast: ForecastPoint[];
  auto_comment: string;
}
