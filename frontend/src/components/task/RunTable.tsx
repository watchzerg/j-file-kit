import type { FileTaskRunListItem, FileTaskTriggerType } from "@/api/types";
import { formatDateTime, formatMilliseconds } from "@/lib/time";
import DryRunBadge from "./DryRunBadge";
import RunRowActions from "./RunRowActions";
import StatusBadge from "./StatusBadge";
import TaskTypeBadge from "./TaskTypeBadge";

interface RunTableProps {
  runs: FileTaskRunListItem[];
}

const triggerLabels: Record<FileTaskTriggerType, string> = {
  manual: "手动",
  auto: "自动",
};

export default function RunTable({ runs }: RunTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1080px] text-left text-sm">
          <thead className="border-b bg-muted/40 text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">状态</th>
              <th className="px-4 py-3 font-medium">Run</th>
              <th className="px-4 py-3 font-medium">类型</th>
              <th className="px-4 py-3 font-medium">触发</th>
              <th className="px-4 py-3 font-medium">开始时间</th>
              <th className="px-4 py-3 font-medium">结束时间</th>
              <th className="px-4 py-3 font-medium">耗时</th>
              <th className="px-4 py-3 font-medium">统计简报</th>
              <th className="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.run_id} className="border-b last:border-b-0">
                <td className="px-4 py-3">
                  <StatusBadge status={run.status} />
                </td>
                <td className="max-w-[320px] px-4 py-3">
                  <div className="font-medium">{run.run_name}</div>
                  {run.dry_run ? <DryRunBadge className="mt-2" /> : null}
                </td>
                <td className="px-4 py-3">
                  <TaskTypeBadge taskType={run.task_type} />
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {triggerLabels[run.trigger_type]}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatDateTime(run.start_time)}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatDateTime(run.end_time)}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatMilliseconds(run.duration_ms)}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatStatistics(run)}
                </td>
                <td className="px-4 py-3">
                  <RunRowActions run={run} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatStatistics(run: FileTaskRunListItem) {
  const statistics = run.statistics_summary;
  return `总 ${statistics.total_items} / 成功 ${statistics.success_items} / 失败 ${statistics.error_items} / 跳过 ${statistics.skipped_items}`;
}
