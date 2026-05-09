import NewTaskPanel from "@/components/task/NewTaskPanel";
import QuickLinks from "@/components/task/QuickLinks";
import RecentRunsList from "@/components/task/RecentRunsList";

export default function DashboardPage() {
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

      <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
        [区块占位] 系统信息（M8 实现）
      </div>
    </div>
  );
}
