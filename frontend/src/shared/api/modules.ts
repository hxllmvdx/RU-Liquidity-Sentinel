import { apiRequest, withQuery } from "@/shared/api/client";
import { mockModuleSignals, mockModules, mockModulesSnapshot } from "@/shared/api/mock";
import type { ModuleId } from "@/shared/types/common";
import type { ModuleSignalsParams, ModuleSignalsResponse, ModulesResponse, ModulesSnapshotResponse } from "@/shared/types/modules";

export function getModules(): Promise<ModulesResponse> {
  return apiRequest({ path: "/api/modules", mockData: mockModules });
}

export function getModulesSnapshot(date?: string): Promise<ModulesSnapshotResponse> {
  return apiRequest({
    path: withQuery("/api/modules/snapshot", { date }),
    mockData: mockModulesSnapshot
  });
}

export function getModuleSignals(moduleId: ModuleId, params: ModuleSignalsParams): Promise<ModuleSignalsResponse> {
  return apiRequest({
    path: withQuery(`/api/modules/${moduleId}/signals`, params),
    mockData: { ...mockModuleSignals, module_id: moduleId }
  });
}
