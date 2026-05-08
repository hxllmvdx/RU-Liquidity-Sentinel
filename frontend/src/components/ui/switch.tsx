"use client";

import { cn } from "@/shared/lib/cn";

export function Switch({
  checked,
  onCheckedChange
}: {
  checked: boolean;
  onCheckedChange: (nextValue: boolean) => void;
}) {
  return (
    <button
      className={cn(
        "relative inline-flex h-7 w-12 rounded-full border transition",
        checked ? "border-primary bg-primary" : "border-slate-300 bg-slate-200"
      )}
      onClick={() => onCheckedChange(!checked)}
      type="button"
    >
      <span className={cn("absolute top-0.5 h-5 w-5 rounded-full bg-white transition", checked ? "left-6" : "left-0.5")} />
    </button>
  );
}
