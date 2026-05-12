import { SectionCard } from "@/components/common/SectionCard";
import type { ShapValue } from "@/shared/types/dashboard";

export function ShapDriversTable({ shapValues }: { shapValues: ShapValue[] }) {
  return (
    <SectionCard title="Топ-драйверы расчёта" description="Факторные вклады, рассчитанные как изменение LSI при нейтрализации признака.">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-left text-muted">
            <tr className="border-b">
              <th className="pb-3 font-medium">Признак</th>
              <th className="pb-3 font-medium">Модуль</th>
              <th className="pb-3 font-medium">Значение</th>
              <th className="pb-3 font-medium">Абс. значение</th>
            </tr>
          </thead>
          <tbody>
            {!shapValues.length && (
              <tr>
                <td className="py-4 text-muted" colSpan={4}>Драйверы пока не рассчитаны для текущей даты.</td>
              </tr>
            )}
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
