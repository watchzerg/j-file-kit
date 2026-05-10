import { useActiveTaskRun, useCancelTaskRun } from "@/api/tasks";
import type { ActiveFileTaskRun } from "@/api/types";
import { getErrorMessage } from "@/lib/errors";
import { formatDuration } from "@/lib/time";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import StatusBadge from "../task/StatusBadge";
import TaskTypeBadge from "../task/TaskTypeBadge";

export default function GlobalRunBanner() {
  const activeRunQuery = useActiveTaskRun();
  const activeRun = activeRunQuery.data;

  if (activeRunQuery.isError) {
    return (
      <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-red-700 text-sm">
        全局任务状态加载失败：{getErrorMessage(activeRunQuery.error)}
      </div>
    );
  }

  if (!activeRun) {
    return null;
  }

  return <GlobalRunBannerInner activeRun={activeRun} />;
}

function GlobalRunBannerInner({ activeRun }: { activeRun: ActiveFileTaskRun }) {
  const cancelRun = useCancelTaskRun(activeRun.run_id);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="border-b bg-muted/40 px-4 py-2">
      <div className="container mx-auto flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-medium">{activeRun.run_name}</span>
          <TaskTypeBadge taskType={activeRun.task_type} />
          <StatusBadge status={activeRun.status} />
          <span className="text-muted-foreground">
            已运行 {formatDuration(activeRun.start_time)}
          </span>
          <span className="sr-only">更新时间 {now}</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to={`/tasks/${activeRun.run_id}`}
            className="font-medium text-sm hover:underline"
          >
            查看详情
          </Link>
          <button
            type="button"
            disabled={cancelRun.isPending}
            onClick={() => cancelRun.mutate()}
            className="rounded-md border px-3 py-1.5 font-medium text-sm transition-colors hover:bg-background disabled:cursor-not-allowed disabled:opacity-50"
          >
            {cancelRun.isPending ? "取消中..." : "取消"}
          </button>
        </div>
        {cancelRun.isError ? (
          <p className="basis-full text-red-600 text-sm">
            {getErrorMessage(cancelRun.error)}
          </p>
        ) : null}
      </div>
    </div>
  );
}
