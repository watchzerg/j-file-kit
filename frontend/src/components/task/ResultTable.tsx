import type { FileTaskDecisionType, FileTaskRunResultItem } from "@/api/types";
import { formatDateTime, formatMilliseconds } from "@/lib/time";

interface ResultTableProps {
  results: FileTaskRunResultItem[];
}

const decisionLabels: Record<FileTaskDecisionType, string> = {
  move: "移动",
  delete: "删除",
  skip: "跳过",
};

export default function ResultTable({ results }: ResultTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1280px] text-left text-sm">
          <thead className="border-b bg-muted/40 text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">结果</th>
              <th className="px-4 py-3 font-medium">源路径</th>
              <th className="px-4 py-3 font-medium">Stem</th>
              <th className="px-4 py-3 font-medium">类型</th>
              <th className="px-4 py-3 font-medium">番号</th>
              <th className="px-4 py-3 font-medium">决策</th>
              <th className="px-4 py-3 font-medium">目标路径</th>
              <th className="px-4 py-3 font-medium">耗时</th>
              <th className="px-4 py-3 font-medium">记录时间</th>
              <th className="px-4 py-3 font-medium">错误</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr key={result.id} className="border-b last:border-b-0">
                <td className="px-4 py-3">
                  <span
                    className={[
                      "rounded-full px-2 py-1 font-medium text-xs",
                      result.success
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700",
                    ].join(" ")}
                  >
                    {result.success ? "成功" : "失败"}
                  </span>
                </td>
                <td className="max-w-[360px] px-4 py-3">
                  <PathCell value={result.source_path} />
                </td>
                <td className="max-w-[180px] px-4 py-3 font-medium">
                  <span className="block truncate" title={result.file_stem}>
                    {result.file_stem}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {result.file_type ?? "-"}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {result.serial_id ?? "-"}
                </td>
                <td className="px-4 py-3">
                  {decisionLabels[result.decision_type]}
                </td>
                <td className="max-w-[360px] px-4 py-3">
                  <PathCell value={result.target_path} />
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatMilliseconds(result.duration_ms)}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatDateTime(result.created_at)}
                </td>
                <td className="max-w-[280px] px-4 py-3 text-red-700">
                  {result.error_message ? (
                    <span
                      className="block truncate"
                      title={result.error_message}
                    >
                      {result.error_message}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PathCell({ value }: { value: string | null }) {
  if (!value) {
    return <span className="text-muted-foreground">-</span>;
  }

  return (
    <span className="block truncate font-mono text-xs" title={value}>
      {value}
    </span>
  );
}
