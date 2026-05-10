import type { SystemFileTypeDefaultsResponse } from "@/api/types";
import type { ReactNode } from "react";

interface SystemDefaultsPanelProps {
  defaults?: SystemFileTypeDefaultsResponse;
  isLoading: boolean;
}

export function SystemDefaultsPanel({
  defaults,
  isLoading,
}: SystemDefaultsPanelProps) {
  if (isLoading) {
    return (
      <section className="rounded-lg border bg-card p-5 text-muted-foreground text-sm">
        正在加载系统默认字典...
      </section>
    );
  }

  if (!defaults) {
    return (
      <section className="rounded-lg border bg-card p-5 text-muted-foreground text-sm">
        暂无系统默认字典。
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <h2 className="font-semibold text-xl">系统默认字典</h2>
      <p className="mt-1 text-muted-foreground text-sm">
        这些值来自后端整理管线常量，只读展示，任务运行时以服务端为准。
      </p>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <DefaultGroup title="文件扩展名">
          <SummaryList label="视频" values={defaults.extensions.video} />
          <SummaryList label="图片" values={defaults.extensions.image} />
          <SummaryList label="字幕" values={defaults.extensions.subtitle} />
          <SummaryList label="压缩包" values={defaults.extensions.archive} />
          <SummaryList label="音乐" values={defaults.extensions.music} />
          <SummaryList
            label="杂项删除"
            values={defaults.extensions.misc_delete}
          />
        </DefaultGroup>

        <DefaultGroup title="Raw 关键字与阈值">
          <SummaryList label="垃圾关键字" values={defaults.raw.junk_keywords} />
          <SummaryList
            label="电影视频桶"
            values={defaults.raw.video_bucket_movie_keywords}
          />
          <SummaryList
            label="欧美 VR 视频桶"
            values={defaults.raw.video_bucket_us_vr_keywords}
          />
          <SummaryList
            label="欧美视频桶"
            values={defaults.raw.video_bucket_us_keywords}
          />
          <SummaryList
            label="CamelCase 保留词"
            values={defaults.raw.camelcase_no_split_words}
          />
          <div className="text-sm">
            <dt className="font-medium text-muted-foreground">
              清理垃圾文件大小上限
            </dt>
            <dd className="mt-1 text-foreground">
              {formatBytes(defaults.raw.cleanup_junk_max_bytes)}
            </dd>
          </div>
        </DefaultGroup>

        <DefaultGroup title="JAV 命名规则">
          <SummaryList
            label="VR 番号前缀"
            values={defaults.jav.vr_serial_prefixes}
          />
          <SummaryList
            label="文件名去噪子串"
            values={defaults.jav.filename_strip_substrings}
          />
        </DefaultGroup>
      </div>
    </section>
  );
}

function DefaultGroup({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-md border bg-background p-4">
      <h3 className="font-medium">{title}</h3>
      <dl className="mt-4 space-y-4">{children}</dl>
    </section>
  );
}

function SummaryList({ label, values }: { label: string; values: string[] }) {
  const visibleValues = values.slice(0, 8);
  const overflowCount = Math.max(values.length - visibleValues.length, 0);

  return (
    <div className="text-sm">
      <dt className="font-medium text-muted-foreground">
        {label}（共 {values.length} 项）
      </dt>
      <dd className="mt-2 flex flex-wrap gap-2">
        {visibleValues.map((value) => (
          <span
            key={value}
            className="rounded-full border bg-muted px-2 py-1 text-foreground text-xs"
          >
            {value}
          </span>
        ))}
        {overflowCount > 0 ? (
          <span className="rounded-full border px-2 py-1 text-muted-foreground text-xs">
            另 {overflowCount} 项
          </span>
        ) : null}
      </dd>
    </div>
  );
}

function formatBytes(bytes: number) {
  const mib = bytes / 1024 / 1024;
  if (Number.isInteger(mib)) {
    return `${mib} MiB (${bytes} bytes)`;
  }
  return `${bytes} bytes`;
}
