import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const defaultConfig = {
  type: "jav_video_organizer",
  enabled: true,
  config: { workspace_root: "/media/inbox" },
};

export const server = setupServer(
  http.get("/api/tasks/active", () => HttpResponse.json(null)),
  http.get("/api/tasks", () => HttpResponse.json({ runs: [] })),
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
    }),
  ),
  http.post("/api/tasks/:runId/cancel", () =>
    HttpResponse.json({ run_id: 1, message: "任务已取消" }),
  ),
);
