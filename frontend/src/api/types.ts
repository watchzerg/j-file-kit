// ── Task runs ──────────────────────────────────────────────────────────────

export type FileTaskRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type FileTaskTriggerType = "manual" | "auto";

export type FileTaskType = "jav_video_organizer" | "raw_file_organizer";

export type FileTaskDecisionType = "move" | "delete" | "skip";

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

export interface FileTaskRunStatisticsSummary {
  total_items: number;
  success_items: number;
  error_items: number;
  skipped_items: number;
  warning_items: number;
  total_duration_ms: number;
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

export interface DeleteFileTaskRunResponse {
  run_id: number;
  message: string;
}

export interface FileTaskRunListItem {
  run_id: number;
  run_name: string;
  task_type: FileTaskType;
  trigger_type: FileTaskTriggerType;
  dry_run: boolean;
  status: FileTaskRunStatus;
  start_time: string;
  end_time: string | null;
  duration_ms: number;
  statistics_summary: FileTaskRunStatisticsSummary;
}

export interface FileTaskRunListResponse {
  runs: FileTaskRunListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskRunListParams {
  task_type?: FileTaskType;
  status?: FileTaskRunStatus;
  page: number;
  page_size: number;
}

export interface FileTaskRunResultItem {
  id: number;
  source_path: string;
  file_stem: string;
  file_type: string | null;
  serial_id: string | null;
  decision_type: FileTaskDecisionType;
  target_path: string | null;
  success: boolean;
  error_message: string | null;
  duration_ms: number;
  created_at: string;
}

export interface FileTaskRunResultsResponse {
  results: FileTaskRunResultItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskRunResultsParams {
  decision_type?: FileTaskDecisionType;
  success?: boolean;
  q?: string;
  page: number;
  page_size: number;
}

export interface FileTaskRunLogLine {
  line_no: number;
  ts: string | null;
  level: string | null;
  msg: string;
  fields: Record<string, unknown>;
}

export interface FileTaskRunLogsResponse {
  total_lines: number;
  offset: number;
  limit: number;
  lines: FileTaskRunLogLine[];
}

export interface TaskRunLogsParams {
  offset: number;
  limit: number;
}

// ── Task config ────────────────────────────────────────────────────────────

export interface InboxDeleteRulesConfig {
  exact_stems: string[];
  max_size_bytes: number;
}

export interface JavVideoOrganizeConfig {
  workspace_root: string;
  misc_file_delete_rules: {
    max_size?: number;
  };
  video_small_delete_bytes: number | null;
  inbox_delete_rules: InboxDeleteRulesConfig;
}

export interface RawFileOrganizeConfig {
  workspace_root: string;
}

export interface FileTaskConfigByType {
  jav_video_organizer: JavVideoOrganizeConfig;
  raw_file_organizer: RawFileOrganizeConfig;
}

export type FileTaskConfig = FileTaskConfigByType[FileTaskType];

export interface GetFileTaskConfigResponse<
  TConfig extends FileTaskConfig = FileTaskConfig,
> {
  type: FileTaskType;
  enabled: boolean;
  config: TConfig;
}

export interface UpdateFileTaskConfigRequest<
  TConfig extends FileTaskConfig = FileTaskConfig,
> {
  enabled?: boolean;
  config?: Partial<TConfig>;
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

// ── System ─────────────────────────────────────────────────────────────────

export interface SystemInfoResponse {
  app_version: string;
  env: string;
  base_dir: string;
  media_root: string;
  jav_media_root: string;
  raw_media_root: string;
  media_mounted: boolean;
}

export interface ExtensionDefaultsResponse {
  video: string[];
  image: string[];
  subtitle: string[];
  archive: string[];
  music: string[];
  misc_delete: string[];
}

export interface RawDefaultsResponse {
  junk_keywords: string[];
  video_bucket_movie_keywords: string[];
  video_bucket_us_vr_keywords: string[];
  video_bucket_us_keywords: string[];
  camelcase_no_split_words: string[];
  cleanup_junk_max_bytes: number;
}

export interface JavDefaultsResponse {
  vr_serial_prefixes: string[];
  filename_strip_substrings: string[];
}

export interface SystemFileTypeDefaultsResponse {
  extensions: ExtensionDefaultsResponse;
  raw: RawDefaultsResponse;
  jav: JavDefaultsResponse;
}
