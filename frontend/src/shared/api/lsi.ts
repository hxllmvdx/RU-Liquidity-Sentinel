import { apiRequest, withQuery } from "@/shared/api/client";
import { mockLsiHistory } from "@/shared/api/mock";
import { lsiHistoryResponseSchema } from "@/shared/api/schemas";
import type { LsiHistoryParams, LsiHistoryResponse } from "@/shared/types/lsi";

export function getLsiHistory(params: LsiHistoryParams): Promise<LsiHistoryResponse> {
  return apiRequest({
    path: withQuery("/api/lsi/history", params),
    schema: lsiHistoryResponseSchema,
    mockData: mockLsiHistory
  });
}
