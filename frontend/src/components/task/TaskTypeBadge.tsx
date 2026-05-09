import type { FileTaskType } from "@/api/types";
import { cn } from "@/lib/utils";

const taskTypeLabels: Record<FileTaskType, string> = {
  jav_video_organizer: "JAV 视频整理",
  raw_file_organizer: "Raw 文件整理",
};

const taskTypeClasses: Record<FileTaskType, string> = {
  jav_video_organizer: "border-violet-300 bg-violet-50 text-violet-700",
  raw_file_organizer: "border-cyan-300 bg-cyan-50 text-cyan-700",
};

interface TaskTypeBadgeProps {
  taskType: FileTaskType;
  className?: string;
}

export function getTaskTypeLabel(taskType: FileTaskType) {
  return taskTypeLabels[taskType];
}

export default function TaskTypeBadge({
  taskType,
  className,
}: TaskTypeBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 font-medium text-xs",
        taskTypeClasses[taskType],
        className,
      )}
    >
      {taskTypeLabels[taskType]}
    </span>
  );
}
