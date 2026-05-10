import type { FileTaskRunLogLine } from "@/api/types";

interface LogViewerProps {
  lines: FileTaskRunLogLine[];
}

const levelClasses: Record<string, string> = {
  DEBUG: "bg-slate-100 text-slate-700",
  INFO: "bg-blue-100 text-blue-700",
  WARNING: "bg-yellow-100 text-yellow-800",
  ERROR: "bg-red-100 text-red-700",
  CRITICAL: "bg-red-100 text-red-800",
};

export default function LogViewer({ lines }: LogViewerProps) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead className="border-b bg-muted/40 text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">行号</th>
              <th className="px-4 py-3 font-medium">时间</th>
              <th className="px-4 py-3 font-medium">等级</th>
              <th className="px-4 py-3 font-medium">消息</th>
              <th className="px-4 py-3 font-medium">字段</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.line_no} className="border-b last:border-b-0">
                <td className="px-4 py-3 font-mono text-muted-foreground text-xs">
                  {line.line_no}
                </td>
                <td className="px-4 py-3 font-mono text-muted-foreground text-xs">
                  {line.ts ?? "-"}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={[
                      "rounded-full px-2 py-1 font-medium text-xs",
                      levelClasses[line.level ?? ""] ??
                        "bg-muted text-muted-foreground",
                    ].join(" ")}
                  >
                    {line.level ?? "UNKNOWN"}
                  </span>
                </td>
                <td className="max-w-[360px] px-4 py-3">
                  <span className="block truncate" title={line.msg}>
                    {line.msg}
                  </span>
                </td>
                <td className="max-w-[360px] px-4 py-3">
                  <details>
                    <summary className="cursor-pointer text-muted-foreground text-xs">
                      查看字段
                    </summary>
                    <pre className="mt-2 max-h-40 overflow-auto rounded-md bg-muted p-3 text-xs">
                      {JSON.stringify(line.fields, null, 2)}
                    </pre>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
