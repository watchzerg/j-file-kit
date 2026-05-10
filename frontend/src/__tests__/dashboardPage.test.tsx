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

describe("Dashboard page", () => {
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

    await clickEnabledButton(user, "启动", 0);

    await waitFor(() => {
      expect(startHandler).toHaveBeenCalledWith({
        dry_run: true,
        trigger_type: "manual",
      });
      expect(window.location.pathname).toBe("/tasks/77");
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

    await screen.findByText("active-run");
    await clickEnabledButton(user, "取消", 0);

    await waitFor(() => expect(cancelHandler).toHaveBeenCalledOnce());
  });
});
