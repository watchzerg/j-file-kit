import { useState } from "react";
import { useParams } from "react-router-dom";

const tabs = [
  { id: "overview", label: "概览", milestone: "M3 实现" },
  { id: "results", label: "文件结果", milestone: "M6 实现" },
  { id: "logs", label: "日志", milestone: "M7 实现" },
] as const;

type TabId = (typeof tabs)[number]["id"];

export default function TaskDetailPage() {
  const { runId } = useParams();
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const activeTabLabel =
    tabs.find((tab) => tab.id === activeTab)?.label ?? "概览";

  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <h1 className="text-2xl font-bold">任务详情 #{runId}</h1>

      <div
        className="flex flex-wrap gap-2"
        role="tablist"
        aria-label="任务详情"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={[
              "rounded-md border px-3 py-2 text-sm transition-colors",
              activeTab === tab.id
                ? "border-foreground text-foreground"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}（{tab.milestone}）
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
        [区块占位] 当前 Tab 内容：{activeTabLabel}
      </div>
    </div>
  );
}
