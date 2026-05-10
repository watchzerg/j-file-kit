import { describe, expect, it } from "vitest";
import { DEFAULT_TASK_RUN_PAGE_SIZE } from "../api/tasks";
import {
  parseListState,
  parsePageSize,
  parsePositiveInt,
  parseStatus,
  parseTaskType,
  toSearchParams,
} from "../pages/TasksListPage";

// ---------------------------------------------------------------------------
// parseTaskType
// ---------------------------------------------------------------------------

describe("parseTaskType", () => {
  it("returns 'jav_video_organizer' for valid value", () => {
    expect(parseTaskType("jav_video_organizer")).toBe("jav_video_organizer");
  });

  it("returns 'raw_file_organizer' for valid value", () => {
    expect(parseTaskType("raw_file_organizer")).toBe("raw_file_organizer");
  });

  it("returns 'all' for null", () => {
    expect(parseTaskType(null)).toBe("all");
  });

  it("returns 'all' for empty string", () => {
    expect(parseTaskType("")).toBe("all");
  });

  it("returns 'all' for unknown value", () => {
    expect(parseTaskType("unknown_task")).toBe("all");
  });
});

// ---------------------------------------------------------------------------
// parseStatus
// ---------------------------------------------------------------------------

describe("parseStatus", () => {
  it.each(["pending", "running", "completed", "failed", "cancelled"] as const)(
    "returns '%s' for valid value",
    (s) => {
      expect(parseStatus(s)).toBe(s);
    },
  );

  it("returns 'all' for null", () => {
    expect(parseStatus(null)).toBe("all");
  });

  it("returns 'all' for empty string", () => {
    expect(parseStatus("")).toBe("all");
  });

  it("returns 'all' for unknown value", () => {
    expect(parseStatus("archived")).toBe("all");
  });
});

// ---------------------------------------------------------------------------
// parsePositiveInt (list page variant)
// ---------------------------------------------------------------------------

describe("parsePositiveInt (tasksListPage)", () => {
  it("returns parsed value for positive integer string", () => {
    expect(parsePositiveInt("3", 1)).toBe(3);
  });

  it("returns fallback for null", () => {
    expect(parsePositiveInt(null, 1)).toBe(1);
  });

  it("returns fallback for zero", () => {
    expect(parsePositiveInt("0", 1)).toBe(1);
  });

  it("returns fallback for negative", () => {
    expect(parsePositiveInt("-5", 1)).toBe(1);
  });

  it("returns fallback for float", () => {
    expect(parsePositiveInt("2.5", 1)).toBe(1);
  });

  it("returns fallback for non-numeric", () => {
    expect(parsePositiveInt("nan", 1)).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// parsePageSize (list page variant; allowed: [10, 20, 50, 100])
// ---------------------------------------------------------------------------

describe("parsePageSize (tasksListPage)", () => {
  it.each([10, 20, 50, 100])("accepts %i", (n) => {
    expect(parsePageSize(String(n))).toBe(n);
  });

  it("returns default for disallowed value", () => {
    expect(parsePageSize("30")).toBe(DEFAULT_TASK_RUN_PAGE_SIZE);
  });

  it("returns default for null", () => {
    expect(parsePageSize(null)).toBe(DEFAULT_TASK_RUN_PAGE_SIZE);
  });
});

// ---------------------------------------------------------------------------
// parseListState
// ---------------------------------------------------------------------------

describe("parseListState", () => {
  it("returns defaults when params are empty", () => {
    const params = new URLSearchParams();
    expect(parseListState(params)).toEqual({
      taskType: "all",
      status: "all",
      page: 1,
      pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
    });
  });

  it("parses all valid fields", () => {
    const params = new URLSearchParams({
      task_type: "raw_file_organizer",
      status: "completed",
      page: "2",
      page_size: "50",
    });
    expect(parseListState(params)).toEqual({
      taskType: "raw_file_organizer",
      status: "completed",
      page: 2,
      pageSize: 50,
    });
  });

  it("falls back for invalid values", () => {
    const params = new URLSearchParams({
      task_type: "bad",
      status: "done",
      page: "0",
      page_size: "999",
    });
    expect(parseListState(params)).toEqual({
      taskType: "all",
      status: "all",
      page: 1,
      pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
    });
  });
});

// ---------------------------------------------------------------------------
// toSearchParams
// ---------------------------------------------------------------------------

describe("toSearchParams", () => {
  it("always includes page and page_size", () => {
    const result = toSearchParams({
      taskType: "all",
      status: "all",
      page: 1,
      pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
    });
    expect(result.get("page")).toBe("1");
    expect(result.get("page_size")).toBe(String(DEFAULT_TASK_RUN_PAGE_SIZE));
  });

  it("omits task_type when 'all'", () => {
    const result = toSearchParams({
      taskType: "all",
      status: "all",
      page: 1,
      pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
    });
    expect(result.has("task_type")).toBe(false);
  });

  it("omits status when 'all'", () => {
    const result = toSearchParams({
      taskType: "all",
      status: "all",
      page: 1,
      pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
    });
    expect(result.has("status")).toBe(false);
  });

  it("includes task_type when not 'all'", () => {
    const result = toSearchParams({
      taskType: "jav_video_organizer",
      status: "all",
      page: 1,
      pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
    });
    expect(result.get("task_type")).toBe("jav_video_organizer");
  });

  it("includes status when not 'all'", () => {
    const result = toSearchParams({
      taskType: "all",
      status: "failed",
      page: 1,
      pageSize: DEFAULT_TASK_RUN_PAGE_SIZE,
    });
    expect(result.get("status")).toBe("failed");
  });

  it("sets non-default page and page_size", () => {
    const result = toSearchParams({
      taskType: "all",
      status: "all",
      page: 3,
      pageSize: 50,
    });
    expect(result.get("page")).toBe("3");
    expect(result.get("page_size")).toBe("50");
  });
});
