"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { SectionCard } from "@/components/common/SectionCard";
import { generateAutoComment } from "@/shared/api/analyst";
import { AutoCommentPreview } from "@/features/analyst/components/AutoCommentPreview";
import { ChatInput } from "@/features/analyst/components/ChatInput";
import { ChatMessage } from "@/features/analyst/components/ChatMessage";
import { RetrievedContexts } from "@/features/analyst/components/RetrievedContexts";
import { SuggestedQuestions } from "@/features/analyst/components/SuggestedQuestions";
import { useAnalystChat } from "@/features/analyst/hooks/useAnalystChat";

export function AnalystChat() {
  const chatMutation = useAnalystChat();
  const commentMutation = useMutation({ mutationFn: generateAutoComment });
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [selectedQuestion, setSelectedQuestion] = useState("");

  const sendMessage = async (message: string) => {
    setMessages((current) => [...current, { role: "user", content: message }]);
    const response = await chatMutation.mutateAsync({
      session_id: "demo-session-1",
      user_message: message,
      preferred_range: { from: "2023-08-01", to: "2023-08-31" }
    });
    setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
    setSelectedQuestion("");

    if (!commentMutation.data) {
      void commentMutation.mutate({
        date: "2026-05-08",
        lsi: 67.5,
        status: "yellow",
        module_contributions: [{ name: "M2_REPO", value: 24 }],
        active_flags: ["Flag_Demand"],
        upcoming_events: ["Tax week starts in 2 days"]
      });
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
      <SectionCard title="Analyst chat" description="Интерфейс для проверки `/api/analyst/chat` и сценариев RAG/LLM до полной готовности ML-слоя.">
        <div className="space-y-4">
          <SuggestedQuestions onSelect={setSelectedQuestion} />
          <div className="flex min-h-[360px] flex-col gap-3 rounded-2xl border bg-slate-50 p-4">
            {messages.length ? (
              messages.map((message, index) => <ChatMessage content={message.content} key={index} role={message.role} />)
            ) : (
              <p className="text-sm text-muted">Start with a suggested question or enter your own prompt.</p>
            )}
          </div>
          <ChatInput loading={chatMutation.isPending} onSend={sendMessage} preset={selectedQuestion} />
        </div>
      </SectionCard>
      <div className="space-y-6">
        <RetrievedContexts contexts={chatMutation.data?.contexts ?? []} />
        <AutoCommentPreview comment={commentMutation.data} />
      </div>
    </div>
  );
}
