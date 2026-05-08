"use client";

import { useQuery } from "@tanstack/react-query";
import { getModuleSignals } from "@/shared/api/modules";
import type { ModuleId } from "@/shared/types/common";

export function useModuleSignals(moduleId: ModuleId, from = "2022-02-01", to = "2022-03-31", enabled = true) {
  return useQuery({
    queryKey: ["module-signals", moduleId, from, to],
    queryFn: () => getModuleSignals(moduleId, { from, to }),
    enabled
  });
}
