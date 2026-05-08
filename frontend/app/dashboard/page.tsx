import { AutoCommentCard } from "@/components/dashboard/AutoCommentCard";
import { LsiGauge } from "@/components/dashboard/LsiGauge";
import { ModuleContributionChart } from "@/components/dashboard/ModuleContributionChart";
import { StatusCard } from "@/components/dashboard/StatusCard";

export default function DashboardPage() {
  return (
    <div className="grid gap-6">
      <div className="grid gap-4 md:grid-cols-2">
        <LsiGauge />
        <StatusCard />
      </div>
      <ModuleContributionChart />
      <AutoCommentCard />
    </div>
  );
}
