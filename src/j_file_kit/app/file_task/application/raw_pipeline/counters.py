"""Raw 管道阶段计数器。

与 `FileTaskRunStatistics` 中 phase* 字段一一对应，终态与仓储聚合 dict 合并后校验。
"""

from dataclasses import dataclass


@dataclass
class RawPhaseCounters:
    """单次 run 内阶段计数（并入返回统计；不落目录明细表）。

    phase3_seen_files_misc：阶段3.0 迁出 junk 之后，进入分流循环的一层文件数。
    phase3_deleted_junk_misc：阶段3.0 迁入 files_to_delete 计数（dry_run 同口径预览）。
    phase3_deferred_files_misc：阶段3 结束时仍未完成分流者（如非视频未知扩展、I-O 失败）。
    """

    phase1_seen_files: int = 0
    phase1_moved_files: int = 0
    phase1_error_files: int = 0
    phase2_seen_dirs: int = 0
    phase2_moved_to_delete_dirs: int = 0
    phase2_cleaned_deleted_files: int = 0
    phase2_cleaned_deleted_empty_dirs: int = 0
    phase2_removed_dirs: int = 0
    phase2_collapsed_chain_dirs: int = 0
    phase2_skipped_collapse_dirs: int = 0
    phase2_flattened_dirs: int = 0
    phase2_flattened_files: int = 0
    phase2_moved_to_pic_dirs: int = 0
    phase2_moved_to_audio_dirs: int = 0
    phase2_moved_to_compressed_dirs: int = 0
    phase2_moved_to_video_dirs: int = 0
    phase2_moved_to_misc_dirs: int = 0
    phase2_classification_errors: int = 0
    phase3_seen_files_misc: int = 0
    phase3_deleted_junk_misc: int = 0
    phase3_deferred_files_misc: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "phase1_seen_files": self.phase1_seen_files,
            "phase1_moved_files": self.phase1_moved_files,
            "phase1_error_files": self.phase1_error_files,
            "phase2_seen_dirs": self.phase2_seen_dirs,
            "phase2_moved_to_delete_dirs": self.phase2_moved_to_delete_dirs,
            "phase2_cleaned_deleted_files": self.phase2_cleaned_deleted_files,
            "phase2_cleaned_deleted_empty_dirs": self.phase2_cleaned_deleted_empty_dirs,
            "phase2_removed_dirs": self.phase2_removed_dirs,
            "phase2_collapsed_chain_dirs": self.phase2_collapsed_chain_dirs,
            "phase2_skipped_collapse_dirs": self.phase2_skipped_collapse_dirs,
            "phase2_flattened_dirs": self.phase2_flattened_dirs,
            "phase2_flattened_files": self.phase2_flattened_files,
            "phase2_moved_to_pic_dirs": self.phase2_moved_to_pic_dirs,
            "phase2_moved_to_audio_dirs": self.phase2_moved_to_audio_dirs,
            "phase2_moved_to_compressed_dirs": self.phase2_moved_to_compressed_dirs,
            "phase2_moved_to_video_dirs": self.phase2_moved_to_video_dirs,
            "phase2_moved_to_misc_dirs": self.phase2_moved_to_misc_dirs,
            "phase2_classification_errors": self.phase2_classification_errors,
            "phase3_seen_files_misc": self.phase3_seen_files_misc,
            "phase3_deleted_junk_misc": self.phase3_deleted_junk_misc,
            "phase3_deferred_files_misc": self.phase3_deferred_files_misc,
        }
