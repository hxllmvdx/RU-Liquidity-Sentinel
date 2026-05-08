"use client";

import ReactECharts from "echarts-for-react";
import { SectionCard } from "@/components/common/SectionCard";
import type { ModuleSignal } from "@/shared/types/modules";

export function ModuleSignalsChart({ signals }: { signals: ModuleSignal[] }) {
  return (
    <SectionCard title="Signals chart" description="Линейный график MAD score для быстрого поиска всплесков напряжения.">
      <ReactECharts
        option={{
          tooltip: { trigger: "axis" },
          grid: { left: 24, right: 16, top: 20, bottom: 24, containLabel: true },
          xAxis: { type: "category", data: signals.map((signal) => signal.date) },
          yAxis: { type: "value", splitLine: { lineStyle: { color: "#e3edf8" } } },
          series: [
            {
              type: "line",
              smooth: true,
              data: signals.map((signal) => signal.mad_score),
              lineStyle: { color: "#1459b8", width: 3 },
              itemStyle: { color: "#ea7b22" }
            }
          ]
        }}
        style={{ height: 300 }}
      />
    </SectionCard>
  );
}
