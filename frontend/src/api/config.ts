import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  FileTaskConfigByType,
  FileTaskType,
  GetFileTaskConfigResponse,
  UpdateFileTaskConfigRequest,
  UpdateFileTaskConfigResponse,
} from "./types";

// Config endpoints are per task type (not parameterised by task_type path)
const CONFIG_PATHS = {
  jav_video_organizer: "/api/file-task/config/jav-video-organizer",
  raw_file_organizer: "/api/file-task/config/raw-file-organizer",
} as const;

type ConfigTaskType = keyof typeof CONFIG_PATHS & FileTaskType;

export function useTaskConfig<TTaskType extends ConfigTaskType>(
  taskType: TTaskType,
) {
  return useQuery({
    queryKey: ["config", taskType],
    queryFn: () =>
      apiClient.get<GetFileTaskConfigResponse<FileTaskConfigByType[TTaskType]>>(
        CONFIG_PATHS[taskType],
      ),
  });
}

export function useUpdateTaskConfig<TTaskType extends ConfigTaskType>(
  taskType: TTaskType,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (
      request: UpdateFileTaskConfigRequest<FileTaskConfigByType[TTaskType]>,
    ) =>
      apiClient.patch<UpdateFileTaskConfigResponse>(
        CONFIG_PATHS[taskType],
        request,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["config", taskType] });
    },
  });
}
