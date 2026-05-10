import { cleanup, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";
import { server } from "../test/server";
import { clickEnabledButton, renderAt } from "../test/utils.tsx";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.pushState(null, "", "/");
});

describe("Task detail page", () => {
  it("renders task detail overview", async () => {
    renderAt("/tasks/123");

    expect(
      await screen.findByRole("heading", {
        name: "raw_file_organizer-manual-20260510010101000",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Raw 文件整理")).toBeInTheDocument();
    expect(screen.getByText("Dry Run")).toBeInTheDocument();
    expect(screen.getByText("统计概览")).toBeInTheDocument();
    expect(screen.getByText("Raw 阶段统计")).toBeInTheDocument();
    expect(screen.getByText("阶段 1：收散落文件")).toBeInTheDocument();
    expect(screen.getByText("暂留 files_misc")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("renders task detail file results", async () => {
    const user = userEvent.setup();
    renderAt("/tasks/123");

    await user.click(await screen.findByRole("tab", { name: "文件结果" }));

    expect(
      await screen.findByText("/media/raw_workspace/inbox/ABC-123.mp4"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("ABC-123").length).toBeGreaterThan(0);
    expect(screen.getAllByText("移动").length).toBeGreaterThan(0);
    expect(screen.getByText("permission denied")).toBeInTheDocument();
  });

  it("syncs file result filters to the URL", async () => {
    const user = userEvent.setup();
    renderAt("/tasks/123");

    await user.click(await screen.findByRole("tab", { name: "文件结果" }));
    await user.selectOptions(await screen.findByLabelText("决策"), "delete");
    await user.selectOptions(screen.getByLabelText("结果"), "false");

    await waitFor(() => {
      expect(window.location.search).toContain("results_decision=delete");
      expect(window.location.search).toContain("results_success=false");
      expect(screen.getByText("junk")).toBeInTheDocument();
      expect(screen.queryByText("ABC-123")).not.toBeInTheDocument();
    });
  });

  it("changes file result pages", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/tasks/:runId/results", ({ request }) => {
        const url = new URL(request.url);
        const page = Number(url.searchParams.get("page") ?? "1");
        return HttpResponse.json({
          results: [
            {
              id: page,
              source_path: `/media/raw_workspace/inbox/page-${page}.mp4`,
              file_stem: `page-${page}`,
              file_type: "video",
              serial_id: null,
              decision_type: "move",
              target_path: `/media/raw_workspace/files_video/page-${page}.mp4`,
              success: true,
              error_message: null,
              duration_ms: 1000,
              created_at: "2026-05-10T01:01:02",
            },
          ],
          total: 25,
          page,
          page_size: 20,
        });
      }),
    );

    renderAt("/tasks/123");

    await user.click(await screen.findByRole("tab", { name: "文件结果" }));
    expect(await screen.findByText("page-1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "下一页" }));

    await waitFor(() => {
      expect(window.location.search).toContain("results_page=2");
      expect(screen.getByText("page-2")).toBeInTheDocument();
    });
  });

  it("renders task detail logs", async () => {
    const user = userEvent.setup();
    renderAt("/tasks/123");

    expect(
      await screen.findByRole("heading", {
        name: "raw_file_organizer-manual-20260510010101000",
      }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "日志" }));

    expect(await screen.findByText("Task started")).toBeInTheDocument();
    expect(screen.getByText("Skipped unsupported file")).toBeInTheDocument();
    expect(screen.getByText("WARNING")).toBeInTheDocument();
  });

  it("changes task log pages", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/tasks/:runId/logs", ({ request }) => {
        const url = new URL(request.url);
        const offset = Number(url.searchParams.get("offset") ?? "0");
        const limit = Number(url.searchParams.get("limit") ?? "100");
        return HttpResponse.json({
          total_lines: 150,
          offset,
          limit,
          lines: [
            {
              line_no: offset + 1,
              ts: "2026-05-10 01:01:01.000000+00:00",
              level: "INFO",
              msg: `log-${offset + 1}`,
              fields: {},
            },
          ],
        });
      }),
    );

    renderAt("/tasks/123");

    await user.click(await screen.findByRole("tab", { name: "日志" }));
    expect(await screen.findByText("log-1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "下一页" }));

    expect(await screen.findByText("log-101")).toBeInTheDocument();
    expect(window.location.search).toContain("logs_offset=100");
  });

  it("renders error page for invalid run ID", () => {
    renderAt("/tasks/abc");

    expect(screen.getByText("无效任务 ID。")).toBeInTheDocument();
  });

  it("renders JAV task detail without RawPhaseStats", async () => {
    renderAt("/tasks/321");

    expect(
      await screen.findByText("jav_video_organizer-manual-20260510020101000"),
    ).toBeInTheDocument();
    expect(screen.getByText("JAV 视频整理")).toBeInTheDocument();
    expect(screen.queryByText("Raw 阶段统计")).not.toBeInTheDocument();
  });

  it("filters file results by keyword and syncs to URL", async () => {
    const user = userEvent.setup();
    renderAt("/tasks/123");

    await user.click(await screen.findByRole("tab", { name: "文件结果" }));

    const queryInput = await screen.findByPlaceholderText(
      "file_stem 或 serial_id",
    );
    await user.type(queryInput, "ABC");

    await waitFor(() => {
      expect(window.location.search).toContain("results_q=ABC");
      // "junk" result should no longer appear
      expect(screen.queryByText("junk")).not.toBeInTheDocument();
      // ABC-123 appears in at least one cell
      expect(screen.getAllByText("ABC-123").length).toBeGreaterThan(0);
    });
  });

  it("resets file result filters and clears URL params", async () => {
    const user = userEvent.setup();
    renderAt("/tasks/123?results_decision=delete&results_success=false");

    await user.click(await screen.findByRole("tab", { name: "文件结果" }));
    await screen.findByText("junk");

    await user.click(screen.getByRole("button", { name: "重置" }));

    await waitFor(() => {
      expect(window.location.search).not.toContain("results_decision");
      expect(window.location.search).not.toContain("results_success");
      // both results should now be visible
      expect(screen.getAllByText("ABC-123").length).toBeGreaterThan(0);
    });
  });

  it("restarts a task detail with the same dry run setting", async () => {
    const user = userEvent.setup();
    const startHandler = vi.fn();
    server.use(
      http.post("/api/tasks/raw_file_organizer/start", async ({ request }) => {
        startHandler(await request.json());
        return HttpResponse.json({
          run_id: 55,
          run_name: "raw-rerun",
          status: "pending",
          dry_run: true,
        });
      }),
    );

    renderAt("/tasks/123");

    await clickEnabledButton(user, "重跑", 0);

    await waitFor(() => {
      expect(startHandler).toHaveBeenCalledWith({
        dry_run: true,
        trigger_type: "manual",
      });
      expect(window.location.pathname).toBe("/tasks/55");
    });
  });

  it("shows empty state when file results are empty", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/tasks/:runId/results", () =>
        HttpResponse.json({ results: [], total: 0, page: 1, page_size: 20 }),
      ),
    );

    renderAt("/tasks/123");

    await user.click(await screen.findByRole("tab", { name: "文件结果" }));

    await waitFor(() => {
      expect(screen.getByText("暂无符合条件的文件结果。")).toBeInTheDocument();
    });
  });

  it("shows empty state when logs are empty", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/tasks/:runId/logs", () =>
        HttpResponse.json({ total_lines: 0, offset: 0, limit: 100, lines: [] }),
      ),
    );

    renderAt("/tasks/123");

    await user.click(await screen.findByRole("tab", { name: "日志" }));

    await waitFor(() => {
      expect(screen.getByText("暂无任务日志。")).toBeInTheDocument();
    });
  });

  it("disables restart when an active run exists", async () => {
    server.use(
      http.get("/api/tasks/active", () =>
        HttpResponse.json({
          run_id: 321,
          run_name: "jav-running",
          task_type: "jav_video_organizer",
          trigger_type: "manual",
          status: "running",
          start_time: new Date().toISOString(),
          end_time: null,
          error_message: null,
        }),
      ),
    );

    renderAt("/tasks/123");

    const restartBtn = await screen.findByRole("button", { name: "重跑" });
    expect(restartBtn).toBeDisabled();
    expect(
      screen.getByText("当前已有活跃任务，完成或取消后才能重跑。"),
    ).toBeInTheDocument();
  });

  it("does not delete when confirmation is dismissed", async () => {
    const user = userEvent.setup();
    const deleteHandler = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    server.use(
      http.delete("/api/tasks/123", () => {
        deleteHandler();
        return HttpResponse.json({ run_id: 123, message: "任务已删除" });
      }),
    );

    renderAt("/tasks/123");

    await user.click(await screen.findByRole("button", { name: "删除" }));

    await waitFor(() => expect(window.confirm).toHaveBeenCalledOnce());
    expect(deleteHandler).not.toHaveBeenCalled();
  });

  it("shows error message when cancel API fails", async () => {
    server.use(
      http.get("/api/tasks/321", () =>
        HttpResponse.json({
          run_id: 321,
          run_name: "running-detail",
          task_type: "jav_video_organizer",
          trigger_type: "manual",
          dry_run: false,
          status: "running",
          start_time: new Date().toISOString(),
          end_time: null,
          error_message: null,
          duration_ms: 0,
          statistics: {
            total_items: 0,
            success_items: 0,
            error_items: 0,
            skipped_items: 0,
            warning_items: 0,
            total_duration_ms: 0,
          },
        }),
      ),
      http.post("/api/tasks/321/cancel", () =>
        HttpResponse.json({ detail: "Internal Server Error" }, { status: 500 }),
      ),
    );

    const user = userEvent.setup();
    renderAt("/tasks/321");

    await user.click(await screen.findByRole("button", { name: "取消" }));

    await waitFor(() => {
      expect(screen.getByText("发生未知错误，请稍后重试")).toBeInTheDocument();
    });
  });

  it("shows error message when restart API fails", async () => {
    server.use(
      http.post("/api/tasks/raw_file_organizer/start", () =>
        HttpResponse.json({ detail: "Internal Server Error" }, { status: 500 }),
      ),
    );

    const user = userEvent.setup();
    renderAt("/tasks/123");

    await clickEnabledButton(user, "重跑", 0);

    await waitFor(() => {
      expect(screen.getByText("发生未知错误，请稍后重试")).toBeInTheDocument();
    });
  });

  it("cancels a running task from the detail page", async () => {
    const user = userEvent.setup();
    const cancelHandler = vi.fn();
    server.use(
      http.get("/api/tasks/321", () =>
        HttpResponse.json({
          run_id: 321,
          run_name: "running-detail",
          task_type: "jav_video_organizer",
          trigger_type: "manual",
          dry_run: false,
          status: "running",
          start_time: new Date().toISOString(),
          end_time: null,
          error_message: null,
          duration_ms: 0,
          statistics: {
            total_items: 0,
            success_items: 0,
            error_items: 0,
            skipped_items: 0,
            warning_items: 0,
            total_duration_ms: 0,
            phase1_seen_files: 0,
            phase1_moved_files: 0,
            phase1_error_files: 0,
            phase2_seen_dirs: 0,
            phase2_moved_to_delete_dirs: 0,
            phase2_cleaned_deleted_files: 0,
            phase2_cleaned_deleted_empty_dirs: 0,
            phase2_removed_dirs: 0,
            phase2_collapsed_chain_dirs: 0,
            phase2_skipped_collapse_dirs: 0,
            phase2_flattened_dirs: 0,
            phase2_flattened_files: 0,
            phase2_moved_to_pic_dirs: 0,
            phase2_moved_to_audio_dirs: 0,
            phase2_moved_to_compressed_dirs: 0,
            phase2_moved_to_video_dirs: 0,
            phase2_moved_to_misc_dirs: 0,
            phase2_classification_errors: 0,
            phase3_seen_files_misc: 0,
            phase3_deleted_junk_misc: 0,
            phase3_deferred_files_misc: 0,
          },
        }),
      ),
      http.post("/api/tasks/321/cancel", () => {
        cancelHandler();
        return HttpResponse.json({ run_id: 321, message: "任务已取消" });
      }),
    );

    renderAt("/tasks/321");

    await user.click(await screen.findByRole("button", { name: "取消" }));

    await waitFor(() => expect(cancelHandler).toHaveBeenCalledOnce());
    expect(
      screen.queryByRole("button", { name: "删除" }),
    ).not.toBeInTheDocument();
  });

  it("deletes a terminal task from the detail page and navigates to the list", async () => {
    const user = userEvent.setup();
    const deleteHandler = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    server.use(
      http.delete("/api/tasks/123", () => {
        deleteHandler();
        return HttpResponse.json({ run_id: 123, message: "任务已删除" });
      }),
    );

    renderAt("/tasks/123");

    await user.click(await screen.findByRole("button", { name: "删除" }));

    await waitFor(() => {
      expect(deleteHandler).toHaveBeenCalledOnce();
      expect(window.location.pathname).toBe("/tasks");
    });
  });
});
