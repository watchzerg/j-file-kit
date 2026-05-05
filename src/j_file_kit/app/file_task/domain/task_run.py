"""文件任务执行实例（Run）相关模型与枚举

包含状态/触发类型、聚合报告与统计快照、持久化行模型。
由 `FileTaskRunRepository`、`FilePipeline` / `RawFilePipeline`、`FileTaskRunManager` 使用。
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FileTaskRunStatus(StrEnum):
    """文件任务执行状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileTaskTriggerType(StrEnum):
    """文件任务触发类型枚举"""

    MANUAL = "manual"
    AUTO = "auto"


class FileTaskRunReport(BaseModel):
    """文件任务执行汇总报告

    记录任务执行的完整统计结果，包含成功率、错误率、耗时等派生属性。
    通常在任务完成后由 Pipeline 构建，用于日志和展示。
    """

    run_name: str = Field(..., description="执行实例名称")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    total_items: int = Field(0, description="总item数")
    success_items: int = Field(0, description="成功item数")
    error_items: int = Field(0, description="失败item数")
    skipped_items: int = Field(0, description="跳过item数")
    warning_items: int = Field(0, description="警告item数")
    total_duration_ms: float = Field(0.0, description="总耗时（毫秒）")

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_items == 0:
            return 0.0
        return self.success_items / self.total_items

    @property
    def error_rate(self) -> float:
        """错误率"""
        if self.total_items == 0:
            return 0.0
        return self.error_items / self.total_items

    @property
    def duration_seconds(self) -> float:
        """耗时（秒）"""
        return self.total_duration_ms / 1000.0

    def update_from_stats(self, stats: dict[str, Any]) -> None:
        """从统计信息字典更新报告字段

        Args:
            stats: 统计信息字典，包含 total_items, success_items, error_items,
                   skipped_items, warning_items, total_duration_ms
        """
        self.total_items = stats.get("total_items", 0)
        self.success_items = stats.get("success_items", 0)
        self.error_items = stats.get("error_items", 0)
        self.skipped_items = stats.get("skipped_items", 0)
        self.warning_items = stats.get("warning_items", 0)
        self.total_duration_ms = stats.get("total_duration_ms", 0.0)


class FileTaskRunStatistics(BaseModel):
    """单次任务 run 结束时的统计快照（返回给 `FileTaskRunManager` 写回 `file_task_runs`）。

    在 JAV 整理链路中：`finish_task_with_repository_statistics` 调用 `FileResultRepository.get_statistics(run_id)`，
    将聚合字典 `model_validate` 为本模型。语义上以仓储聚合为准，而非仅依赖管道内存计数。

    Raw 整理链路：`RawFilePipeline` 在上述聚合之上合并「阶段化」计数（仍不写目录明细表），
    键名见 `phase*` 字段。
    """

    total_items: int = Field(0, description="总item数")
    success_items: int = Field(0, description="成功item数")
    error_items: int = Field(0, description="失败item数")
    skipped_items: int = Field(0, description="跳过item数")
    warning_items: int = Field(0, description="警告item数")
    total_duration_ms: float = Field(0.0, description="总耗时（毫秒）")

    phase1_seen_files: int = Field(
        0,
        description="Raw：阶段1 见到的 inbox 第一层文件数",
    )
    phase1_moved_files: int = Field(
        0,
        description="Raw：阶段1 成功归入 files_misc 的文件数（含 dry_run 预览成功）",
    )
    phase1_error_files: int = Field(
        0,
        description="Raw：阶段1 处理失败的文件数",
    )
    phase2_seen_dirs: int = Field(
        0,
        description="Raw：阶段2 见到的 inbox 第一层目录数",
    )
    phase2_moved_to_delete_dirs: int = Field(
        0,
        description="Raw：阶段2.1 整目录迁入 folders_to_delete 的数量（含 dry_run 预览计数）",
    )
    phase2_cleaned_deleted_files: int = Field(
        0,
        description="Raw：阶段2.2 清洗阶段删除的文件数（含 dry_run 预览计数）",
    )
    phase2_cleaned_deleted_empty_dirs: int = Field(
        0,
        description="Raw：阶段2.2 清洗阶段删除的空目录数（不含整目录迁出；含 dry_run 预览计数）",
    )
    phase2_removed_dirs: int = Field(
        0,
        description="Raw：阶段2.2 清洗后 inbox 第一层目录被 rmdir 移除的数量（因内容删空）",
    )
    phase2_collapsed_chain_dirs: int = Field(
        0,
        description="Raw：阶段2.3 单链目录折叠成功次数（含 dry_run 预览计数）",
    )
    phase2_skipped_collapse_dirs: int = Field(
        0,
        description="Raw：阶段2.3 因长度预算等跳过折叠的目录数（不中断 run）",
    )
    phase2_flattened_dirs: int = Field(
        0,
        description="Raw：阶段2.4 符合小目录规则并拆解迁入 files_misc 的目录数（含 dry_run 预览）",
    )
    phase2_flattened_files: int = Field(
        0,
        description="Raw：阶段2.4 拆解目录时迁入 files_misc 的文件数（含 dry_run 预览）",
    )
    phase2_moved_to_pic_dirs: int = Field(
        0,
        description="Raw：阶段2.4 整目录迁入 folders_pic 的数量（含 dry_run 预览）",
    )
    phase2_moved_to_audio_dirs: int = Field(
        0,
        description="Raw：阶段2.4 整目录迁入 folders_audio 的数量（含 dry_run 预览）",
    )
    phase2_moved_to_compressed_dirs: int = Field(
        0,
        description="Raw：阶段2.4 整目录迁入 folders_compressed 的数量（含 dry_run 预览）",
    )
    phase2_moved_to_video_dirs: int = Field(
        0,
        description="Raw：阶段2.4 整目录迁入 folders_video 的数量（含 dry_run 预览）",
    )
    phase2_moved_to_misc_dirs: int = Field(
        0,
        description="Raw：阶段2.4 整目录迁入 folders_misc 的数量（含 dry_run 预览）",
    )
    phase2_classification_errors: int = Field(
        0,
        description="Raw：阶段2.4 分类或迁移失败次数（不中断 run）",
    )
    phase3_seen_files_misc: int = Field(
        0,
        description="Raw：阶段3 开始时 files_misc 下第一层文件数",
    )
    phase3_deferred_files_misc: int = Field(
        0,
        description="Raw：阶段3 占位暂未分流处理的文件数",
    )


class FileTaskRun(BaseModel):
    """文件任务执行实例持久化记录

    对应数据库 file_task_runs 表中的一行，由 FileTaskRunRepository 读写。
    """

    run_id: int = Field(..., description="执行实例ID")
    run_name: str = Field(..., description="执行实例名称")
    task_type: str = Field(..., description="任务类型")
    trigger_type: FileTaskTriggerType = Field(..., description="触发类型")
    status: FileTaskRunStatus = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")
