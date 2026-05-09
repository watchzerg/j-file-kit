import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  CancelFileTaskRunResponse,
  FileTaskRunListResponse,
  FileTaskRunStatusResponse,
  StartTaskRequest,
  StartTaskResponse,
} from "./types";

export const TASK_TYPES = {
  JAV: "jav_video_organizer",
  RAW: "raw_file_organizer",
} as const;

export type TaskType = (typeof TASK_TYPES)[keyof typeof TASK_TYPES];

const POLL_INTERVAL_MS = 2_000;

function isActiveStatus(status: FileTaskRunStatusResponse["status"]) {
  return status === "pending" || status === "running";
}

export function useTaskRunList() {
  return useQuery({
    queryKey: ["tasks", "runs"],
    queryFn: () => apiClient.get<FileTaskRunListResponse>("/api/tasks"),
  });
}

export function useTaskRunStatus(runId: number | null) {
  return useQuery({
    queryKey: ["tasks", "runs", runId],
    queryFn: () =>
      apiClient.get<FileTaskRunStatusResponse>(`/api/tasks/${runId}`),
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
    },
  });
}
