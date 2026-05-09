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
  dry_run: boolean;
}

export interface FileTaskRunStatistics {
  total_items: number;
  success_items: number;
  error_items: number;
  skipped_items: number;
  warning_items: number;
  total_duration_ms: number;
  phase1_seen_files: number;
  phase1_moved_files: number;
  phase1_error_files: number;
  phase2_seen_dirs: number;
  phase2_moved_to_delete_dirs: number;
  phase2_cleaned_deleted_files: number;
  phase2_cleaned_deleted_empty_dirs: number;
  phase2_removed_dirs: number;
  phase2_collapsed_chain_dirs: number;
  phase2_skipped_collapse_dirs: number;
  phase2_flattened_dirs: number;
  phase2_flattened_files: number;
  phase2_moved_to_pic_dirs: number;
  phase2_moved_to_audio_dirs: number;
  phase2_moved_to_compressed_dirs: number;
  phase2_moved_to_video_dirs: number;
  phase2_moved_to_misc_dirs: number;
  phase2_classification_errors: number;
  phase3_seen_files_misc: number;
  phase3_deleted_junk_misc: number;
  phase3_deferred_files_misc: number;
}

export interface FileTaskRunDetailResponse {
  run_id: number;
  run_name: string;
  task_type: FileTaskType;
  trigger_type: FileTaskTriggerType;
  dry_run: boolean;
  status: FileTaskRunStatus;
  start_time: string;
  end_time: string | null;
  error_message: string | null;
  duration_ms: number;
  statistics: FileTaskRunStatistics;
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
