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
      { path: "/tasks/123", heading: "任务详情 #123" },
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

  it("switches task detail placeholder tabs locally", async () => {
    const user = userEvent.setup();
    renderAt("/tasks/123");

    expect(
      screen.getByText("[区块占位] 当前 Tab 内容：概览"),
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
