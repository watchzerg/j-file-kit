import type { SystemInfoResponse } from "@/api/types";

interface SystemInfoPanelProps {
  info?: SystemInfoResponse;
  isLoading: boolean;
  variant?: "full" | "compact";
}

export function SystemInfoPanel({
  info,
  isLoading,
  variant = "full",
}: SystemInfoPanelProps) {
  if (isLoading) {
    return (
      <section className="rounded-lg border bg-card p-5 text-muted-foreground text-sm">
        正在加载系统信息...
      </section>
    );
  }

  const items = [
    { label: "版本", value: info?.app_version ?? "-" },
    { label: "环境", value: info?.env ?? "-" },
    { label: "数据目录", value: info?.base_dir ?? "-" },
    { label: "媒体根目录", value: info?.media_root ?? "-" },
    { label: "JAV 根目录", value: info?.jav_media_root ?? "-" },
    { label: "Raw 根目录", value: info?.raw_media_root ?? "-" },
    {
      label: "媒体挂载",
      value: info?.media_mounted === true ? "已挂载" : "未检测到挂载",
    },
  ];

  if (variant === "compact") {
    return (
      <section className="rounded-lg border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-lg">系统信息</h2>
            <p className="mt-1 text-muted-foreground text-sm">
              当前服务版本、媒体挂载和默认工作区边界。
            </p>
          </div>
          <span className="rounded-full border px-3 py-1 text-muted-foreground text-xs">
            {info?.media_mounted === true ? "媒体已挂载" : "媒体未挂载"}
          </span>
        </div>
        <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
          {items.map((item) => (
            <InfoItem key={item.label} label={item.label} value={item.value} />
          ))}
        </dl>
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <h2 className="font-semibold text-xl">路径与挂载</h2>
      <p className="mt-1 text-muted-foreground text-sm">
        只读系统路径与挂载状态，作为任务配置校验与 Dashboard
        页脚的统一数据来源。
      </p>
      <dl className="mt-5 grid gap-4 text-sm md:grid-cols-2">
        {items.map((item) => (
          <InfoItem key={item.label} label={item.label} value={item.value} />
        ))}
      </dl>
    </section>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-all text-foreground">{value}</dd>
    </div>
  );
}
