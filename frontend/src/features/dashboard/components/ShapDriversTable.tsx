import { SectionCard } from "@/components/common/SectionCard";
import type { ShapValue } from "@/shared/types/dashboard";

export function ShapDriversTable({ shapValues }: { shapValues: ShapValue[] }) {
  return (
    <SectionCard title="SHAP top drivers" description="Ключевые факторы, которые сильнее всего влияют на текущий расчёт LSI.">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-left text-muted">
            <tr className="border-b">
              <th className="pb-3 font-medium">Feature</th>
              <th className="pb-3 font-medium">Module</th>
              <th className="pb-3 font-medium">Value</th>
              <th className="pb-3 font-medium">Abs value</th>
            </tr>
          </thead>
          <tbody>
            {shapValues.map((item) => (
              <tr className="border-b last:border-b-0" key={`${item.module_id}-${item.feature_name}`}>
                <td className="py-3">{item.feature_name}</td>
                <td className="py-3">{item.module_id}</td>
                <td className="py-3">{item.value.toFixed(1)}</td>
                <td className="py-3">{item.abs_value.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}
