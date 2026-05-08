"use client";

import { useQuery } from "@tanstack/react-query";
import { getModules } from "@/shared/api/modules";
import { useModulesSnapshot } from "@/features/modules/hooks/useModulesSnapshot";

export function useModules() {
  const modulesQuery = useQuery({
    queryKey: ["modules"],
    queryFn: getModules
  });

  const snapshotQuery = useModulesSnapshot();

  return { modulesQuery, snapshotQuery };
}
