import { describe, expect, it } from "vitest";
import {
  DEFAULT_TASK_LOG_LIMIT,
  DEFAULT_TASK_RUN_PAGE_SIZE,
} from "../api/tasks";
import {
  defaultResultState,
  parseDecisionType,
  parseLogLimit,
  parseLogState,
  parseNonNegativeInt,
  parsePageSize,
  parsePositiveInt,
  parseResultState,
  parseSuccess,
  toLogSearchParams,
  toResultSearchParams,
} from "../pages/taskDetailSearchParams";

// ---------------------------------------------------------------------------
// defaultResultState
// ---------------------------------------------------------------------------

describe("defaultResultState", () => {
  it("returns the correct default shape", () => {
    expect(defaultResultState()).toEqual({
      decisionType: "all",
      success: "all",
      query: "",
      page: 1,
      pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
    });
  });

  it("returns a fresh object each call", () => {
    const a = defaultResultState();
    const b = defaultResultState();
    expect(a).not.toBe(b);
  });
});

// ---------------------------------------------------------------------------
// parseDecisionType
// ---------------------------------------------------------------------------

describe("parseDecisionType", () => {
  it.each(["move", "delete", "skip"] as const)(
    "returns %s for valid value",
    (v) => {
      expect(parseDecisionType(v)).toBe(v);
    },
  );

  it("returns 'all' for null", () => {
    expect(parseDecisionType(null)).toBe("all");
  });

  it("returns 'all' for empty string", () => {
    expect(parseDecisionType("")).toBe("all");
  });

  it("returns 'all' for unknown value", () => {
    expect(parseDecisionType("archive")).toBe("all");
  });
});

// ---------------------------------------------------------------------------
// parseSuccess
// ---------------------------------------------------------------------------

describe("parseSuccess", () => {
  it("returns 'true' for string 'true'", () => {
    expect(parseSuccess("true")).toBe("true");
  });

  it("returns 'false' for string 'false'", () => {
    expect(parseSuccess("false")).toBe("false");
  });

  it("returns 'all' for null", () => {
    expect(parseSuccess(null)).toBe("all");
  });

  it("returns 'all' for 'all'", () => {
    expect(parseSuccess("all")).toBe("all");
  });

  it("returns 'all' for any other string", () => {
    expect(parseSuccess("yes")).toBe("all");
    expect(parseSuccess("1")).toBe("all");
  });
});

// ---------------------------------------------------------------------------
// parsePositiveInt
// ---------------------------------------------------------------------------

