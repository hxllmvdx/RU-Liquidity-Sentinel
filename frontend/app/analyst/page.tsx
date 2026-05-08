import { ChatInput } from "@/components/analyst/ChatInput";
import { ChatWindow } from "@/components/analyst/ChatWindow";
import { SuggestedQuestions } from "@/components/analyst/SuggestedQuestions";

export default function AnalystPage() {
  return (
    <div className="grid gap-4">
      <SuggestedQuestions />
      <ChatWindow />
      <ChatInput />
    </div>
  );
}
