import { useRecentTaskRuns } from "@/api/tasks";
import { getErrorMessage } from "@/lib/errors";
import { formatDateTime, formatDuration } from "@/lib/time";
import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function RecentRunsList() {
  const recentRunsQuery = useRecentTaskRuns();

  return (
    <section className="space-y-4" aria-labelledby="recent-runs-heading">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="recent-runs-heading" className="font-semibold text-xl">
            最近任务
          </h2>
          <p className="mt-1 text-muted-foreground text-sm">
            显示最近 10 个 run；统计简报会在列表接口扩展后补齐。
          </p>
        </div>
        <Link
          to="/tasks"
          className="font-medium text-foreground text-sm hover:underline"
        >
          查看全部
        </Link>
      </div>

      {recentRunsQuery.isLoading ? (
        <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
          正在加载最近任务...
        </div>
      ) : null}

      {recentRunsQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 text-sm">
          {getErrorMessage(recentRunsQuery.error)}
        </div>
      ) : null}

      {recentRunsQuery.data?.length === 0 ? (
        <div className="rounded-lg border border-dashed p-6 text-muted-foreground">
          暂无任务记录。
        </div>
      ) : null}

      {recentRunsQuery.data && recentRunsQuery.data.length > 0 ? (
        <div className="overflow-hidden rounded-lg border">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b bg-muted/40 text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">状态</th>
                  <th className="px-4 py-3 font-medium">Run</th>
                  <th className="px-4 py-3 font-medium">开始时间</th>
                  <th className="px-4 py-3 font-medium">结束时间</th>
                  <th className="px-4 py-3 font-medium">耗时</th>
                  <th className="px-4 py-3 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {recentRunsQuery.data.map((run) => (
                  <tr key={run.run_id} className="border-b last:border-b-0">
                    <td className="px-4 py-3">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-4 py-3 font-medium">{run.run_name}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDateTime(run.start_time)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDateTime(run.end_time)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDuration(run.start_time, run.end_time)}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/tasks/${run.run_id}`}
                        className="font-medium text-foreground hover:underline"
                      >
                        查看详情
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}
