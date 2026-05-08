"use client";

import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ErrorState({
  message,
  onRetry
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-[26px] border border-danger/20 bg-white p-6 shadow-panel">
      <div className="flex items-start gap-3">
        <div className="rounded-2xl bg-danger/10 p-3 text-danger">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Данные недоступны</h3>
          <p className="max-w-2xl text-sm leading-6 text-muted">{message}</p>
          {onRetry ? (
            <Button onClick={onRetry} variant="outline">
              Повторить
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
