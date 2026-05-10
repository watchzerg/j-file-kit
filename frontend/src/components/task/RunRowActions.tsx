import { useCancelTaskRun, useDeleteTaskRun } from "@/api/tasks";
import type { FileTaskRunListItem } from "@/api/types";
import { getErrorMessage } from "@/lib/errors";
import { Link } from "react-router-dom";

interface RunRowActionsProps {
  run: FileTaskRunListItem;
}

function isActiveStatus(status: FileTaskRunListItem["status"]) {
  return status === "pending" || status === "running";
}

function isTerminalStatus(status: FileTaskRunListItem["status"]) {
  return (
    status === "completed" || status === "failed" || status === "cancelled"
  );
}

export default function RunRowActions({ run }: RunRowActionsProps) {
  const cancelMutation = useCancelTaskRun(run.run_id);
  const deleteMutation = useDeleteTaskRun(run.run_id);

  function handleDelete() {
    if (!window.confirm(`确定删除任务 ${run.run_name}？此操作不可恢复。`)) {
      return;
    }
    deleteMutation.mutate();
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Link
        to={`/tasks/${run.run_id}`}
        className="font-medium text-foreground text-sm hover:underline"
      >
        查看详情
      </Link>
      {isActiveStatus(run.status) ? (
        <button
          type="button"
          className="rounded-md border border-red-200 px-2 py-1 font-medium text-red-700 text-xs hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={cancelMutation.isPending}
          onClick={() => cancelMutation.mutate()}
        >
          {cancelMutation.isPending ? "取消中..." : "取消"}
        </button>
      ) : null}
      {isTerminalStatus(run.status) ? (
        <button
          type="button"
          className="rounded-md border border-red-200 px-2 py-1 font-medium text-red-700 text-xs hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={deleteMutation.isPending}
          onClick={handleDelete}
        >
          {deleteMutation.isPending ? "删除中..." : "删除"}
        </button>
      ) : null}
      {cancelMutation.isError ? (
        <span className="text-red-600 text-xs">
          {getErrorMessage(cancelMutation.error)}
        </span>
      ) : null}
      {deleteMutation.isError ? (
        <span className="text-red-600 text-xs">
          {getErrorMessage(deleteMutation.error)}
        </span>
      ) : null}
    </div>
  );
}
