"use client";

import ReactECharts from "echarts-for-react";
import { SectionCard } from "@/components/common/SectionCard";
import type { ModuleContribution } from "@/shared/types/dashboard";

export function ModuleContributionChart({ contributions }: { contributions: ModuleContribution[] }) {
  return (
    <SectionCard title="Вклады модулей" description="Отображает вклад модулей М1-М5 в текущий уровень индекса.">
      <ReactECharts
        option={{
          grid: { left: 24, right: 16, top: 24, bottom: 24, containLabel: true },
          tooltip: { trigger: "axis" },
          xAxis: { type: "category", data: contributions.map((item) => item.module_id) },
          yAxis: { type: "value", axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "#e3edf8" } } },
          series: [
            {
              type: "bar",
              data: contributions.map((item) => item.contribution_percent),
              itemStyle: { color: "#1459b8", borderRadius: [8, 8, 0, 0] }
            }
          ]
        }}
        style={{ height: 300 }}
      />
    </SectionCard>
  );
}
