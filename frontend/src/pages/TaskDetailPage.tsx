import {
  useTaskRunDetail,
  useTaskRunLogs,
  useTaskRunResults,
} from "@/api/tasks";
import LogPagination from "@/components/task/LogPagination";
import LogViewer from "@/components/task/LogViewer";
import RawPhaseStats from "@/components/task/RawPhaseStats";
import ResultFilterBar from "@/components/task/ResultFilterBar";
import ResultTable from "@/components/task/ResultTable";
import RunActions from "@/components/task/RunActions";
import RunHeader from "@/components/task/RunHeader";
import RunPagination from "@/components/task/RunPagination";
import RunTimeline from "@/components/task/RunTimeline";
import StatsSummaryGrid from "@/components/task/StatsSummaryGrid";
import { getErrorMessage } from "@/lib/errors";
import { useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { LogState, ResultState } from "./taskDetailSearchParams";
import {
  defaultResultState,
  parseLogState,
  parseResultState,
  toLogSearchParams,
  toResultSearchParams,
} from "./taskDetailSearchParams";

const tabs = [
  { id: "overview", label: "概览" },
  { id: "results", label: "文件结果" },
  { id: "logs", label: "日志" },
] as const;

type TabId = (typeof tabs)[number]["id"];

export default function TaskDetailPage() {
  const { runId } = useParams();
  const parsedRunId = parseRunId(runId);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const runDetailQuery = useTaskRunDetail(parsedRunId);
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const resultState = useMemo(
    () => parseResultState(searchParams),
    [searchParams],
  );
  const logState = useMemo(() => parseLogState(searchParams), [searchParams]);
  const resultsQuery = useTaskRunResults(
    parsedRunId,
    {
      decision_type:
        resultState.decisionType === "all"
          ? undefined
          : resultState.decisionType,
      success:
        resultState.success === "all"
          ? undefined
          : resultState.success === "true",
      q: resultState.query.trim() || undefined,
      page: resultState.page,
      page_size: resultState.pageSize,
    },
    runDetailQuery.data?.status,
  );
  const logsQuery = useTaskRunLogs(
    parsedRunId,
    {
      offset: logState.offset,
      limit: logState.limit,
    },
    runDetailQuery.data?.status,
  );

  function updateResultState(nextState: ResultState) {
    setSearchParams(toResultSearchParams(searchParams, nextState));
  }

  function updateLogState(nextState: LogState) {
    setSearchParams(toLogSearchParams(searchParams, nextState));
  }

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
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === "overview" ? (
            <div className="space-y-6">
              <RunActions
                run={runDetailQuery.data}
                onDeleted={() => navigate("/tasks")}
              />
              <RunTimeline run={runDetailQuery.data} />
              <StatsSummaryGrid statistics={runDetailQuery.data.statistics} />
              {runDetailQuery.data.task_type === "raw_file_organizer" ? (
                <RawPhaseStats statistics={runDetailQuery.data.statistics} />
              ) : null}
            </div>
          ) : activeTab === "results" ? (
            <div className="space-y-4">
              <ResultFilterBar
                decisionType={resultState.decisionType}
                success={resultState.success}
                query={resultState.query}
                pageSize={resultState.pageSize}
                onDecisionTypeChange={(decisionType) =>
                  updateResultState({ ...resultState, decisionType, page: 1 })
                }
                onSuccessChange={(success) =>
                  updateResultState({ ...resultState, success, page: 1 })
                }
                onQueryChange={(query) =>
                  updateResultState({ ...resultState, query, page: 1 })
                }
                onPageSizeChange={(pageSize) =>
                  updateResultState({ ...resultState, pageSize, page: 1 })
                }
                onReset={() => updateResultState(defaultResultState())}
              />

              {resultsQuery.isLoading ? (
                <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
                  正在加载文件结果...
                </div>
              ) : null}

              {resultsQuery.isError ? (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
                  {getErrorMessage(resultsQuery.error)}
                </div>
              ) : null}

              {resultsQuery.data?.results.length === 0 ? (
                <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
                  暂无符合条件的文件结果。
                </div>
              ) : null}

              {resultsQuery.data && resultsQuery.data.results.length > 0 ? (
                <>
                  <ResultTable results={resultsQuery.data.results} />
                  <RunPagination
                    page={resultsQuery.data.page}
                    pageSize={resultsQuery.data.page_size}
                    total={resultsQuery.data.total}
                    onPageChange={(page) =>
                      updateResultState({ ...resultState, page })
                    }
                  />
                </>
              ) : null}
            </div>
          ) : activeTab === "logs" ? (
            <div className="space-y-4">
              <div className="rounded-lg border bg-card p-4 text-sm">
                <h2 className="font-semibold">任务日志</h2>
                <p className="mt-1 text-muted-foreground">
                  按日志文件行号分页展示；任务运行中会自动刷新。
                </p>
              </div>

              {logsQuery.isLoading ? (
                <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
                  正在加载任务日志...
                </div>
              ) : null}

              {logsQuery.isError ? (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
                  {getErrorMessage(logsQuery.error)}
                </div>
              ) : null}

              {logsQuery.data?.lines.length === 0 ? (
                <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
                  暂无任务日志。
                </div>
              ) : null}

              {logsQuery.data && logsQuery.data.lines.length > 0 ? (
                <>
                  <LogViewer lines={logsQuery.data.lines} />
                  <LogPagination
                    offset={logsQuery.data.offset}
                    limit={logsQuery.data.limit}
                    total={logsQuery.data.total_lines}
                    onOffsetChange={(offset) =>
                      updateLogState({ ...logState, offset })
                    }
                  />
                </>
              ) : null}
            </div>
          ) : null}
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
