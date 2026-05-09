const dashboardSections = [
  "启动任务（M2 实现）",
  "快捷链接（M2 实现）",
  "最近任务（M2 实现）",
  "系统信息（M8 实现）",
] as const;

export default function DashboardPage() {
  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="space-y-4">
        {dashboardSections.map((section) => (
          <div
            key={section}
            className="rounded-lg border border-dashed p-6 text-muted-foreground"
          >
            [区块占位] {section}
          </div>
        ))}
      </div>
    </div>
  );
}
