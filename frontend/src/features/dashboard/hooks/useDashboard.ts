"use client";

import { format, subDays } from "date-fns";
import { useQuery } from "@tanstack/react-query";
import { getCurrentDashboard } from "@/shared/api/dashboard";
import { useLsiHistory } from "@/features/dashboard/hooks/useLsiHistory";

export function useDashboard() {
  const to = format(new Date(), "yyyy-MM-dd");
  const from = format(subDays(new Date(), 180), "yyyy-MM-dd");

  const dashboardQuery = useQuery({
    queryKey: ["dashboard", "current"],
    queryFn: getCurrentDashboard
  });

  const historyQuery = useLsiHistory({ from, to, limit: 180, offset: 0 }, "dashboard");

  return { dashboardQuery, historyQuery };
}
