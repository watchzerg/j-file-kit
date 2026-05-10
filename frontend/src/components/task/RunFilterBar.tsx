import type { FileTaskRunStatus, FileTaskType } from "@/api/types";

interface RunFilterBarProps {
  taskType: FileTaskType | "all";
  status: FileTaskRunStatus | "all";
  pageSize: number;
  onTaskTypeChange: (value: FileTaskType | "all") => void;
  onStatusChange: (value: FileTaskRunStatus | "all") => void;
  onPageSizeChange: (value: number) => void;
  onReset: () => void;
}

export default function RunFilterBar({
  taskType,
  status,
  pageSize,
  onTaskTypeChange,
  onStatusChange,
  onPageSizeChange,
  onReset,
}: RunFilterBarProps) {
  return (
    <section
      className="flex flex-wrap items-end gap-3 rounded-lg border p-4"
      aria-label="任务列表筛选"
    >
      <label className="grid gap-1 text-sm">
        <span className="font-medium">任务类型</span>
        <select
          className="rounded-md border bg-background px-3 py-2"
          value={taskType}
          onChange={(event) =>
            onTaskTypeChange(event.target.value as FileTaskType | "all")
          }
        >
          <option value="all">全部</option>
          <option value="jav_video_organizer">JAV 视频整理</option>
          <option value="raw_file_organizer">Raw 文件整理</option>
        </select>
      </label>

      <label className="grid gap-1 text-sm">
        <span className="font-medium">状态</span>
        <select
          className="rounded-md border bg-background px-3 py-2"
          value={status}
          onChange={(event) =>
            onStatusChange(event.target.value as FileTaskRunStatus | "all")
          }
        >
          <option value="all">全部</option>
          <option value="pending">等待中</option>
          <option value="running">运行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
          <option value="cancelled">已取消</option>
        </select>
      </label>

      <label className="grid gap-1 text-sm">
        <span className="font-medium">每页</span>
        <select
          className="rounded-md border bg-background px-3 py-2"
          value={pageSize}
          onChange={(event) => onPageSizeChange(Number(event.target.value))}
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </label>

      <button
        type="button"
        className="rounded-md border px-3 py-2 font-medium text-sm hover:bg-muted"
        onClick={onReset}
      >
        重置
      </button>
    </section>
  );
}
