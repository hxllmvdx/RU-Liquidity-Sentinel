import { StressEpisodeCard } from "./StressEpisodeCard";

export function BacktestTimeline() {
  return (
    <div className="grid gap-4">
      <div className="rounded-2xl bg-white p-6 shadow-sm">Backtest timeline</div>
      <StressEpisodeCard />
    </div>
  );
}
