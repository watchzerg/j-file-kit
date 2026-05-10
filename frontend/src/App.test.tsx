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
  vi.restoreAllMocks();
  window.history.pushState(null, "", "/");
});

describe("App routes", () => {
  it("renders Dashboard at the root route", async () => {
    renderAt("/");

    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("任务管理")).not.toBeInTheDocument();
    expect(screen.getByText("启动任务")).toBeInTheDocument();
    expect(screen.getByText("最近任务")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "系统信息" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("/media/jav_workspace").length).toBeGreaterThan(
      0,
    );
    expect(screen.getByText("媒体已挂载")).toBeInTheDocument();
    expect(
      screen.queryByText("[区块占位] 系统信息（M8 实现）"),
    ).not.toBeInTheDocument();
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

  it("renders the config center with typed JAV fields", async () => {
    renderAt("/config");

    expect(
      await screen.findByRole("heading", { name: "JAV 视频整理" }),
    ).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("/media/jav_workspace"),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("1048576")).toBeInTheDocument();
    expect(screen.getByDisplayValue("209715200")).toBeInTheDocument();
    expect(screen.getByDisplayValue("sample")).toBeInTheDocument();
  });

  it("renders readonly global system config and defaults", async () => {
    const user = userEvent.setup();
    renderAt("/config");

    await user.click(await screen.findByRole("tab", { name: "全局配置" }));

    expect(
      await screen.findByRole("heading", { name: "路径与挂载" }),
    ).toBeInTheDocument();
    expect(screen.getByText("/data")).toBeInTheDocument();
    expect(screen.getAllByText("/media/raw_workspace").length).toBeGreaterThan(
      0,
    );
    expect(
      await screen.findByRole("heading", { name: "系统默认字典" }),
    ).toBeInTheDocument();
    expect(screen.getByText("视频（共 3 项）")).toBeInTheDocument();
    expect(screen.getByText(".mp4")).toBeInTheDocument();
    expect(screen.getByText("垃圾关键字（共 3 项）")).toBeInTheDocument();
    expect(screen.getByText("100 MiB (104857600 bytes)")).toBeInTheDocument();
    expect(screen.getByText("VR 番号前缀（共 2 项）")).toBeInTheDocument();
  });

  it("updates the JAV task config", async () => {
    const user = userEvent.setup();
    const updateHandler = vi.fn();
    server.use(
      http.patch(
        "/api/file-task/config/jav-video-organizer",
        async ({ request }) => {
          updateHandler(await request.json());
          return HttpResponse.json({
            code: "SUCCESS",
            message: "配置更新成功",
          });
        },
      ),
    );

    renderAt("/config");

    const workspaceInput = await screen.findByLabelText("工作区");
    await user.clear(workspaceInput);
    await user.type(workspaceInput, "/media/jav_workspace/project-a");
    await user.clear(screen.getByLabelText("收件箱预删除 exact stems"));
    await user.type(
      screen.getByLabelText("收件箱预删除 exact stems"),
      "sample, trailer",
    );
    await user.click(screen.getByRole("button", { name: "保存配置" }));

    await waitFor(() => {
      expect(updateHandler).toHaveBeenCalledWith({
        enabled: true,
        config: {
          workspace_root: "/media/jav_workspace/project-a",
          misc_file_delete_rules: { max_size: 1048576 },
          video_small_delete_bytes: 209715200,
          inbox_delete_rules: {
            exact_stems: ["sample", "trailer"],
            max_size_bytes: 0,
          },
        },
      });
      expect(screen.getByText("JAV 视频整理配置已保存")).toBeInTheDocument();
    });
  });

  it("selects a workspace from the media picker", async () => {
    const user = userEvent.setup();
    renderAt("/config");

    await user.click(await screen.findByRole("button", { name: "选择目录" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(await screen.findByText("project-a")).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "选择" })[1]);

    expect(
      screen.getByDisplayValue("/media/jav_workspace/project-a"),
    ).toBeInTheDocument();
  });

  it("blocks config updates outside the task media root", async () => {
    const user = userEvent.setup();
    const updateHandler = vi.fn();
    server.use(
      http.patch("/api/file-task/config/jav-video-organizer", () => {
        updateHandler();
        return HttpResponse.json({ code: "SUCCESS", message: "配置更新成功" });
      }),
    );

    renderAt("/config");

    const workspaceInput = await screen.findByLabelText("工作区");
    await user.clear(workspaceInput);
    await user.type(workspaceInput, "/etc");
    await user.click(screen.getByRole("button", { name: "保存配置" }));

    await waitFor(() => {
      expect(updateHandler).not.toHaveBeenCalled();
      expect(
        screen.getAllByText("工作区必须位于 /media/jav_workspace 下").length,
      ).toBeGreaterThan(0);
    });
  });

  it("renders and updates the Raw config tab", async () => {
    const user = userEvent.setup();
    const updateHandler = vi.fn();
    server.use(
      http.patch(
        "/api/file-task/config/raw-file-organizer",
        async ({ request }) => {
          updateHandler(await request.json());
          return HttpResponse.json({
            code: "SUCCESS",
            message: "配置更新成功",
          });
        },
      ),
    );

    renderAt("/config");

    await user.click(await screen.findByRole("tab", { name: "Raw 文件整理" }));
    const workspaceInput = await screen.findByLabelText("工作区");
    await user.clear(workspaceInput);
    await user.type(workspaceInput, "/media/raw_workspace/inbox-a");
    await user.click(screen.getByRole("checkbox", { name: "启用任务" }));
    await user.click(screen.getByRole("button", { name: "保存配置" }));

    await waitFor(() => {
      expect(updateHandler).toHaveBeenCalledWith({
        enabled: false,
        config: { workspace_root: "/media/raw_workspace/inbox-a" },
      });
      expect(screen.getByText("Raw 文件整理配置已保存")).toBeInTheDocument();
    });
  });

  it("renders the task list with filters and summaries", async () => {
    renderAt("/tasks");

    expect(
      await screen.findByText("raw_file_organizer-manual-20260510010101000"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Raw 文件整理").length).toBeGreaterThan(0);
    expect(screen.getAllByText("JAV 视频整理").length).toBeGreaterThan(0);
    expect(screen.getByText("Dry Run")).toBeInTheDocument();
    expect(
      screen.getByText("总 12 / 成功 9 / 失败 1 / 跳过 2"),
    ).toBeInTheDocument();
  });

  it("syncs task list filters to the URL", async () => {
    const user = userEvent.setup();
    renderAt("/tasks");

    await user.selectOptions(
      await screen.findByLabelText("任务类型"),
      "raw_file_organizer",
    );
    await user.selectOptions(screen.getByLabelText("状态"), "completed");

    await waitFor(() => {
      expect(window.location.search).toContain("task_type=raw_file_organizer");
      expect(window.location.search).toContain("status=completed");
      expect(
        screen.getByText("raw_file_organizer-manual-20260510010101000"),
      ).toBeInTheDocument();
      expect(
        screen.queryByText("jav_video_organizer-manual-20260510020101000"),
      ).not.toBeInTheDocument();
    });
  });

  it("changes task list pages", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/tasks", ({ request }) => {
        const url = new URL(request.url);
        const page = Number(url.searchParams.get("page") ?? "1");
        return HttpResponse.json({
          runs: [
            {
              run_id: page,
              run_name: `page-${page}-run`,
              task_type: "raw_file_organizer",
              trigger_type: "manual",
              dry_run: true,
              status: "completed",
              start_time: "2026-05-10T01:01:01",
              end_time: "2026-05-10T01:01:03",
              duration_ms: 2000,
              statistics_summary: {
                total_items: 1,
                success_items: 1,
                error_items: 0,
                skipped_items: 0,
                warning_items: 0,
                total_duration_ms: 2000,
              },
            },
          ],
          total: 25,
          page,
          page_size: 20,
        });
      }),
    );

    renderAt("/tasks");

    expect(await screen.findByText("page-1-run")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "下一页" }));

    await waitFor(() => {
      expect(window.location.search).toContain("page=2");
      expect(screen.getByText("page-2-run")).toBeInTheDocument();
    });
  });

  it("cancels a running task from the task list", async () => {
    const user = userEvent.setup();
    const cancelHandler = vi.fn();
    server.use(
      http.post("/api/tasks/321/cancel", () => {
        cancelHandler();
        return HttpResponse.json({ run_id: 321, message: "任务已取消" });
      }),
    );

    renderAt("/tasks");

    await user.click(await screen.findByRole("button", { name: "取消" }));

    await waitFor(() => expect(cancelHandler).toHaveBeenCalledOnce());
  });

  it("deletes a terminal task from the task list", async () => {
    const user = userEvent.setup();
    const deleteHandler = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    server.use(
      http.delete("/api/tasks/123", () => {
        deleteHandler();
        return HttpResponse.json({ run_id: 123, message: "任务已删除" });
      }),
    );

    renderAt("/tasks");

    await user.click(await screen.findByRole("button", { name: "删除" }));

    await waitFor(() => expect(deleteHandler).toHaveBeenCalledOnce());
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
    expect(
      screen.getAllByRole("link", { name: "查看详情" })[0],
    ).toHaveAttribute("href", "/tasks/99");
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
