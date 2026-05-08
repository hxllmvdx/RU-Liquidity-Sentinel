import { SectionCard } from "@/components/common/SectionCard";
import { formatPercent } from "@/shared/lib/format";

export function ConfidenceCard({ confidence }: { confidence: number }) {
  return (
    <SectionCard title="Уверенность модели" description="Показывает уверенность текущего расчёта на уровне агрегированного индекса.">
      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted">Текущая уверенность</span>
          <span className="font-semibold">{formatPercent(confidence)}</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-primary-soft">
          <div className="h-full rounded-full bg-accent" style={{ width: `${confidence * 100}%` }} />
        </div>
      </div>
    </SectionCard>
  );
}
