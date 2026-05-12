import { apiRequest } from "@/shared/api/client";
import { mockDashboard } from "@/shared/api/mock";
import { dashboardResponseSchema } from "@/shared/api/schemas";
import type { DashboardResponse } from "@/shared/types/dashboard";

export function getCurrentDashboard(): Promise<DashboardResponse> {
  return apiRequest({
    path: "/api/dashboard/current?include_shap=true&include_forecast=false&include_comment=true",
    schema: dashboardResponseSchema,
    mockData: mockDashboard
  });
}
