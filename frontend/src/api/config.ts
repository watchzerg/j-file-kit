import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  GetFileTaskConfigResponse,
  UpdateFileTaskConfigRequest,
  UpdateFileTaskConfigResponse,
} from "./types";

// Config endpoints are per task type (not parameterised by task_type path)
const CONFIG_PATHS = {
  jav_video_organizer: "/api/file-task/config/jav-video-organizer",
  raw_file_organizer: "/api/file-task/config/raw-file-organizer",
} as const;

type ConfigTaskType = keyof typeof CONFIG_PATHS;

export function useTaskConfig(taskType: ConfigTaskType) {
  return useQuery({
    queryKey: ["config", taskType],
    queryFn: () =>
      apiClient.get<GetFileTaskConfigResponse>(CONFIG_PATHS[taskType]),
  });
}

export function useUpdateTaskConfig(taskType: ConfigTaskType) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: UpdateFileTaskConfigRequest) =>
      apiClient.patch<UpdateFileTaskConfigResponse>(
        CONFIG_PATHS[taskType],
        request,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["config", taskType] });
    },
  });
}
