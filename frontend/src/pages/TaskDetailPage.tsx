import {
  DEFAULT_TASK_LOG_LIMIT,
  DEFAULT_TASK_RUN_PAGE_SIZE,
  useTaskRunDetail,
  useTaskRunLogs,
  useTaskRunResults,
} from "@/api/tasks";
import type { FileTaskDecisionType } from "@/api/types";
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

const tabs = [
  { id: "overview", label: "概览", milestone: "M3 实现" },
  { id: "results", label: "文件结果", milestone: "M6 已完成" },
  { id: "logs", label: "日志", milestone: "M7 实现" },
] as const;

type TabId = (typeof tabs)[number]["id"];
type ResultSuccessFilter = "all" | "true" | "false";

const DECISION_TYPES = ["move", "delete", "skip"] as const;

interface ResultState {
  decisionType: FileTaskDecisionType | "all";
  success: ResultSuccessFilter;
  query: string;
  page: number;
  pageSize: number;
}

interface LogState {
  offset: number;
  limit: number;
}

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
  const activeTabLabel =
    tabs.find((tab) => tab.id === activeTab)?.label ?? "概览";

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
                {tab.label}（{tab.milestone}）
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

function defaultResultState(): ResultState {
  return {
    decisionType: "all",
    success: "all",
    query: "",
    page: 1,
    pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
  };
}

function parseResultState(searchParams: URLSearchParams): ResultState {
  return {
    decisionType: parseDecisionType(searchParams.get("results_decision")),
    success: parseSuccess(searchParams.get("results_success")),
    query: searchParams.get("results_q") ?? "",
    page: parsePositiveInt(searchParams.get("results_page"), 1),
    pageSize: parsePageSize(searchParams.get("results_page_size")),
  };
}

function parseDecisionType(value: string | null): FileTaskDecisionType | "all" {
  if (value && (DECISION_TYPES as readonly string[]).includes(value)) {
    return value as FileTaskDecisionType;
  }
  return "all";
}

function parseSuccess(value: string | null): ResultSuccessFilter {
  if (value === "true" || value === "false") {
    return value;
  }
  return "all";
}

function parsePositiveInt(value: string | null, fallback: number) {
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function parsePageSize(value: string | null) {
  const parsed = parsePositiveInt(value, DEFAULT_TASK_RUN_PAGE_SIZE);
  return [10, 20, 50, 100].includes(parsed)
    ? parsed
    : DEFAULT_TASK_RUN_PAGE_SIZE;
}

function parseLogState(searchParams: URLSearchParams): LogState {
  return {
    offset: parseNonNegativeInt(searchParams.get("logs_offset"), 0),
    limit: parseLogLimit(searchParams.get("logs_limit")),
  };
}

function parseNonNegativeInt(value: string | null, fallback: number) {
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : fallback;
}

function parseLogLimit(value: string | null) {
  const parsed = parsePositiveInt(value, DEFAULT_TASK_LOG_LIMIT);
  return [50, 100, 200, 500].includes(parsed) ? parsed : DEFAULT_TASK_LOG_LIMIT;
}

function toResultSearchParams(
  currentSearchParams: URLSearchParams,
  state: ResultState,
) {
  const nextSearchParams = new URLSearchParams(currentSearchParams);
  setOrDelete(nextSearchParams, "results_decision", state.decisionType, "all");
  setOrDelete(nextSearchParams, "results_success", state.success, "all");
  setOrDelete(nextSearchParams, "results_q", state.query.trim(), "");
  setOrDelete(nextSearchParams, "results_page", String(state.page), "1");
  setOrDelete(
    nextSearchParams,
    "results_page_size",
    String(state.pageSize),
    String(DEFAULT_TASK_RUN_PAGE_SIZE),
  );
  return nextSearchParams;
}

function toLogSearchParams(
  currentSearchParams: URLSearchParams,
  state: LogState,
) {
  const nextSearchParams = new URLSearchParams(currentSearchParams);
  setOrDelete(nextSearchParams, "logs_offset", String(state.offset), "0");
  setOrDelete(
    nextSearchParams,
    "logs_limit",
    String(state.limit),
    String(DEFAULT_TASK_LOG_LIMIT),
  );
  return nextSearchParams;
}

function setOrDelete(
  searchParams: URLSearchParams,
  key: string,
  value: string,
  defaultValue: string,
) {
  if (value === defaultValue) {
    searchParams.delete(key);
    return;
  }
  searchParams.set(key, value);
}
