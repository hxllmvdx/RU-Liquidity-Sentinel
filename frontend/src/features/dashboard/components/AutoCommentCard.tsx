import { SectionCard } from "@/components/common/SectionCard";

export function AutoCommentCard({ comment }: { comment: string }) {
  return (
    <SectionCard title="Автокомментарий LLM" description="Краткая автогенерируемая интерпретация текущего состояния денежного рынка.">
      <p className="text-sm leading-7 text-ink">{comment}</p>
    </SectionCard>
  );
}
