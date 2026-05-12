"use client";

import ReactECharts from "echarts-for-react";
import { SectionCard } from "@/components/common/SectionCard";
import type { LsiHistoryPoint } from "@/shared/types/lsi";

export function LsiHistoryChart({ points }: { points: LsiHistoryPoint[] }) {
  return (
    <SectionCard title="LSI за последнюю неделю" description="Недельная динамика индекса со справочными границами 40 и 70.">
      <ReactECharts
        option={{
          tooltip: { trigger: "axis" },
          grid: { left: 24, right: 16, top: 20, bottom: 24, containLabel: true },
          xAxis: { type: "category", data: points.map((point) => point.date) },
          yAxis: { type: "value", min: 0, max: 100, splitLine: { lineStyle: { color: "#e3edf8" } } },
          series: [
            {
              type: "line",
              data: points.map((point) => point.lsi),
              smooth: true,
              symbol: "circle",
              symbolSize: 7,
              lineStyle: { color: "#1459b8", width: 3 },
              itemStyle: { color: "#ea7b22" },
              areaStyle: { color: "rgba(20, 89, 184, 0.08)" },
              markLine: {
                silent: true,
                lineStyle: { color: "#d8a229", type: "dashed" },
                data: [{ yAxis: 40 }, { yAxis: 70 }]
              }
            }
          ]
        }}
        style={{ height: 320 }}
      />
    </SectionCard>
  );
}
