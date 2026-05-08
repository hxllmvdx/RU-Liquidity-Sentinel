import { PageHeader } from "@/components/common/PageHeader";
import { AnalystChat } from "@/features/analyst/components/AnalystChat";

export function AnalystScreen() {
  return (
    <div className="space-y-6">
      <PageHeader title="Analyst workspace" description="Рабочее место для тестирования `/api/analyst/chat` и `/api/analyst/comment` через chat UI и preview retrieved contexts." />
      <AnalystChat />
    </div>
  );
}
