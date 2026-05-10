import type { FileTaskTriggerType } from "@/api/types";

export const TASK_TRIGGER_LABELS: Record<FileTaskTriggerType, string> = {
  manual: "手动触发",
  auto: "自动触发",
};
