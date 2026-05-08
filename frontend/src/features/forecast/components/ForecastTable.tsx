import { SectionCard } from "@/components/common/SectionCard";
import { StatusBadge } from "@/features/dashboard/components/StatusBadge";
import type { ForecastPoint } from "@/shared/types/dashboard";

export function ForecastTable({ forecast }: { forecast: ForecastPoint[] }) {
  return (
    <SectionCard title="Forecast details" description="Короткий прогноз не следует трактовать как факт. Он нужен как сигнал повышенного внимания.">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-left text-muted">
            <tr className="border-b">
              <th className="pb-3 font-medium">Horizon</th>
              <th className="pb-3 font-medium">Target date</th>
              <th className="pb-3 font-medium">LSI</th>
              <th className="pb-3 font-medium">Status</th>
              <th className="pb-3 font-medium">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {forecast.map((point) => (
              <tr className="border-b last:border-b-0" key={point.horizon}>
                <td className="py-3">{point.horizon}</td>
                <td className="py-3">{point.target_date}</td>
                <td className="py-3">{point.lsi.toFixed(1)}</td>
                <td className="py-3"><StatusBadge status={point.status} /></td>
                <td className="py-3">{Math.round(point.confidence * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}
