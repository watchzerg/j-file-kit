"""任务相关模型

定义任务执行相关的模型，包括任务实例和任务报告。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import TaskStatus, TaskType, TriggerType


class TaskReport(BaseModel):
    """任务汇总报告

    通用的任务执行报告，适用于所有类型的任务（文件处理、爬虫等）。
    """

    task_name: str = Field(..., description="任务名称")
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
        """从统计信息更新报告

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


class Task(BaseModel):
    """任务模型

    表示一个执行中的任务实例。
    """

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    task_type: TaskType = Field(..., description="任务类型")
    trigger_type: TriggerType = Field(..., description="触发类型")
    status: TaskStatus = Field(..., description="任务状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")
