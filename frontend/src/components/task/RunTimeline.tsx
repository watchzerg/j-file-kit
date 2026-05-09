import type { FileTaskRunDetailResponse } from "@/api/types";
import { formatDateTime, formatDuration } from "@/lib/time";
import { useEffect, useState } from "react";

interface RunTimelineProps {
  run: FileTaskRunDetailResponse;
}

function isActiveStatus(status: FileTaskRunDetailResponse["status"]) {
  return status === "pending" || status === "running";
}

export default function RunTimeline({ run }: RunTimelineProps) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!isActiveStatus(run.status)) {
      return;
    }
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [run.status]);

  const items = [
    { label: "开始时间", value: formatDateTime(run.start_time) },
    { label: "结束时间", value: formatDateTime(run.end_time) },
    { label: "已耗时", value: formatDuration(run.start_time, run.end_time) },
  ];

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-semibold text-lg">执行时间线</h2>
        <span className="sr-only">更新时间 {now}</span>
      </div>
      <dl className="grid gap-4 md:grid-cols-3">
        {items.map((item) => (
          <div key={item.label} className="rounded-md border bg-background p-4">
            <dt className="font-medium text-muted-foreground text-sm">
              {item.label}
            </dt>
            <dd className="mt-2 font-semibold">{item.value}</dd>
          </div>
        ))}
      </dl>
      {run.error_message ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
          <p className="font-medium">错误信息</p>
          <p className="mt-1 break-all">{run.error_message}</p>
        </div>
      ) : null}
    </section>
  );
}
