import { useTaskConfig } from "@/api/config";
import { type TaskType, useStartTask } from "@/api/tasks";
import type { ActiveFileTaskRun } from "@/api/types";
import { getErrorMessage } from "@/lib/errors";
import { getWorkspaceRoot } from "@/lib/task-config";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import DryRunBadge from "./DryRunBadge";
import TaskTypeBadge from "./TaskTypeBadge";

interface StartTaskCardProps {
  taskType: TaskType;
  title: string;
  description: string;
  activeRun: ActiveFileTaskRun | null | undefined;
}

export default function StartTaskCard({
  taskType,
  title,
  description,
  activeRun,
}: StartTaskCardProps) {
  const navigate = useNavigate();
  const [dryRun, setDryRun] = useState(true);
  const configQuery = useTaskConfig(taskType);
  const startTask = useStartTask(taskType);
  const workspaceRoot = getWorkspaceRoot(configQuery.data);

  const disabledReason = getDisabledReason({
    activeRun,
    isConfigLoading: configQuery.isLoading,
    isConfigError: configQuery.isError,
    enabled: configQuery.data?.enabled,
    isStarting: startTask.isPending,
  });

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-semibold text-lg">{title}</h2>
            <TaskTypeBadge taskType={taskType} />
            {dryRun ? <DryRunBadge /> : null}
          </div>
          <p className="text-muted-foreground text-sm">{description}</p>
        </div>
      </div>

      <dl className="mt-5 space-y-3 text-sm">
        <div>
          <dt className="font-medium text-muted-foreground">工作区</dt>
          <dd className="mt-1 break-all text-foreground">
            {workspaceRoot ?? "配置加载后显示"}
          </dd>
        </div>
        <div className="flex items-center gap-2">
          <dt className="font-medium text-muted-foreground">启用状态</dt>
          <dd>{configQuery.data?.enabled ? "已启用" : "未启用"}</dd>
        </div>
      </dl>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(event) => setDryRun(event.target.checked)}
            className="h-4 w-4 rounded border"
          />
          Dry Run（预览）
        </label>
        <button
          type="button"
          disabled={disabledReason !== null}
          onClick={() =>
            startTask.mutate(
              { dry_run: dryRun, trigger_type: "manual" },
              { onSuccess: (run) => navigate(`/tasks/${run.run_id}`) },
            )
          }
          className="rounded-md bg-foreground px-4 py-2 font-medium text-background text-sm transition-colors hover:bg-foreground/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {startTask.isPending ? "启动中..." : "启动"}
        </button>
      </div>

      {disabledReason ? (
        <p className="mt-3 text-muted-foreground text-sm">{disabledReason}</p>
      ) : null}
      {configQuery.isError ? (
        <p className="mt-3 text-red-600 text-sm">
          {getErrorMessage(configQuery.error)}
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

interface DisabledReasonInput {
  activeRun: ActiveFileTaskRun | null | undefined;
  isConfigLoading: boolean;
  isConfigError: boolean;
  enabled: boolean | undefined;
  isStarting: boolean;
}

function getDisabledReason({
  activeRun,
  isConfigLoading,
  isConfigError,
  enabled,
  isStarting,
}: DisabledReasonInput) {
  if (activeRun) {
    return `已有任务正在运行：${activeRun.run_name}`;
  }
  if (isConfigLoading) {
    return "正在加载任务配置";
  }
  if (isConfigError) {
    return "配置加载失败，暂不能启动";
  }
  if (enabled === false) {
    return "请先在配置中启用该任务";
  }
  if (isStarting) {
    return "正在启动任务";
  }
  return null;
}
