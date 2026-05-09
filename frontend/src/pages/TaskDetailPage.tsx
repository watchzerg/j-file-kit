import { useTaskRunDetail } from "@/api/tasks";
import RawPhaseStats from "@/components/task/RawPhaseStats";
import RunActions from "@/components/task/RunActions";
import RunHeader from "@/components/task/RunHeader";
import RunTimeline from "@/components/task/RunTimeline";
import StatsSummaryGrid from "@/components/task/StatsSummaryGrid";
import { getErrorMessage } from "@/lib/errors";
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
  const parsedRunId = parseRunId(runId);
  const runDetailQuery = useTaskRunDetail(parsedRunId);
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const activeTabLabel =
    tabs.find((tab) => tab.id === activeTab)?.label ?? "概览";

  if (parsedRunId === null) {
    return (
      <div className="container mx-auto space-y-6 px-4 py-6">
        <h1 className="text-2xl font-bold">任务详情</h1>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
          无效任务 ID。
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      {runDetailQuery.isLoading ? (
        <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
          正在加载任务详情...
        </div>
      ) : null}

      {runDetailQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
          {getErrorMessage(runDetailQuery.error)}
        </div>
      ) : null}

      {runDetailQuery.data ? (
        <>
          <RunHeader run={runDetailQuery.data} />

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

          {activeTab === "overview" ? (
            <div className="space-y-6">
              <RunActions run={runDetailQuery.data} />
              <RunTimeline run={runDetailQuery.data} />
              <StatsSummaryGrid statistics={runDetailQuery.data.statistics} />
              {runDetailQuery.data.task_type === "raw_file_organizer" ? (
                <RawPhaseStats statistics={runDetailQuery.data.statistics} />
              ) : null}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
              [区块占位] 当前 Tab 内容：{activeTabLabel}
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

function parseRunId(value: string | undefined) {
  if (!value || !/^\d+$/.test(value)) {
    return null;
  }
  return Number(value);
}
