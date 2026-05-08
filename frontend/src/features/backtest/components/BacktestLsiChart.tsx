"use client";

import ReactECharts from "echarts-for-react";
import { SectionCard } from "@/components/common/SectionCard";
import type { LsiHistoryPoint } from "@/shared/types/lsi";

export function BacktestLsiChart({ history }: { history: LsiHistoryPoint[] }) {
  return (
    <SectionCard title="График LSI для бэктеста" description="Исторический ряд выбранного стресс-эпизода для проверки своевременности сигнала.">
      <ReactECharts
        option={{
          tooltip: { trigger: "axis" },
          grid: { left: 24, right: 16, top: 20, bottom: 24, containLabel: true },
          xAxis: { type: "category", data: history.map((point) => point.date) },
          yAxis: { type: "value", min: 0, max: 100, splitLine: { lineStyle: { color: "#e3edf8" } } },
          series: [
            {
              type: "line",
              smooth: true,
              data: history.map((point) => point.lsi),
              lineStyle: { color: "#1459b8", width: 3 },
              areaStyle: { color: "rgba(20, 89, 184, 0.08)" },
              itemStyle: { color: "#ea7b22" }
            }
          ]
        }}
        style={{ height: 320 }}
      />
    </SectionCard>
  );
}
