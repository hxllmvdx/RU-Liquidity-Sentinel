"use client";

import { format, subDays } from "date-fns";
import { useQuery } from "@tanstack/react-query";
import { getCurrentDashboard } from "@/shared/api/dashboard";
import { getLsiHistory } from "@/shared/api/lsi";

export function useForecast() {
  const to = format(new Date(), "yyyy-MM-dd");
  const from = format(subDays(new Date(), 180), "yyyy-MM-dd");

  const dashboardQuery = useQuery({
    queryKey: ["forecast", "dashboard"],
    queryFn: getCurrentDashboard
  });

  const historyQuery = useQuery({
    queryKey: ["forecast", "history"],
    queryFn: () => getLsiHistory({ from, to, limit: 180, offset: 0 })
  });

  return { dashboardQuery, historyQuery };
}
