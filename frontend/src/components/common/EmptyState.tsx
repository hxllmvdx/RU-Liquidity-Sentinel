export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-[26px] border bg-white p-8 text-center shadow-panel">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">{description}</p>
    </div>
  );
}
