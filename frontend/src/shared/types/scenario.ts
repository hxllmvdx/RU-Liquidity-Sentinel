import type { ModuleId, Status } from "@/shared/types/common";
import type { ModuleContribution, ShapValue } from "@/shared/types/dashboard";

export interface ScenarioShock {
  feature_name: string;
  module_id: ModuleId;
  delta: number;
  absolute_value: number;
  unit: string;
}

export interface ScenarioRequest {
  base_date: string;
  tax_week_enabled: boolean;
  shocks: ScenarioShock[];
}

export interface ScenarioResponse {
  base_date: string;
  base_lsi: number;
  base_status: Status;
  scenario_lsi: number;
  scenario_status: Status;
  delta_lsi: number;
  changed_contributions: ModuleContribution[];
  scenario_shap_values: ShapValue[];
  explanation: string;
}
