import { apiRequest } from "@/shared/api/client";
import { mockScenarioResult } from "@/shared/api/mock";
import { scenarioRequestSchema, scenarioResponseSchema } from "@/shared/api/schemas";
import type { ScenarioRequest, ScenarioResponse } from "@/shared/types/scenario";

export function runScenario(request: ScenarioRequest): Promise<ScenarioResponse> {
  const parsed = scenarioRequestSchema.parse(request);

  return apiRequest({
    path: "/api/scenario/simulate",
    init: {
      method: "POST",
      body: JSON.stringify(parsed)
    },
    schema: scenarioResponseSchema,
    mockData: mockScenarioResult
  });
}
