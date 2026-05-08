"use client";

import { useQuery } from "@tanstack/react-query";
import { getBacktest } from "@/shared/api/backtest";
import type { BacktestParams } from "@/shared/types/backtest";

export function useBacktest(params: BacktestParams) {
  return useQuery({
    queryKey: ["backtest", params],
    queryFn: () => getBacktest(params)
  });
}
