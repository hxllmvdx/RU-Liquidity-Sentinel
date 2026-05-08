import { ModuleDetailsScreen } from "@/screens/ModuleDetailsScreen";

export default async function ModuleDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  return <ModuleDetailsScreen id={id} />;
}
