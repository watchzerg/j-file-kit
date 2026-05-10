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

describe("Config page", () => {
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
});
