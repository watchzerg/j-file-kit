import { useSystemInfo } from "@/api/system";
import {
  JavConfigPanel,
  RawConfigPanel,
} from "@/components/config/TaskConfigPanel";
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

      {activeTab === "global" ? (
        <GlobalConfigPanel
          isLoading={systemInfoQuery.isLoading}
          appVersion={systemInfo?.app_version}
          env={systemInfo?.env}
          baseDir={systemInfo?.base_dir}
          mediaRoot={systemInfo?.media_root}
          mediaMounted={systemInfo?.media_mounted}
        />
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

function GlobalConfigPanel({
  isLoading,
  appVersion,
  env,
  baseDir,
  mediaRoot,
  mediaMounted,
}: {
  isLoading: boolean;
  appVersion?: string;
  env?: string;
  baseDir?: string;
  mediaRoot?: string;
  mediaMounted?: boolean;
}) {
  if (isLoading) {
    return (
      <section className="rounded-lg border bg-card p-5 text-muted-foreground text-sm">
        正在加载系统信息...
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <h2 className="font-semibold text-xl">全局配置</h2>
      <p className="mt-1 text-muted-foreground text-sm">
        M5 先提供只读系统信息，完整全局配置编辑留给 M8。
      </p>
      <dl className="mt-5 grid gap-4 text-sm md:grid-cols-2">
        <InfoItem label="版本" value={appVersion ?? "-"} />
        <InfoItem label="环境" value={env ?? "-"} />
        <InfoItem label="数据目录" value={baseDir ?? "-"} />
        <InfoItem label="媒体根目录" value={mediaRoot ?? "-"} />
        <InfoItem
          label="媒体挂载"
          value={mediaMounted === true ? "已挂载" : "未检测到挂载"}
        />
      </dl>
    </section>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-all text-foreground">{value}</dd>
    </div>
  );
}
