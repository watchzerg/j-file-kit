// ── Task runs ──────────────────────────────────────────────────────────────

export type FileTaskRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type FileTaskTriggerType = "manual" | "auto";

export type FileTaskType = "jav_video_organizer" | "raw_file_organizer";

export interface StartTaskRequest {
  dry_run?: boolean;
  trigger_type?: FileTaskTriggerType | null;
}

export interface StartTaskResponse {
  run_id: number;
  run_name: string;
  status: FileTaskRunStatus;
}

export interface FileTaskRunStatusResponse {
  run_id: number;
  run_name: string;
  status: FileTaskRunStatus;
  start_time: string;
  end_time: string | null;
  error_message: string | null;
  total_items: number | null;
}

export interface ActiveFileTaskRun {
  run_id: number;
  run_name: string;
  task_type: FileTaskType;
  trigger_type: FileTaskTriggerType;
  status: FileTaskRunStatus;
  start_time: string;
  end_time: string | null;
  error_message: string | null;
}

export type ActiveFileTaskRunResponse = ActiveFileTaskRun | null;

export interface CancelFileTaskRunResponse {
  run_id: number;
  message: string;
}

export interface FileTaskRunListItem {
  run_id: number;
  run_name: string;
  status: FileTaskRunStatus;
  start_time: string;
  end_time: string | null;
}

export interface FileTaskRunListResponse {
  runs: FileTaskRunListItem[];
}

// ── Task config ────────────────────────────────────────────────────────────

export interface GetFileTaskConfigResponse {
  type: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

export interface UpdateFileTaskConfigRequest {
  enabled?: boolean;
  config?: Record<string, unknown>;
}

export interface UpdateFileTaskConfigResponse {
  message: string;
  code: string;
}

// ── Media browser ──────────────────────────────────────────────────────────

export interface DirectoryItem {
  name: string;
  path: string;
}

export interface ListDirectoriesResponse {
  path: string;
  children: DirectoryItem[];
}
