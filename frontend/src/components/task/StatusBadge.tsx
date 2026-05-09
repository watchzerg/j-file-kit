import type { FileTaskRunStatus } from "@/api/types";
import { cn } from "@/lib/utils";

const statusLabels: Record<FileTaskRunStatus, string> = {
  pending: "等待中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

const statusClasses: Record<FileTaskRunStatus, string> = {
  pending: "border-slate-300 bg-slate-50 text-slate-700",
  running: "border-blue-300 bg-blue-50 text-blue-700",
  completed: "border-emerald-300 bg-emerald-50 text-emerald-700",
  failed: "border-red-300 bg-red-50 text-red-700",
  cancelled: "border-amber-300 bg-amber-50 text-amber-700",
};

interface StatusBadgeProps {
  status: FileTaskRunStatus;
  className?: string;
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 font-medium text-xs",
        statusClasses[status],
        className,
      )}
    >
      {statusLabels[status]}
    </span>
  );
}
