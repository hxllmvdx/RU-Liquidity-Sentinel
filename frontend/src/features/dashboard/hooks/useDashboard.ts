"use client";

import { format, subDays } from "date-fns";
import { useQuery } from "@tanstack/react-query";
import { getCurrentDashboard } from "@/shared/api/dashboard";
import { useLsiHistory } from "@/features/dashboard/hooks/useLsiHistory";

export function useDashboard() {
  const to = format(new Date(), "yyyy-MM-dd");
  const from = format(subDays(new Date(), 7), "yyyy-MM-dd");

  const dashboardQuery = useQuery({
    queryKey: ["dashboard", "current"],
    queryFn: getCurrentDashboard
  });

  const historyQuery = useLsiHistory({ from, to, limit: 8, offset: 0 }, "dashboard");

  return { dashboardQuery, historyQuery };
}
