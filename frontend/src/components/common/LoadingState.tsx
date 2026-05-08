export function LoadingState({ label = "Loading data..." }: { label?: string }) {
  return (
    <div className="rounded-[26px] border bg-white p-6 shadow-panel">
      <div className="animate-pulse space-y-3">
        <div className="h-5 w-40 rounded bg-slate-200" />
        <div className="h-10 w-full rounded bg-slate-100" />
        <div className="h-10 w-2/3 rounded bg-slate-100" />
      </div>
      <p className="mt-4 text-sm text-muted">{label}</p>
    </div>
  );
}
