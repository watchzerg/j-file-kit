import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import App from "./App.tsx";

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
});
