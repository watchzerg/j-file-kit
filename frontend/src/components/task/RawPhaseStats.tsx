import type { FileTaskRunStatistics } from "@/api/types";

type StatisticKey = keyof FileTaskRunStatistics;

interface PhaseGroup {
  title: string;
  description: string;
  items: Array<{ key: StatisticKey; label: string }>;
}

function readStat(
  statistics: FileTaskRunStatistics,
  key: StatisticKey,
): number {
  return statistics[key] ?? 0;
}

const phaseGroups: PhaseGroup[] = [
  {
    title: "阶段 1：收散落文件",
    description: "处理 inbox 第一层散落文件并归入 files_misc。",
    items: [
      { key: "phase1_seen_files", label: "见到文件" },
      { key: "phase1_moved_files", label: "归入 files_misc" },
      { key: "phase1_error_files", label: "处理失败" },
    ],
  },
  {
    title: "阶段 2：子目录处理",
    description: "目录迁出、清洗、单链折叠与分类迁移。",
    items: [
      { key: "phase2_seen_dirs", label: "见到目录" },
      { key: "phase2_moved_to_delete_dirs", label: "整目录待删除" },
      { key: "phase2_cleaned_deleted_files", label: "清洗删除文件" },
      {
        key: "phase2_cleaned_deleted_empty_dirs",
        label: "清洗删除空目录",
      },
      { key: "phase2_removed_dirs", label: "移除空目录" },
      { key: "phase2_collapsed_chain_dirs", label: "单链折叠" },
      { key: "phase2_skipped_collapse_dirs", label: "跳过折叠" },
      { key: "phase2_flattened_dirs", label: "拆解目录" },
      { key: "phase2_flattened_files", label: "拆解文件" },
      { key: "phase2_moved_to_pic_dirs", label: "迁入图片目录" },
      { key: "phase2_moved_to_audio_dirs", label: "迁入音频目录" },
      { key: "phase2_moved_to_compressed_dirs", label: "迁入压缩目录" },
      { key: "phase2_moved_to_video_dirs", label: "迁入视频目录" },
      { key: "phase2_moved_to_misc_dirs", label: "迁入杂项目录" },
      { key: "phase2_classification_errors", label: "分类失败" },
    ],
  },
  {
    title: "阶段 3：files_misc 分流",
    description:
      "对 files_misc 第一层文件继续删除 junk 或分类迁移，并展示细分去向。",
    items: [
      { key: "phase3_seen_files_misc", label: "进入分流文件" },
      { key: "phase3_deleted_junk_misc", label: "junk 待删除" },
      { key: "phase3_routed_archive_files", label: "迁入压缩目录" },
      { key: "phase3_routed_image_files", label: "迁入图片目录" },
      { key: "phase3_routed_audio_files", label: "迁入音频目录" },
      { key: "phase3_routed_video_files", label: "迁入视频目录（总）" },
      { key: "phase3_routed_video_movie_files", label: "视频桶 movie" },
      { key: "phase3_routed_video_us_vr_files", label: "视频桶 us_vr" },
      { key: "phase3_routed_video_us_files", label: "视频桶 us" },
      { key: "phase3_routed_video_jav_vr_files", label: "视频桶 jav_vr" },
      { key: "phase3_routed_video_jav_files", label: "视频桶 jav" },
      { key: "phase3_routed_video_misc_files", label: "视频桶 misc" },
      { key: "phase3_deferred_files_misc", label: "暂留 files_misc" },
      {
        key: "phase3_deferred_unknown_extension_files",
        label: "暂留（未知扩展）",
      },
      { key: "phase3_deferred_error_files", label: "暂留（迁移失败）" },
    ],
  },
];

interface RawPhaseStatsProps {
  statistics: FileTaskRunStatistics;
}

export default function RawPhaseStats({ statistics }: RawPhaseStatsProps) {
  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <div>
        <h2 className="font-semibold text-lg">Raw 阶段统计</h2>
        <p className="mt-1 text-muted-foreground text-sm">
          仅 Raw 文件整理任务显示，按三阶段汇总关键处理计数。
        </p>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {phaseGroups.map((group) => (
          <article key={group.title} className="rounded-lg border p-4">
            <h3 className="font-semibold">{group.title}</h3>
            <p className="mt-1 text-muted-foreground text-sm">
              {group.description}
            </p>
            <dl className="mt-4 space-y-3">
              {group.items.map((item) => (
                <div
                  key={item.key}
                  className="flex items-center justify-between gap-3"
                >
                  <dt className="text-muted-foreground text-sm">
                    {item.label}
                  </dt>
                  <dd className="font-semibold">
                    {readStat(statistics, item.key)}
                  </dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}
