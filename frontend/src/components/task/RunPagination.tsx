interface RunPaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export default function RunPagination({
  page,
  pageSize,
  total,
  onPageChange,
}: RunPaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const hasPrevious = page > 1;
  const hasNext = page < totalPages;

  return (
    <nav
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4 text-sm"
      aria-label="任务列表分页"
    >
      <div className="text-muted-foreground">
        共 {total} 条，第 {page} / {totalPages} 页
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="rounded-md border px-3 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!hasPrevious}
          onClick={() => onPageChange(page - 1)}
        >
          上一页
        </button>
        <button
          type="button"
          className="rounded-md border px-3 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!hasNext}
          onClick={() => onPageChange(page + 1)}
        >
          下一页
        </button>
      </div>
    </nav>
  );
}
