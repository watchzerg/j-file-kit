import type { FileTaskRunDetailResponse } from "@/api/types";
import DryRunBadge from "./DryRunBadge";
import StatusBadge from "./StatusBadge";
import TaskTypeBadge from "./TaskTypeBadge";

const triggerTypeLabels: Record<
  FileTaskRunDetailResponse["trigger_type"],
  string
> = {
  manual: "手动触发",
  auto: "自动触发",
};

interface RunHeaderProps {
  run: FileTaskRunDetailResponse;
}

export default function RunHeader({ run }: RunHeaderProps) {
  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <TaskTypeBadge taskType={run.task_type} />
            <StatusBadge status={run.status} />
            {run.dry_run ? <DryRunBadge /> : null}
            <span className="rounded-full border px-2 py-0.5 font-medium text-muted-foreground text-xs">
              {triggerTypeLabels[run.trigger_type]}
            </span>
          </div>
          <div>
            <p className="text-muted-foreground text-sm">Run #{run.run_id}</p>
            <h1 className="break-all font-bold text-2xl">{run.run_name}</h1>
          </div>
        </div>
      </div>
    </section>
  );
}
