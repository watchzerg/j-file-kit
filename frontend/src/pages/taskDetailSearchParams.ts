import {
  DEFAULT_TASK_LOG_LIMIT,
  DEFAULT_TASK_RUN_PAGE_SIZE,
} from "@/api/tasks";
import type { FileTaskDecisionType } from "@/api/types";

export type ResultSuccessFilter = "all" | "true" | "false";

export interface ResultState {
  decisionType: FileTaskDecisionType | "all";
  success: ResultSuccessFilter;
  query: string;
  page: number;
  pageSize: number;
}

export interface LogState {
  offset: number;
  limit: number;
}

const DECISION_TYPES = ["move", "delete", "skip"] as const;

export function defaultResultState(): ResultState {
  return {
    decisionType: "all",
    success: "all",
    query: "",
    page: 1,
    pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
  };
}

export function parseResultState(searchParams: URLSearchParams): ResultState {
  return {
    decisionType: parseDecisionType(searchParams.get("results_decision")),
    success: parseSuccess(searchParams.get("results_success")),
    query: searchParams.get("results_q") ?? "",
    page: parsePositiveInt(searchParams.get("results_page"), 1),
    pageSize: parsePageSize(searchParams.get("results_page_size")),
  };
}

export function parseDecisionType(
  value: string | null,
): FileTaskDecisionType | "all" {
  if (value && (DECISION_TYPES as readonly string[]).includes(value)) {
    return value as FileTaskDecisionType;
  }
  return "all";
}

export function parseSuccess(value: string | null): ResultSuccessFilter {
  if (value === "true" || value === "false") {
    return value;
  }
  return "all";
}

export function parsePositiveInt(value: string | null, fallback: number) {
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export function parsePageSize(value: string | null) {
  const parsed = parsePositiveInt(value, DEFAULT_TASK_RUN_PAGE_SIZE);
  return [10, 20, 50, 100].includes(parsed)
    ? parsed
    : DEFAULT_TASK_RUN_PAGE_SIZE;
}

export function parseLogState(searchParams: URLSearchParams): LogState {
  return {
    offset: parseNonNegativeInt(searchParams.get("logs_offset"), 0),
    limit: parseLogLimit(searchParams.get("logs_limit")),
  };
}

export function parseNonNegativeInt(value: string | null, fallback: number) {
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : fallback;
}

export function parseLogLimit(value: string | null) {
  const parsed = parsePositiveInt(value, DEFAULT_TASK_LOG_LIMIT);
  return [50, 100, 200, 500].includes(parsed) ? parsed : DEFAULT_TASK_LOG_LIMIT;
}

export function toResultSearchParams(
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

export function toLogSearchParams(
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
