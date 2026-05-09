const taskListSections = [
  "筛选栏（M4 实现）",
  "任务表格（M4 实现）",
  "分页（M4 实现）",
] as const;

export default function TasksListPage() {
  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <h1 className="text-2xl font-bold">任务列表</h1>

      <div className="space-y-4">
        {taskListSections.map((section) => (
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
