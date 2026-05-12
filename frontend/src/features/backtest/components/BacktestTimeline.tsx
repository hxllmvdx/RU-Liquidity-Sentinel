import { SectionCard } from "@/components/common/SectionCard";
import type { BacktestEvent } from "@/shared/types/backtest";

export function BacktestTimeline({ events }: { events: BacktestEvent[] }) {
  return (
    <SectionCard title="Лента событий" description="Ключевые события стрессового эпизода и их интерпретация для денежного рынка.">
      <div className="space-y-4">
        {events.map((event, index) => (
          <div className="flex gap-4" key={`${event.date}-${index}`}>
            <div className="mt-1 h-3 w-3 rounded-full bg-accent" />
            <div>
              <p className="font-semibold">{event.title ?? "Событие"}</p>
              <p className="text-sm text-muted">{event.date}</p>
              <p className="mt-1 text-sm leading-6 text-muted">{event.description}</p>
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
