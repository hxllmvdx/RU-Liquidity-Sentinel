import { apiRequest, withQuery } from "@/shared/api/client";
import { mockBacktest } from "@/shared/api/mock";
import type { BacktestParams, BacktestResponse } from "@/shared/types/backtest";

export function getBacktest(params: BacktestParams): Promise<BacktestResponse> {
  return apiRequest({
    path: withQuery("/api/backtest", params),
    mockData: mockBacktest
  });
}
