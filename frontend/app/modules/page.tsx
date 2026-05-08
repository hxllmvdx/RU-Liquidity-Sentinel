import { ModuleCard } from "@/components/modules/ModuleCard";

const modules = ["M1", "M2", "M3", "M4", "M5"];

export default function ModulesPage() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {modules.map((moduleId) => (
        <ModuleCard key={moduleId} moduleId={moduleId} />
      ))}
    </div>
  );
}
