"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { SectionCard } from "@/components/common/SectionCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { ScenarioContributionsChart } from "@/features/scenario/components/ScenarioContributionsChart";
import { ScenarioResultCard } from "@/features/scenario/components/ScenarioResultCard";
import { ScenarioShockRow } from "@/features/scenario/components/ScenarioShockRow";
import { useScenario } from "@/features/scenario/hooks/useScenario";
import type { ScenarioShock } from "@/shared/types/scenario";

const defaultShock: ScenarioShock = {
  feature_name: "treasury_delta_week",
  module_id: "M5_TREASURY",
  delta: 300,
  absolute_value: 0,
  unit: "bln_rub"
};

const presets: Record<string, ScenarioShock[]> = {
  "Treasury outflow shock": [{ feature_name: "treasury_delta_week", module_id: "M5_TREASURY", delta: 300, absolute_value: 0, unit: "bln_rub" }],
  "Repo demand spike": [{ feature_name: "repo_demand_spike", module_id: "M2_REPO", delta: 2.5, absolute_value: 0, unit: "ratio" }],
  "Tax week pressure": [{ feature_name: "tax_week_flag", module_id: "M4_TAX", delta: 1, absolute_value: 1, unit: "flag" }],
  "OFZ weak demand": [{ feature_name: "ofz_bid_cover", module_id: "M3_OFZ", delta: -0.8, absolute_value: 0, unit: "ratio" }]
};

export function ScenarioForm() {
  const mutation = useScenario();
  const [baseDate, setBaseDate] = useState("2026-05-08");
  const [taxWeekEnabled, setTaxWeekEnabled] = useState(true);
  const [shocks, setShocks] = useState<ScenarioShock[]>([defaultShock]);

  const submit = async () => {
    await mutation.mutateAsync({
      base_date: baseDate,
      tax_week_enabled: taxWeekEnabled,
      shocks
    });
  };

  return (
    <div className="space-y-6">
      <SectionCard title="What-if simulator" description="Меняйте базовую дату, налоговую неделю и параметры шоков, чтобы оперативно оценивать сценарии стресса.">
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-[240px_auto] md:items-center">
            <Input type="date" value={baseDate} onChange={(event) => setBaseDate(event.target.value)} />
            <div className="flex items-center gap-3">
              <Switch checked={taxWeekEnabled} onCheckedChange={setTaxWeekEnabled} />
              <span className="text-sm text-muted">Tax week enabled</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(presets).map(([label, presetShocks]) => (
              <Button key={label} onClick={() => setShocks(presetShocks)} type="button" variant="secondary">
                {label}
              </Button>
            ))}
          </div>
          <div className="space-y-3">
            {shocks.map((shock, index) => (
              <ScenarioShockRow
                key={`${shock.module_id}-${index}`}
                onChange={(nextValue) => setShocks((current) => current.map((item, itemIndex) => (itemIndex === index ? nextValue : item)))}
                onRemove={() => setShocks((current) => current.filter((_, itemIndex) => itemIndex !== index))}
                shock={shock}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() => setShocks((current) => [...current, { feature_name: "", module_id: "M1_RESERVES", delta: 0, absolute_value: 0, unit: "" }])}
              type="button"
              variant="outline"
            >
              <Plus className="h-4 w-4" />
              Add shock
            </Button>
            <Button onClick={submit} type="button">
              Run scenario
            </Button>
          </div>
        </div>
      </SectionCard>
      {mutation.data ? (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <ScenarioResultCard result={mutation.data} />
          <ScenarioContributionsChart contributions={mutation.data.changed_contributions} />
        </div>
      ) : null}
    </div>
  );
}
