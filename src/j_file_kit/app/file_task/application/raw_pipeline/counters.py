"""Raw 管道阶段计数器。

与 `FileTaskRunStatistics` 中 phase* 字段一一对应，终态与仓储聚合 dict 合并后校验。
"""

from dataclasses import dataclass


@dataclass
class RawPhaseCounters:
    """单次 run 内阶段计数（并入返回统计；不落目录明细表）。"""

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
    phase2_deferred_classification_dirs: int = 0
    phase3_seen_files_misc: int = 0
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
            "phase2_deferred_classification_dirs": self.phase2_deferred_classification_dirs,
            "phase3_seen_files_misc": self.phase3_seen_files_misc,
            "phase3_deferred_files_misc": self.phase3_deferred_files_misc,
        }
