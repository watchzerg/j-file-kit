interface LogPaginationProps {
  offset: number;
  limit: number;
  total: number;
  onOffsetChange: (offset: number) => void;
}

export default function LogPagination({
  offset,
  limit,
  total,
  onOffsetChange,
}: LogPaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const hasPrevious = offset > 0;
  const hasNext = offset + limit < total;

  return (
    <nav
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4 text-sm"
      aria-label="日志分页"
    >
      <div className="text-muted-foreground">
        共 {total} 行，第 {currentPage} / {totalPages} 页
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="rounded-md border px-3 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!hasPrevious}
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
        >
          上一页
        </button>
        <button
          type="button"
          className="rounded-md border px-3 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!hasNext}
          onClick={() => onOffsetChange(offset + limit)}
        >
          下一页
        </button>
      </div>
    </nav>
  );
}
