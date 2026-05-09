import type { FileTaskRunStatistics } from "@/api/types";
import { formatMilliseconds } from "@/lib/time";

interface StatsSummaryGridProps {
  statistics: FileTaskRunStatistics;
}

export default function StatsSummaryGrid({
  statistics,
}: StatsSummaryGridProps) {
  const items = [
    { label: "总数", value: statistics.total_items },
    { label: "成功", value: statistics.success_items },
    { label: "失败", value: statistics.error_items },
    { label: "跳过", value: statistics.skipped_items },
    { label: "警告", value: statistics.warning_items },
    {
      label: "处理耗时",
      value: formatMilliseconds(statistics.total_duration_ms),
    },
  ];

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <h2 className="font-semibold text-lg">统计概览</h2>
      <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <div key={item.label} className="rounded-md border bg-background p-4">
            <dt className="font-medium text-muted-foreground text-sm">
              {item.label}
            </dt>
            <dd className="mt-2 font-semibold text-2xl">{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
