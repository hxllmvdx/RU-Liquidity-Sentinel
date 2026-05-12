import type { Status } from "@/shared/types/common";

export interface LsiHistoryPoint {
  date: string;
  lsi: number;
  status: Status;
  confidence: number;
}

export interface LsiHistoryResponse {
  points: LsiHistoryPoint[];
}

export interface LsiHistoryParams {
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}
