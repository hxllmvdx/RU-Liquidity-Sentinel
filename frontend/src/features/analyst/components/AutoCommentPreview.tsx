import { SectionCard } from "@/components/common/SectionCard";
import type { AutoCommentResponse } from "@/shared/types/analyst";

export function AutoCommentPreview({ comment }: { comment?: AutoCommentResponse }) {
  if (!comment) {
    return null;
  }

  return (
    <SectionCard title="Auto comment preview" description="Ответ эндпоинта `/api/analyst/comment` для быстрого просмотра текста аналитика.">
      <div className="space-y-3 text-sm leading-6 text-muted">
        <p><span className="font-semibold text-ink">Comment:</span> {comment.comment}</p>
        <p><span className="font-semibold text-ink">Retrospective:</span> {comment.retrospective}</p>
        <p><span className="font-semibold text-ink">Outlook:</span> {comment.outlook}</p>
      </div>
    </SectionCard>
  );
}
