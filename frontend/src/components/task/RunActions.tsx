import { useActiveTaskRun, useCancelTaskRun, useStartTask } from "@/api/tasks";
import type { FileTaskRunDetailResponse } from "@/api/types";
import { getErrorMessage } from "@/lib/errors";
import { useNavigate } from "react-router-dom";

interface RunActionsProps {
  run: FileTaskRunDetailResponse;
}

function isActiveStatus(status: FileTaskRunDetailResponse["status"]) {
  return status === "pending" || status === "running";
}

export default function RunActions({ run }: RunActionsProps) {
  const navigate = useNavigate();
  const activeRunQuery = useActiveTaskRun();
  const cancelRun = useCancelTaskRun(run.run_id);
  const startTask = useStartTask(run.task_type);
  const hasActiveRun =
    activeRunQuery.data !== null && activeRunQuery.data !== undefined;
  const canCancel = isActiveStatus(run.status);
  const restartDisabled =
    hasActiveRun || activeRunQuery.isLoading || startTask.isPending;

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold text-lg">操作</h2>
          <p className="mt-1 text-muted-foreground text-sm">
            重跑会沿用当前 run 的任务类型和 Dry Run 设置。
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {canCancel ? (
            <button
              type="button"
              disabled={cancelRun.isPending}
              onClick={() => cancelRun.mutate()}
              className="rounded-md border px-4 py-2 font-medium text-sm transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              {cancelRun.isPending ? "取消中..." : "取消"}
            </button>
          ) : null}
          <button
            type="button"
            disabled={restartDisabled}
            onClick={() =>
              startTask.mutate(
                { dry_run: run.dry_run, trigger_type: "manual" },
                { onSuccess: (newRun) => navigate(`/tasks/${newRun.run_id}`) },
              )
            }
            className="rounded-md bg-foreground px-4 py-2 font-medium text-background text-sm transition-colors hover:bg-foreground/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {startTask.isPending ? "重跑中..." : "重跑"}
          </button>
        </div>
      </div>

      {hasActiveRun ? (
        <p className="mt-3 text-muted-foreground text-sm">
          当前已有活跃任务，完成或取消后才能重跑。
        </p>
      ) : null}
      {cancelRun.isError ? (
        <p className="mt-3 text-red-600 text-sm">
          {getErrorMessage(cancelRun.error)}
        </p>
      ) : null}
      {startTask.isError ? (
        <p className="mt-3 text-red-600 text-sm">
          {getErrorMessage(startTask.error)}
        </p>
      ) : null}
    </section>
  );
}