describe("parsePositiveInt", () => {
  it("returns parsed value for positive integer string", () => {
    expect(parsePositiveInt("5", 1)).toBe(5);
    expect(parsePositiveInt("100", 1)).toBe(100);
  });

  it("returns fallback for null", () => {
    expect(parsePositiveInt(null, 3)).toBe(3);
  });

  it("returns fallback for empty string", () => {
    expect(parsePositiveInt("", 3)).toBe(3);
  });

  it("returns fallback for zero", () => {
    expect(parsePositiveInt("0", 2)).toBe(2);
  });

  it("returns fallback for negative number", () => {
    expect(parsePositiveInt("-1", 2)).toBe(2);
  });

  it("returns fallback for non-integer float", () => {
    expect(parsePositiveInt("1.5", 2)).toBe(2);
  });

  it("returns fallback for non-numeric string", () => {
    expect(parsePositiveInt("abc", 2)).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// parsePageSize (allowed: [10, 20, 50, 100])
// ---------------------------------------------------------------------------

describe("parsePageSize (taskDetail)", () => {
  it.each([10, 20, 50, 100])("accepts %i", (n) => {
    expect(parsePageSize(String(n))).toBe(n);
  });

  it("returns default for disallowed value", () => {
    expect(parsePageSize("15")).toBe(DEFAULT_TASK_RUN_PAGE_SIZE);
    expect(parsePageSize("200")).toBe(DEFAULT_TASK_RUN_PAGE_SIZE);
  });

  it("returns default for null", () => {
    expect(parsePageSize(null)).toBe(DEFAULT_TASK_RUN_PAGE_SIZE);
  });
});

// ---------------------------------------------------------------------------
// parseNonNegativeInt
// ---------------------------------------------------------------------------

describe("parseNonNegativeInt", () => {
  it("returns parsed value for zero", () => {
    expect(parseNonNegativeInt("0", 5)).toBe(0);
  });

  it("returns parsed value for positive integer", () => {
    expect(parseNonNegativeInt("42", 5)).toBe(42);
  });

  it("returns fallback for null", () => {
    expect(parseNonNegativeInt(null, 5)).toBe(5);
  });

  it("returns fallback for empty string", () => {
    expect(parseNonNegativeInt("", 5)).toBe(5);
  });

  it("returns fallback for negative number", () => {
    expect(parseNonNegativeInt("-1", 5)).toBe(5);
  });

  it("returns fallback for float", () => {
    expect(parseNonNegativeInt("1.5", 5)).toBe(5);
  });
});

// ---------------------------------------------------------------------------
// parseLogLimit (allowed: [50, 100, 200, 500])
// ---------------------------------------------------------------------------

describe("parseLogLimit", () => {
  it.each([50, 100, 200, 500])("accepts %i", (n) => {
    expect(parseLogLimit(String(n))).toBe(n);
  });

  it("returns default for disallowed value", () => {
    expect(parseLogLimit("150")).toBe(DEFAULT_TASK_LOG_LIMIT);
    expect(parseLogLimit("1000")).toBe(DEFAULT_TASK_LOG_LIMIT);
  });

  it("returns default for null", () => {
    expect(parseLogLimit(null)).toBe(DEFAULT_TASK_LOG_LIMIT);
  });
});

// ---------------------------------------------------------------------------
// parseResultState
// ---------------------------------------------------------------------------

describe("parseResultState", () => {
  it("returns defaults when no params are set", () => {
    const params = new URLSearchParams();
    expect(parseResultState(params)).toEqual(defaultResultState());
  });

  it("parses all valid fields", () => {
    const params = new URLSearchParams({
      results_decision: "delete",
      results_success: "false",
      results_q: "ABC",
      results_page: "3",
      results_page_size: "50",
    });
    expect(parseResultState(params)).toEqual({
      decisionType: "delete",
      success: "false",
      query: "ABC",
      page: 3,
      pageSize: 50,
    });
  });

  it("falls back to defaults for invalid values", () => {
    const params = new URLSearchParams({
      results_decision: "badval",
      results_success: "maybe",
      results_page: "-1",
      results_page_size: "999",
    });
    expect(parseResultState(params)).toEqual(defaultResultState());
  });
});

// ---------------------------------------------------------------------------
// parseLogState
// ---------------------------------------------------------------------------

describe("parseLogState", () => {
  it("returns defaults when no params are set", () => {
    const params = new URLSearchParams();
    expect(parseLogState(params)).toEqual({
      offset: 0,
      limit: DEFAULT_TASK_LOG_LIMIT,
    });
  });

  it("parses valid offset and limit", () => {
    const params = new URLSearchParams({
      logs_offset: "200",
      logs_limit: "500",
    });
    expect(parseLogState(params)).toEqual({ offset: 200, limit: 500 });
  });

  it("offset may be 0", () => {
    const params = new URLSearchParams({ logs_offset: "0" });
    expect(parseLogState(params).offset).toBe(0);
  });

  it("falls back for invalid limit", () => {
    const params = new URLSearchParams({ logs_limit: "999" });
    expect(parseLogState(params).limit).toBe(DEFAULT_TASK_LOG_LIMIT);
  });
});

// ---------------------------------------------------------------------------
// toResultSearchParams
// ---------------------------------------------------------------------------

describe("toResultSearchParams", () => {
  it("removes keys that equal their defaults (clean URL)", () => {
    const current = new URLSearchParams();
    const result = toResultSearchParams(current, defaultResultState());
    expect(result.has("results_decision")).toBe(false);
    expect(result.has("results_success")).toBe(false);
    expect(result.has("results_q")).toBe(false);
    expect(result.has("results_page")).toBe(false);
    expect(result.has("results_page_size")).toBe(false);
  });

  it("sets keys that differ from defaults", () => {
    const current = new URLSearchParams();
    const result = toResultSearchParams(current, {
      decisionType: "move",
      success: "true",
      query: "foo",
      page: 2,
      pageSize: 50,
    });
    expect(result.get("results_decision")).toBe("move");
    expect(result.get("results_success")).toBe("true");
    expect(result.get("results_q")).toBe("foo");
    expect(result.get("results_page")).toBe("2");
    expect(result.get("results_page_size")).toBe("50");
  });

  it("removes a key when it returns to default", () => {
    const current = new URLSearchParams({ results_decision: "delete" });
    const result = toResultSearchParams(current, defaultResultState());
    expect(result.has("results_decision")).toBe(false);
  });

  it("preserves unrelated params from current", () => {
    const current = new URLSearchParams({ logs_offset: "100" });
    const result = toResultSearchParams(current, defaultResultState());
    expect(result.get("logs_offset")).toBe("100");
  });

  it("trims whitespace from query", () => {
    const current = new URLSearchParams();
    const result = toResultSearchParams(current, {
      ...defaultResultState(),
      query: "  bar  ",
    });
    expect(result.get("results_q")).toBe("bar");
  });
});

// ---------------------------------------------------------------------------
// toLogSearchParams
// ---------------------------------------------------------------------------

describe("toLogSearchParams", () => {
  it("removes offset and limit when they equal defaults", () => {
    const current = new URLSearchParams();
    const result = toLogSearchParams(current, {
      offset: 0,
      limit: DEFAULT_TASK_LOG_LIMIT,
    });
    expect(result.has("logs_offset")).toBe(false);
    expect(result.has("logs_limit")).toBe(false);
  });

  it("sets offset when non-zero", () => {
    const current = new URLSearchParams();
    const result = toLogSearchParams(current, {
      offset: 100,
      limit: DEFAULT_TASK_LOG_LIMIT,
    });
    expect(result.get("logs_offset")).toBe("100");
  });

  it("sets limit when non-default", () => {
    const current = new URLSearchParams();
    const result = toLogSearchParams(current, { offset: 0, limit: 200 });
    expect(result.get("logs_limit")).toBe("200");
  });

  it("preserves unrelated params from current", () => {
    const current = new URLSearchParams({ results_decision: "move" });
    const result = toLogSearchParams(current, {
      offset: 0,
      limit: DEFAULT_TASK_LOG_LIMIT,
    });
    expect(result.get("results_decision")).toBe("move");
  });
});
