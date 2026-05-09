import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App.tsx";
import { server } from "./test/server";

function renderAt(path: string) {
  window.history.pushState(null, "", path);
  return render(<App />);
}

afterEach(() => {
  cleanup();
  window.history.pushState(null, "", "/");
});

describe("App routes", () => {
  it("renders Dashboard at the root route", () => {
    renderAt("/");

    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("任务管理")).not.toBeInTheDocument();
    expect(screen.getByText("启动任务")).toBeInTheDocument();
    expect(screen.getByText("最近任务")).toBeInTheDocument();
  });

  it("renders all M1 routes", () => {
    const routes = [
      { path: "/tasks", heading: "任务列表" },
      { path: "/config", heading: "任务配置" },
      { path: "/media", heading: "媒体目录" },
    ];

    for (const route of routes) {
      const { unmount } = renderAt(route.path);

      expect(
        screen.getByRole("heading", { name: route.heading }),
      ).toBeInTheDocument();
      expect(document.querySelectorAll("main")).toHaveLength(1);

      unmount();
    }
  });

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

  it("navigates with TopNav and marks only the matching link active", async () => {
    const user = userEvent.setup();
    renderAt("/");

    const dashboardLink = screen.getByRole("link", { name: /Dashboard/ });
    const tasksLink = screen.getByRole("link", { name: "任务列表" });

    expect(dashboardLink).toHaveClass("font-medium", "text-foreground");
    expect(tasksLink).toHaveClass("text-muted-foreground");

    await user.click(tasksLink);

    expect(window.location.pathname).toBe("/tasks");
    expect(
      screen.getByRole("heading", { name: "任务列表" }),
    ).toBeInTheDocument();
    expect(tasksLink).toHaveClass("font-medium", "text-foreground");
    expect(dashboardLink).toHaveClass("text-muted-foreground");
  });

  it("keeps later task detail tabs as placeholders", async () => {
    const user = userEvent.setup();
    renderAt("/tasks/123");

    expect(
      await screen.findByRole("heading", {
        name: "raw_file_organizer-manual-20260510010101000",
      }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "日志（M7 实现）" }));

    expect(
      screen.getByText("[区块占位] 当前 Tab 内容：日志"),
    ).toBeInTheDocument();
  });

  it("renders an active run banner and disables task starts", async () => {
    server.use(
      http.get("/api/tasks/active", () =>
        HttpResponse.json({
          run_id: 99,
          run_name: "raw_file_organizer-manual-20260510010101000",
          task_type: "raw_file_organizer",
          trigger_type: "manual",
          status: "running",
          start_time: new Date().toISOString(),
          end_time: null,
          error_message: null,
        }),
      ),
    );

    renderAt("/");

    expect(
      await screen.findByText("raw_file_organizer-manual-20260510010101000"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看详情" })).toHaveAttribute(
      "href",
      "/tasks/99",
    );
    for (const button of await screen.findAllByRole("button", {
      name: "启动",
    })) {
      expect(button).toBeDisabled();
    }
  });

  it("starts a task with dry run enabled by default and navigates to detail", async () => {
    const user = userEvent.setup();
    const startHandler = vi.fn();
    server.use(
      http.post("/api/tasks/jav_video_organizer/start", async ({ request }) => {
        startHandler(await request.json());
        return HttpResponse.json({
          run_id: 77,
          run_name: "jav-run",
          status: "pending",
          dry_run: true,
        });
      }),
    );

    renderAt("/");

    for (const checkbox of await screen.findAllByRole("checkbox", {
      name: "Dry Run（预览）",
    })) {
      expect(checkbox).toBeChecked();
    }

    await user.click(
      (await screen.findAllByRole("button", { name: "启动" }))[0],
    );

    await waitFor(() => {
      expect(startHandler).toHaveBeenCalledWith({
        dry_run: true,
        trigger_type: "manual",
      });
      expect(window.location.pathname).toBe("/tasks/77");
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

    await user.click(await screen.findByRole("button", { name: "重跑" }));

    await waitFor(() => {
      expect(startHandler).toHaveBeenCalledWith({
        dry_run: true,
        trigger_type: "manual",
      });
      expect(window.location.pathname).toBe("/tasks/55");
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
  });

  it("cancels the active run from the global banner", async () => {
    const user = userEvent.setup();
    const cancelHandler = vi.fn();
    server.use(
      http.get("/api/tasks/active", () =>
        HttpResponse.json({
          run_id: 88,
          run_name: "active-run",
          task_type: "jav_video_organizer",
          trigger_type: "manual",
          status: "running",
          start_time: new Date().toISOString(),
          end_time: null,
          error_message: null,
        }),
      ),
      http.post("/api/tasks/88/cancel", () => {
        cancelHandler();
        return HttpResponse.json({ run_id: 88, message: "任务已取消" });
      }),
    );

    renderAt("/");

    await user.click(await screen.findByRole("button", { name: "取消" }));

    await waitFor(() => expect(cancelHandler).toHaveBeenCalledOnce());
  });
});
