"use client";

import ReactECharts from "echarts-for-react";
import { SectionCard } from "@/components/common/SectionCard";
import type { ForecastPoint } from "@/shared/types/dashboard";
import type { LsiHistoryPoint } from "@/shared/types/lsi";

export function ForecastChart({
  history,
  forecast
}: {
  history: LsiHistoryPoint[];
  forecast: ForecastPoint[];
}) {
  return (
    <SectionCard title="Historical LSI + forecast" description="Forecast points показываются поверх исторического ряда как аналитический early warning.">
      <ReactECharts
        option={{
          tooltip: { trigger: "axis" },
          legend: { data: ["History", "Forecast"] },
          grid: { left: 24, right: 16, top: 30, bottom: 24, containLabel: true },
          xAxis: {
            type: "category",
            data: [...history.map((point) => point.date), ...forecast.map((point) => point.target_date)]
          },
          yAxis: { type: "value", min: 0, max: 100, splitLine: { lineStyle: { color: "#e3edf8" } } },
          series: [
            {
              name: "History",
              type: "line",
              smooth: true,
              data: [...history.map((point) => point.lsi), ...forecast.map(() => null)],
              lineStyle: { color: "#1459b8", width: 3 }
            },
            {
              name: "Forecast",
              type: "line",
              smooth: true,
              data: [...history.map(() => null), ...forecast.map((point) => point.lsi)],
              lineStyle: { color: "#ea7b22", width: 3, type: "dashed" },
              itemStyle: { color: "#ea7b22" }
            }
          ]
        }}
        style={{ height: 320 }}
      />
    </SectionCard>
  );
}
