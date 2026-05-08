import { PageHeader } from "@/components/common/PageHeader";
import { MODULE_META } from "@/shared/config/modules";
import type { ModuleId } from "@/shared/types/common";

export function ModuleDetailsHeader({ moduleId }: { moduleId: ModuleId }) {
  const meta = MODULE_META[moduleId];

  return <PageHeader title={meta.shortName} description={meta.description} />;
}
