import { useSystemInfo } from "@/api/system";
import { SystemInfoPanel } from "@/components/system/SystemInfoPanel";
import NewTaskPanel from "@/components/task/NewTaskPanel";
import QuickLinks from "@/components/task/QuickLinks";
import RecentRunsList from "@/components/task/RecentRunsList";
import { getErrorMessage } from "@/lib/errors";

export default function DashboardPage() {
  const systemInfoQuery = useSystemInfo();

  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">
          启动整理任务并查看最近执行情况。
        </p>
      </div>

      <NewTaskPanel />
      <QuickLinks />
      <RecentRunsList />

      {systemInfoQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
          {getErrorMessage(systemInfoQuery.error)}
        </div>
      ) : null}
      <SystemInfoPanel
        info={systemInfoQuery.data}
        isLoading={systemInfoQuery.isLoading}
        variant="compact"
      />
    </div>
  );
}
