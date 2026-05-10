import type { FileTaskDecisionType } from "@/api/types";

interface ResultFilterBarProps {
  decisionType: FileTaskDecisionType | "all";
  success: "all" | "true" | "false";
  query: string;
  pageSize: number;
  onDecisionTypeChange: (value: FileTaskDecisionType | "all") => void;
  onSuccessChange: (value: "all" | "true" | "false") => void;
  onQueryChange: (value: string) => void;
  onPageSizeChange: (value: number) => void;
  onReset: () => void;
}

export default function ResultFilterBar({
  decisionType,
  success,
  query,
  pageSize,
  onDecisionTypeChange,
  onSuccessChange,
  onQueryChange,
  onPageSizeChange,
  onReset,
}: ResultFilterBarProps) {
  return (
    <section
      className="flex flex-wrap items-end gap-3 rounded-lg border p-4"
      aria-label="文件结果筛选"
    >
      <label className="grid gap-1 text-sm">
        <span className="font-medium">决策</span>
        <select
          className="rounded-md border bg-background px-3 py-2"
          value={decisionType}
          onChange={(event) =>
            onDecisionTypeChange(
              event.target.value as FileTaskDecisionType | "all",
            )
          }
        >
          <option value="all">全部</option>
          <option value="move">移动</option>
          <option value="delete">删除</option>
          <option value="skip">跳过</option>
        </select>
      </label>

      <label className="grid gap-1 text-sm">
        <span className="font-medium">结果</span>
        <select
          className="rounded-md border bg-background px-3 py-2"
          value={success}
          onChange={(event) =>
            onSuccessChange(event.target.value as "all" | "true" | "false")
          }
        >
          <option value="all">全部</option>
          <option value="true">成功</option>
          <option value="false">失败</option>
        </select>
      </label>

      <label className="grid min-w-[240px] gap-1 text-sm">
        <span className="font-medium">关键字</span>
        <input
          className="rounded-md border bg-background px-3 py-2"
          value={query}
          placeholder="file_stem 或 serial_id"
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </label>

      <label className="grid gap-1 text-sm">
        <span className="font-medium">每页</span>
        <select
          className="rounded-md border bg-background px-3 py-2"
          value={pageSize}
          onChange={(event) => onPageSizeChange(Number(event.target.value))}
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </label>

      <button
        type="button"
        className="rounded-md border px-3 py-2 font-medium text-sm hover:bg-muted"
        onClick={onReset}
      >
        重置
      </button>
    </section>
  );
}
