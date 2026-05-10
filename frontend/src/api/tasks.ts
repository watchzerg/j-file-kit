import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  ActiveFileTaskRunResponse,
  CancelFileTaskRunResponse,
  FileTaskRunDetailResponse,
  FileTaskRunListResponse,
  FileTaskRunStatus,
  StartTaskRequest,
  StartTaskResponse,
  TaskRunListParams,
} from "./types";

export const TASK_TYPES = {
  JAV: "jav_video_organizer",
  RAW: "raw_file_organizer",
} as const;

export type TaskType = (typeof TASK_TYPES)[keyof typeof TASK_TYPES];

const POLL_INTERVAL_MS = 2_000;
const ACTIVE_RUN_POLL_INTERVAL_MS = 3_000;
const RECENT_RUNS_LIMIT = 10;
export const DEFAULT_TASK_RUN_PAGE_SIZE = 20;

function isActiveStatus(status: FileTaskRunStatus) {
  return status === "pending" || status === "running";
}

function buildTaskRunsPath(params: TaskRunListParams) {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(params.page));
  searchParams.set("page_size", String(params.page_size));
  if (params.task_type) {
    searchParams.set("task_type", params.task_type);
  }
  if (params.status) {
    searchParams.set("status", params.status);
  }
  return `/api/tasks?${searchParams.toString()}`;
}

export function useTaskRunList(params: TaskRunListParams) {
  return useQuery({
    queryKey: ["tasks", "runs", params],
    queryFn: () =>
      apiClient.get<FileTaskRunListResponse>(buildTaskRunsPath(params)),
  });
}

export function useRecentTaskRuns() {
  return useQuery({
    queryKey: ["tasks", "runs", "recent"],
    queryFn: async () => {
      const response = await apiClient.get<FileTaskRunListResponse>(
        buildTaskRunsPath({
          page: 1,
          page_size: RECENT_RUNS_LIMIT,
        }),
      );
      return response.runs;
    },
  });
}

export function useActiveTaskRun() {
  return useQuery({
    queryKey: ["tasks", "active"],
    queryFn: () =>
      apiClient.get<ActiveFileTaskRunResponse>("/api/tasks/active"),
    refetchInterval: ACTIVE_RUN_POLL_INTERVAL_MS,
  });
}

export function useTaskRunDetail(runId: number | null) {
  return useQuery({
    queryKey: ["tasks", "runs", runId],
    queryFn: () =>
      apiClient.get<FileTaskRunDetailResponse>(`/api/tasks/${runId}`),
    enabled: runId !== null,
    refetchInterval: (query) =>
      query.state.data && isActiveStatus(query.state.data.status)
        ? POLL_INTERVAL_MS
        : false,
  });
}

export function useStartTask(taskType: TaskType) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: StartTaskRequest) =>
      apiClient.post<StartTaskResponse>(
        `/api/tasks/${taskType}/start`,
        request,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks", "runs"] });
      queryClient.invalidateQueries({ queryKey: ["tasks", "active"] });
    },
  });
}

export function useCancelTaskRun(runId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiClient.post<CancelFileTaskRunResponse>(`/api/tasks/${runId}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks", "runs"] });
      queryClient.invalidateQueries({ queryKey: ["tasks", "active"] });
    },
  });
}
