import { cleanup, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderAt } from "../test/utils.tsx";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.pushState(null, "", "/");
});

describe("App routes", () => {
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
});
