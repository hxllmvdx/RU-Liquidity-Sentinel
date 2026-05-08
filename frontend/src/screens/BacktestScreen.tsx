"use client";

import { useState } from "react";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { BacktestControls } from "@/features/backtest/components/BacktestControls";
import { BacktestEvents } from "@/features/backtest/components/BacktestEvents";
import { BacktestLsiChart } from "@/features/backtest/components/BacktestLsiChart";
import { BacktestMetrics } from "@/features/backtest/components/BacktestMetrics";
import { BacktestTimeline } from "@/features/backtest/components/BacktestTimeline";
import { useBacktest } from "@/features/backtest/hooks/useBacktest";

export function BacktestScreen() {
  const [episode, setEpisode] = useState("february_march_2022");
  const [from, setFrom] = useState("2022-02-01");
  const [to, setTo] = useState("2022-03-31");

  const query = useBacktest({
    episode,
    from: episode === "custom" ? from : undefined,
    to: episode === "custom" ? to : undefined,
    include_shap: true,
    include_module_breakdown: true
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Backtest episodes" description="Проверка исторических стрессовых эпизодов, метрик раннего предупреждения и структуры вкладов модулей." />
      <SectionCard title="Episode controls" description="Выберите стандартный эпизод или задайте собственный диапазон дат.">
        <BacktestControls episode={episode} from={from} onEpisodeChange={setEpisode} onFromChange={setFrom} onToChange={setTo} to={to} />
      </SectionCard>
      {query.isLoading ? <LoadingState label="Loading backtest..." /> : null}
      {query.error ? <ErrorState message={(query.error as Error).message} onRetry={() => void query.refetch()} /> : null}
      {query.data ? (
        <>
          <BacktestMetrics metrics={query.data.metrics} />
          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <BacktestLsiChart history={query.data.lsi_history} />
            <BacktestTimeline events={query.data.events} />
          </div>
          <BacktestEvents conclusion={query.data.conclusion} contributions={query.data.average_contributions} />
        </>
      ) : null}
    </div>
  );
}
