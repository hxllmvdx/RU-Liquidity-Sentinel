"use client";

import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

export function BacktestControls({
  episode,
  from,
  to,
  onEpisodeChange,
  onFromChange,
  onToChange
}: {
  episode: string;
  from: string;
  to: string;
  onEpisodeChange: (value: string) => void;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Select value={episode} onChange={(event) => onEpisodeChange(event.target.value)}>
        <option value="december_2014">december_2014</option>
        <option value="february_march_2022">february_march_2022</option>
        <option value="august_2023">august_2023</option>
        <option value="custom">custom</option>
      </Select>
      <Input disabled={episode !== "custom"} type="date" value={from} onChange={(event) => onFromChange(event.target.value)} />
      <Input disabled={episode !== "custom"} type="date" value={to} onChange={(event) => onToChange(event.target.value)} />
    </div>
  );
}
