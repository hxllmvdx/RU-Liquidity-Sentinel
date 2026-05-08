"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ChatInput({
  onSend,
  loading,
  preset
}: {
  onSend: (message: string) => void;
  loading: boolean;
  preset?: string;
}) {
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (preset) {
      setMessage(preset);
    }
  }, [preset]);

  return (
    <div className="space-y-3">
      <Textarea placeholder="Спросите аналитика про текущий LSI, исторический эпизод или сценарный шок." value={message} onChange={(event) => setMessage(event.target.value)} />
      <div className="flex justify-end">
        <Button disabled={loading || !message.trim()} onClick={() => onSend(message)} type="button">
          Send message
        </Button>
      </div>
    </div>
  );
}
