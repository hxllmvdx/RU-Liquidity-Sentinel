"use client";

import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { MODULE_IDS } from "@/shared/config/modules";
import type { ScenarioShock } from "@/shared/types/scenario";

export function ScenarioShockRow({
  shock,
  onChange,
  onRemove
}: {
  shock: ScenarioShock;
  onChange: (nextValue: ScenarioShock) => void;
  onRemove: () => void;
}) {
  return (
    <div className="grid gap-3 rounded-2xl border bg-slate-50 p-4 lg:grid-cols-[1.2fr_1.2fr_0.8fr_0.8fr_0.8fr_auto]">
      <Select value={shock.module_id} onChange={(event) => onChange({ ...shock, module_id: event.target.value as ScenarioShock["module_id"] })}>
        {MODULE_IDS.map((moduleId) => (
          <option key={moduleId} value={moduleId}>
            {moduleId}
          </option>
        ))}
      </Select>
      <Input value={shock.feature_name} onChange={(event) => onChange({ ...shock, feature_name: event.target.value })} placeholder="feature_name" />
      <Input type="number" value={shock.delta} onChange={(event) => onChange({ ...shock, delta: Number(event.target.value) })} placeholder="delta" />
      <Input
        type="number"
        value={shock.absolute_value}
        onChange={(event) => onChange({ ...shock, absolute_value: Number(event.target.value) })}
        placeholder="absolute value"
      />
      <Input value={shock.unit} onChange={(event) => onChange({ ...shock, unit: event.target.value })} placeholder="unit" />
      <Button onClick={onRemove} type="button" variant="ghost">
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}
