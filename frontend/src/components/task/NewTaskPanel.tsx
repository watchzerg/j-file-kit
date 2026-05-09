import { TASK_TYPES, useActiveTaskRun } from "@/api/tasks";
import { getErrorMessage } from "@/lib/errors";
import StartTaskCard from "./StartTaskCard";

const taskCards = [
  {
    taskType: TASK_TYPES.JAV,
    title: "JAV 视频整理",
    description: "扫描 JAV 工作区 inbox，并按番号、杂项规则整理视频文件。",
  },
  {
    taskType: TASK_TYPES.RAW,
    title: "Raw 文件整理",
    description: "执行 Raw 三阶段收件箱整理，把散落文件和目录归入目标区域。",
  },
] as const;

export default function NewTaskPanel() {
  const activeRunQuery = useActiveTaskRun();

  return (
    <section className="space-y-4" aria-labelledby="new-task-heading">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="new-task-heading" className="font-semibold text-xl">
            启动任务
          </h2>
          <p className="mt-1 text-muted-foreground text-sm">
            Dry Run 默认开启；关闭后才会执行真实移动或删除。
          </p>
        </div>
      </div>

      {activeRunQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
          {getErrorMessage(activeRunQuery.error)}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        {taskCards.map((task) => (
          <StartTaskCard
            key={task.taskType}
            taskType={task.taskType}
            title={task.title}
            description={task.description}
            activeRun={activeRunQuery.data}
          />
        ))}
      </div>
    </section>
  );
}
