"use client";

import { useQuery } from "@tanstack/react-query";
import { getModulesSnapshot } from "@/shared/api/modules";

export function useModulesSnapshot(date?: string) {
  return useQuery({
    queryKey: ["modules", "snapshot", date],
    queryFn: () => getModulesSnapshot(date)
  });
}
