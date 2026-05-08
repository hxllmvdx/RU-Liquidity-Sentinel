import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  rightSlot
}: {
  title: string;
  description: string;
  rightSlot?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 rounded-[28px] border bg-white p-6 shadow-panel lg:flex-row lg:items-end lg:justify-between">
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Analytical workspace</p>
        <h2 className="text-3xl font-semibold text-balance">{title}</h2>
        <p className="max-w-3xl text-sm leading-6 text-muted">{description}</p>
      </div>
      {rightSlot ? <div className="shrink-0">{rightSlot}</div> : null}
    </div>
  );
}
