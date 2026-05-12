import { z } from "zod";

export const statusSchema = z.enum(["green", "yellow", "red", "unspecified"]);
export const moduleIdSchema = z.enum(["M1_RESERVES", "M2_REPO", "M3_OFZ", "M4_TAX", "M5_TREASURY"]);

export const moduleContributionSchema = z.object({
  module_id: moduleIdSchema,
  module_name: z.string(),
  contribution_value: z.number(),
  contribution_percent: z.number()
});

export const shapValueSchema = z.object({
  feature_name: z.string(),
  module_id: moduleIdSchema,
  value: z.number(),
  abs_value: z.number()
});

export const activeFlagSchema = z.object({
  flag_name: z.string(),
  module_id: moduleIdSchema,
  description: z.string(),
  severity: z.number()
});

export const forecastPointSchema = z.object({
  horizon: z.string(),
  target_date: z.string(),
  lsi: z.number(),
  status: statusSchema,
  confidence: z.number()
});

export const dashboardResponseSchema = z.object({
  date: z.string(),
  lsi: z.number(),
  status: statusSchema,
  confidence: z.number(),
  contributions: z.array(moduleContributionSchema),
  shap_values: z.array(shapValueSchema),
  active_flags: z.array(activeFlagSchema),
  forecast: z.array(forecastPointSchema),
  auto_comment: z.string()
});

export const scenarioRequestSchema = z.object({
  base_date: z.string(),
  tax_week_enabled: z.boolean(),
  shocks: z.array(
    z.object({
      feature_name: z.string(),
      module_id: moduleIdSchema,
      delta: z.number(),
      absolute_value: z.number(),
      unit: z.string()
    })
  )
});

export const scenarioResponseSchema = z.object({
  base_date: z.string(),
  base_lsi: z.number(),
  base_status: statusSchema,
  scenario_lsi: z.number(),
  scenario_status: statusSchema,
  delta_lsi: z.number(),
  changed_contributions: z.array(moduleContributionSchema),
  scenario_shap_values: z.array(shapValueSchema),
  explanation: z.string()
});

export const lsiHistoryResponseSchema = z.object({
  points: z.array(
    z.object({
      date: z.string(),
      lsi: z.number(),
      status: statusSchema,
      confidence: z.number()
    })
  )
});
