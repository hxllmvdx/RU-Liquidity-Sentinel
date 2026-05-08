export default function ModuleDetailsPage({ params }: { params: { id: string } }) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Module {params.id.toUpperCase()}</h1>
      <p>Здесь будет детализация признаков, сигналов и временных рядов модуля.</p>
    </div>
  );
}
