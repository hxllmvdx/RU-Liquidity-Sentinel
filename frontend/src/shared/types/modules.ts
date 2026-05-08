import type { ModuleId } from "@/shared/types/common";
import type { ActiveFlag } from "@/shared/types/dashboard";

export interface ModuleDefinition {
  module_id: ModuleId;
  module_name: string;
  description: string;
}

export interface ModulesResponse {
  modules: ModuleDefinition[];
}

export interface ModuleSignal {
  date: string;
  module_id: ModuleId;
  signal_name: string;
  raw_value: number;
  mad_score: number;
  flag: boolean;
  unit: string;
}

export interface ModuleSnapshot {
  module_id: ModuleId;
  module_name: string;
  module_score?: number;
  signals: ModuleSignal[];
  active_flags: ActiveFlag[];
}

export interface ModulesSnapshotResponse {
  date: string;
  modules: ModuleSnapshot[];
}

export interface ModuleSignalsResponse {
  module_id: ModuleId;
  signals: ModuleSignal[];
  active_flags: ActiveFlag[];
}

export interface ModuleSignalsParams {
  from?: string;
  to?: string;
}
