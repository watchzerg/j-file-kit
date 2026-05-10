import { cleanup, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";
import { server } from "../test/server";
import { renderAt } from "../test/utils.tsx";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.pushState(null, "", "/");
});

describe("Tasks list page", () => {
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
});
