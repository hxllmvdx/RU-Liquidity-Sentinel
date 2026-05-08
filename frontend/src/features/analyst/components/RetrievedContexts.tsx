import { SectionCard } from "@/components/common/SectionCard";
import type { AnalystContext } from "@/shared/types/analyst";

export function RetrievedContexts({ contexts }: { contexts: AnalystContext[] }) {
  return (
    <SectionCard title="Retrieved contexts" description="Контексты RAG, использованные для подготовки ответа аналитика.">
      <div className="space-y-3">
        {contexts.map((context, index) => (
          <div className="rounded-2xl border bg-slate-50 p-4" key={`${context.title}-${index}`}>
            <div className="flex items-center justify-between gap-2">
              <p className="font-semibold">{context.title}</p>
              <span className="text-xs font-semibold text-primary">{Math.round(context.relevance * 100)}%</span>
            </div>
            <p className="mt-1 text-sm text-muted">{context.source_type}</p>
            <p className="mt-2 text-sm leading-6 text-muted">{context.content}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
