import {
  DEFAULT_TASK_RUN_PAGE_SIZE,
  TASK_TYPES,
  useTaskRunList,
} from "@/api/tasks";
import type { FileTaskRunStatus, FileTaskType } from "@/api/types";
import RunFilterBar from "@/components/task/RunFilterBar";
import RunPagination from "@/components/task/RunPagination";
import RunTable from "@/components/task/RunTable";
import { getErrorMessage } from "@/lib/errors";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

const TASK_TYPE_VALUES = [TASK_TYPES.JAV, TASK_TYPES.RAW] as const;
const STATUS_VALUES = [
  "pending",
  "running",
  "completed",
  "failed",
  "cancelled",
] as const satisfies readonly FileTaskRunStatus[];

interface ListState {
  taskType: FileTaskType | "all";
  status: FileTaskRunStatus | "all";
  page: number;
  pageSize: number;
}

export default function TasksListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const listState = useMemo(() => parseListState(searchParams), [searchParams]);
  const taskRunsQuery = useTaskRunList({
    task_type: listState.taskType === "all" ? undefined : listState.taskType,
    status: listState.status === "all" ? undefined : listState.status,
    page: listState.page,
    page_size: listState.pageSize,
  });

  function updateListState(nextState: ListState) {
    setSearchParams(toSearchParams(nextState));
  }

  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <div>
        <h1 className="text-2xl font-bold">任务列表</h1>
        <p className="mt-1 text-muted-foreground text-sm">
          按任务类型和状态浏览历史 run，活跃任务可在列表中直接取消。
        </p>
      </div>

      <RunFilterBar
        taskType={listState.taskType}
        status={listState.status}
        pageSize={listState.pageSize}
        onTaskTypeChange={(taskType) =>
          updateListState({ ...listState, taskType, page: 1 })
        }
        onStatusChange={(status) =>
          updateListState({ ...listState, status, page: 1 })
        }
        onPageSizeChange={(pageSize) =>
          updateListState({ ...listState, pageSize, page: 1 })
        }
        onReset={() => setSearchParams(new URLSearchParams())}
      />

      {taskRunsQuery.isLoading ? (
        <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
          正在加载任务列表...
        </div>
      ) : null}

      {taskRunsQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
          {getErrorMessage(taskRunsQuery.error)}
        </div>
      ) : null}

      {taskRunsQuery.data?.runs.length === 0 ? (
        <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
          暂无符合条件的任务记录。
        </div>
      ) : null}

      {taskRunsQuery.data && taskRunsQuery.data.runs.length > 0 ? (
        <>
          <RunTable runs={taskRunsQuery.data.runs} />
          <RunPagination
            page={taskRunsQuery.data.page}
            pageSize={taskRunsQuery.data.page_size}
            total={taskRunsQuery.data.total}
            onPageChange={(page) => updateListState({ ...listState, page })}
          />
        </>
      ) : null}
    </div>
  );
}

function parseListState(searchParams: URLSearchParams): ListState {
  return {
    taskType: parseTaskType(searchParams.get("task_type")),
    status: parseStatus(searchParams.get("status")),
    page: parsePositiveInt(searchParams.get("page"), 1),
    pageSize: parsePageSize(searchParams.get("page_size")),
  };
}

function parseTaskType(value: string | null): FileTaskType | "all" {
  if (value && (TASK_TYPE_VALUES as readonly string[]).includes(value)) {
    return value as FileTaskType;
  }
  return "all";
}

function parseStatus(value: string | null): FileTaskRunStatus | "all" {
  if (value && (STATUS_VALUES as readonly string[]).includes(value)) {
    return value as FileTaskRunStatus;
  }
  return "all";
}

function parsePositiveInt(value: string | null, fallback: number) {
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function parsePageSize(value: string | null) {
  const parsed = parsePositiveInt(value, DEFAULT_TASK_RUN_PAGE_SIZE);
  return [10, 20, 50, 100].includes(parsed)
    ? parsed
    : DEFAULT_TASK_RUN_PAGE_SIZE;
}

function toSearchParams(state: ListState) {
  const nextSearchParams = new URLSearchParams();
  nextSearchParams.set("page", String(state.page));
  nextSearchParams.set("page_size", String(state.pageSize));
  if (state.taskType !== "all") {
    nextSearchParams.set("task_type", state.taskType);
  }
  if (state.status !== "all") {
    nextSearchParams.set("status", state.status);
  }
  return nextSearchParams;
}
