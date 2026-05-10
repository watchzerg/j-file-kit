import { useSystemFileTypeDefaults, useSystemInfo } from "@/api/system";
import { JavConfigPanel } from "@/components/config/JavConfigPanel";
import { RawConfigPanel } from "@/components/config/RawConfigPanel";
import { SystemDefaultsPanel } from "@/components/system/SystemDefaultsPanel";
import { SystemInfoPanel } from "@/components/system/SystemInfoPanel";
import { getErrorMessage } from "@/lib/errors";
import { useState } from "react";

type ConfigTab = "global" | "jav" | "raw";

const tabs = [
  { id: "global", label: "全局配置" },
  { id: "jav", label: "JAV 视频整理" },
  { id: "raw", label: "Raw 文件整理" },
] satisfies { id: ConfigTab; label: string }[];

export default function ConfigPage() {
  const [activeTab, setActiveTab] = useState<ConfigTab>("jav");
  const systemInfoQuery = useSystemInfo();
  const defaultsQuery = useSystemFileTypeDefaults();
  const systemInfo = systemInfoQuery.data;

  return (
    <div className="container mx-auto space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold">任务配置</h1>
        <p className="mt-2 text-muted-foreground text-sm">
          管理文件任务的启用状态、工作区路径和任务专属规则。路径保存前会先按系统根目录做前缀校验。
        </p>
      </header>

      <nav
        className="flex flex-wrap gap-2"
        role="tablist"
        aria-label="配置分类"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={
              activeTab === tab.id
                ? "rounded-md bg-foreground px-3 py-2 font-medium text-background text-sm"
                : "rounded-md border px-3 py-2 text-sm transition-colors hover:bg-muted"
            }
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {systemInfoQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
          {getErrorMessage(systemInfoQuery.error)}
        </div>
      ) : null}
      {activeTab === "global" && defaultsQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
          {getErrorMessage(defaultsQuery.error)}
        </div>
      ) : null}

      {activeTab === "global" ? (
        <div className="space-y-6">
          <SystemInfoPanel
            info={systemInfo}
            isLoading={systemInfoQuery.isLoading}
          />
          <SystemDefaultsPanel
            defaults={defaultsQuery.data}
            isLoading={defaultsQuery.isLoading}
          />
        </div>
      ) : null}
      {activeTab === "jav" ? (
        <JavConfigPanel rootPath={systemInfo?.jav_media_root ?? null} />
      ) : null}
      {activeTab === "raw" ? (
        <RawConfigPanel rootPath={systemInfo?.raw_media_root ?? null} />
      ) : null}
    </div>
  );
}
