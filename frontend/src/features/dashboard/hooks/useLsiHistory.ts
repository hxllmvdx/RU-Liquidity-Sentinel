"use client";

import { useQuery } from "@tanstack/react-query";
import { getLsiHistory } from "@/shared/api/lsi";
import type { LsiHistoryParams } from "@/shared/types/lsi";

export function useLsiHistory(params: LsiHistoryParams, scope = "default") {
  return useQuery({
    queryKey: ["lsi-history", scope, params],
    queryFn: () => getLsiHistory(params)
  });
}
