import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const defaultConfig = {
  type: "jav_video_organizer",
  enabled: true,
  config: {
    workspace_root: "/media/jav_workspace",
    misc_file_delete_rules: { max_size: 1048576 },
    video_small_delete_bytes: 209715200,
    inbox_delete_rules: { exact_stems: ["sample"], max_size_bytes: 0 },
  },
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

const defaultStatisticsSummary = {
  total_items: defaultStatistics.total_items,
  success_items: defaultStatistics.success_items,
  error_items: defaultStatistics.error_items,
  skipped_items: defaultStatistics.skipped_items,
  warning_items: defaultStatistics.warning_items,
  total_duration_ms: defaultStatistics.total_duration_ms,
};

const taskRuns = [
  {
    run_id: 123,
    run_name: "raw_file_organizer-manual-20260510010101000",
    task_type: "raw_file_organizer",
    trigger_type: "manual",
    dry_run: true,
    status: "completed",
    start_time: "2026-05-10T01:01:01",
    end_time: "2026-05-10T01:01:03",
    duration_ms: 2000,
    statistics_summary: defaultStatisticsSummary,
  },
  {
    run_id: 321,
    run_name: "jav_video_organizer-manual-20260510020101000",
    task_type: "jav_video_organizer",
    trigger_type: "manual",
    dry_run: false,
    status: "running",
    start_time: "2026-05-10T02:01:01",
    end_time: null,
    duration_ms: 3000,
    statistics_summary: {
      ...defaultStatisticsSummary,
      total_items: 3,
      success_items: 1,
      error_items: 0,
      skipped_items: 0,
    },
  },
];

const taskResults = [
  {
    id: 1,
    source_path: "/media/raw_workspace/inbox/ABC-123.mp4",
    file_stem: "ABC-123",
    file_type: "video",
    serial_id: "ABC-123",
    decision_type: "move",
    target_path: "/media/raw_workspace/files_video/ABC-123.mp4",
    success: true,
    error_message: null,
    duration_ms: 10.5,
    created_at: "2026-05-10T01:01:02",
  },
  {
    id: 2,
    source_path: "/media/raw_workspace/inbox/junk.tmp",
    file_stem: "junk",
    file_type: null,
    serial_id: null,
    decision_type: "delete",
    target_path: null,
    success: false,
    error_message: "permission denied",
    duration_ms: 2,
    created_at: "2026-05-10T01:01:03",
  },
] as const;

const taskLogs = [
  {
    line_no: 1,
    ts: "2026-05-10 01:01:01.000000+00:00",
    level: "INFO",
    msg: "Task started",
    fields: { run_id: 123 },
  },
  {
    line_no: 2,
    ts: "2026-05-10 01:01:02.000000+00:00",
    level: "WARNING",
    msg: "Skipped unsupported file",
    fields: { source_path: "/media/raw_workspace/inbox/readme.txt" },
  },
] as const;

export const server = setupServer(
  http.get("/api/system/info", () =>
    HttpResponse.json({
      app_version: "dev",
      env: "development",
      base_dir: "/data",
      media_root: "/media",
      jav_media_root: "/media/jav_workspace",
      raw_media_root: "/media/raw_workspace",
      media_mounted: true,
    }),
  ),
  http.get("/api/media/directories", ({ request }) => {
    const url = new URL(request.url);
    const path = url.searchParams.get("path") ?? "/media";
    const childrenByPath: Record<string, { name: string; path: string }[]> = {
      "/media": [
        { name: "jav_workspace", path: "/media/jav_workspace" },
        { name: "raw_workspace", path: "/media/raw_workspace" },
      ],
      "/media/jav_workspace": [
        { name: "project-a", path: "/media/jav_workspace/project-a" },
      ],
      "/media/raw_workspace": [
        { name: "inbox-a", path: "/media/raw_workspace/inbox-a" },
      ],
      "/media/jav_workspace/project-a": [],
      "/media/raw_workspace/inbox-a": [],
    };
    return HttpResponse.json({
      path,
      children: childrenByPath[path] ?? [],
    });
  }),
  http.get("/api/tasks/active", () => HttpResponse.json(null)),
  http.get("/api/tasks", ({ request }) => {
    const url = new URL(request.url);
    const page = Number(url.searchParams.get("page") ?? "1");
    const pageSize = Number(url.searchParams.get("page_size") ?? "20");
    const taskType = url.searchParams.get("task_type");
    const status = url.searchParams.get("status");
    const filteredRuns = taskRuns.filter((run) => {
      const matchesTaskType = taskType === null || run.task_type === taskType;
      const matchesStatus = status === null || run.status === status;
      return matchesTaskType && matchesStatus;
    });
    const start = (page - 1) * pageSize;
    const runs = filteredRuns.slice(start, start + pageSize);

    return HttpResponse.json({
      runs,
      total: filteredRuns.length,
      page,
      page_size: pageSize,
    });
  }),
  http.get("/api/tasks/:runId/results", ({ request }) => {
    const url = new URL(request.url);
    const page = Number(url.searchParams.get("page") ?? "1");
    const pageSize = Number(url.searchParams.get("page_size") ?? "20");
    const decisionType = url.searchParams.get("decision_type");
    const success = url.searchParams.get("success");
    const query = url.searchParams.get("q")?.toLowerCase();
    const filteredResults = taskResults.filter((result) => {
      const matchesDecision =
        decisionType === null || result.decision_type === decisionType;
      const matchesSuccess =
        success === null || String(result.success) === success;
      const matchesQuery =
        !query ||
        result.file_stem.toLowerCase().includes(query) ||
        (result.serial_id?.toLowerCase().includes(query) ?? false);
      return matchesDecision && matchesSuccess && matchesQuery;
    });
    const start = (page - 1) * pageSize;
    const results = filteredResults.slice(start, start + pageSize);

    return HttpResponse.json({
      results,
      total: filteredResults.length,
      page,
      page_size: pageSize,
    });
  }),
  http.get("/api/tasks/:runId/logs", ({ request }) => {
    const url = new URL(request.url);
    const offset = Number(url.searchParams.get("offset") ?? "0");
    const limit = Number(url.searchParams.get("limit") ?? "100");
    const lines = taskLogs.slice(offset, offset + limit);

    return HttpResponse.json({
      total_lines: taskLogs.length,
      offset,
      limit,
      lines,
    });
  }),
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
    }),
  ),
  http.get("/api/file-task/config/raw-file-organizer", () =>
    HttpResponse.json({
      ...defaultConfig,
      type: "raw_file_organizer",
      config: { workspace_root: "/media/raw_workspace" },
    }),
  ),
  http.patch("/api/file-task/config/jav-video-organizer", () =>
    HttpResponse.json({ code: "SUCCESS", message: "配置更新成功" }),
  ),
  http.patch("/api/file-task/config/raw-file-organizer", () =>
    HttpResponse.json({ code: "SUCCESS", message: "配置更新成功" }),
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
  http.delete("/api/tasks/:runId", ({ params }) =>
    HttpResponse.json({
      run_id: Number(params.runId),
      message: "任务已删除",
    }),
  ),
);
