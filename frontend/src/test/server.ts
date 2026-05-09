import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const defaultConfig = {
  type: "jav_video_organizer",
  enabled: true,
  config: { workspace_root: "/media/inbox" },
};

const defaultStatistics = {
  total_items: 12,
  success_items: 9,
  error_items: 1,
  skipped_items: 2,
  warning_items: 0,
  total_duration_ms: 1234,
  phase1_seen_files: 3,
  phase1_moved_files: 2,
  phase1_error_files: 1,
  phase2_seen_dirs: 4,
  phase2_moved_to_delete_dirs: 1,
  phase2_cleaned_deleted_files: 2,
  phase2_cleaned_deleted_empty_dirs: 1,
  phase2_removed_dirs: 1,
  phase2_collapsed_chain_dirs: 1,
  phase2_skipped_collapse_dirs: 0,
  phase2_flattened_dirs: 1,
  phase2_flattened_files: 5,
  phase2_moved_to_pic_dirs: 1,
  phase2_moved_to_audio_dirs: 0,
  phase2_moved_to_compressed_dirs: 0,
  phase2_moved_to_video_dirs: 1,
  phase2_moved_to_misc_dirs: 1,
  phase2_classification_errors: 0,
  phase3_seen_files_misc: 6,
  phase3_deleted_junk_misc: 2,
  phase3_deferred_files_misc: 1,
};

export const server = setupServer(
  http.get("/api/tasks/active", () => HttpResponse.json(null)),
  http.get("/api/tasks", () => HttpResponse.json({ runs: [] })),
  http.get("/api/tasks/:runId", ({ params }) =>
    HttpResponse.json({
      run_id: Number(params.runId),
      run_name: "raw_file_organizer-manual-20260510010101000",
      task_type: "raw_file_organizer",
      trigger_type: "manual",
      dry_run: true,
      status: "completed",
      start_time: "2026-05-10T01:01:01",
      end_time: "2026-05-10T01:01:03",
      error_message: null,
      duration_ms: 2000,
      statistics: defaultStatistics,
    }),
  ),
  http.get("/api/file-task/config/jav-video-organizer", () =>
    HttpResponse.json({
      ...defaultConfig,
      type: "jav_video_organizer",
      config: { workspace_root: "/media/jav" },
    }),
  ),
  http.get("/api/file-task/config/raw-file-organizer", () =>
    HttpResponse.json({
      ...defaultConfig,
      type: "raw_file_organizer",
      config: { workspace_root: "/media/raw" },
    }),
  ),
  http.post("/api/tasks/:taskType/start", () =>
    HttpResponse.json({
      run_id: 1,
      run_name: "test-run",
      status: "pending",
      dry_run: true,
    }),
  ),
  http.post("/api/tasks/:runId/cancel", () =>
    HttpResponse.json({ run_id: 1, message: "任务已取消" }),
  ),
);
