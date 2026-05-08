import { SectionCard } from "@/components/common/SectionCard";
import type { ModuleSignal } from "@/shared/types/modules";

export function ModuleSignalsTable({ signals }: { signals: ModuleSignal[] }) {
  return (
    <SectionCard title="Signals table" description="Сырые сигналы и MAD-оценки для выбранного модуля.">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-left text-muted">
            <tr className="border-b">
              <th className="pb-3 font-medium">Date</th>
              <th className="pb-3 font-medium">Signal</th>
              <th className="pb-3 font-medium">Raw value</th>
              <th className="pb-3 font-medium">MAD score</th>
              <th className="pb-3 font-medium">Unit</th>
              <th className="pb-3 font-medium">Flag</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((signal) => (
              <tr className="border-b last:border-b-0" key={`${signal.signal_name}-${signal.date}`}>
                <td className="py-3">{signal.date}</td>
                <td className="py-3">{signal.signal_name}</td>
                <td className="py-3">{signal.raw_value.toFixed(2)}</td>
                <td className="py-3">{signal.mad_score.toFixed(2)}</td>
                <td className="py-3">{signal.unit}</td>
                <td className="py-3">{signal.flag ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}
