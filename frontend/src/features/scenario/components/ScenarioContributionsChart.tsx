"use client";

import ReactECharts from "echarts-for-react";
import { SectionCard } from "@/components/common/SectionCard";
import type { ModuleContribution } from "@/shared/types/dashboard";

export function ScenarioContributionsChart({ contributions }: { contributions: ModuleContribution[] }) {
  return (
    <SectionCard title="Изменившиеся вклады" description="После шока можно быстро увидеть, какие модули сильнее всего сдвинули итоговый индекс.">
      <ReactECharts
        option={{
          grid: { left: 24, right: 16, top: 20, bottom: 24, containLabel: true },
          tooltip: { trigger: "axis" },
          xAxis: { type: "category", data: contributions.map((item) => item.module_id) },
          yAxis: { type: "value", splitLine: { lineStyle: { color: "#e3edf8" } } },
          series: [
            {
              type: "bar",
              data: contributions.map((item) => item.contribution_percent),
              itemStyle: { color: "#ea7b22", borderRadius: [8, 8, 0, 0] }
            }
          ]
        }}
        style={{ height: 300 }}
      />
    </SectionCard>
  );
}
