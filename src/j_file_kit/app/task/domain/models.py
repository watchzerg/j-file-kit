"""任务领域模型和协议

定义任务管理领域的核心模型和协议：
- 枚举：TaskStatus, TriggerType
- 异常：TaskError, TaskNotFoundError, TaskAlreadyRunningError, TaskCancelledError
- 模型：TaskRecord, TaskReport
- 协议：TaskRunner

所有具体任务实现必须符合 TaskRunner 协议。
"""

import threading
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(str, Enum):
    """触发类型枚举"""

    MANUAL = "manual"
    AUTO = "auto"


# ============================================================
# 领域异常
# ============================================================


class TaskError(Exception):
    """任务相关异常基类"""

    pass


class TaskNotFoundError(TaskError):
    """任务不存在异常"""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"任务不存在: {task_id}")


class TaskAlreadyRunningError(TaskError):
    """任务已在运行异常"""

    def __init__(self, running_task_id: int) -> None:
        self.running_task_id = running_task_id
        super().__init__(f"已有任务正在运行: {running_task_id}")


class TaskCancelledError(TaskError):
    """任务已取消异常"""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"任务已取消: {task_id}")


# ============================================================
# 领域模型
# ============================================================


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


class TaskStatistics(BaseModel):
    """任务统计信息"""

    total_items: int = Field(0, description="总item数")
    success_items: int = Field(0, description="成功item数")
    error_items: int = Field(0, description="失败item数")
    skipped_items: int = Field(0, description="跳过item数")
    warning_items: int = Field(0, description="警告item数")
    total_duration_ms: float = Field(0.0, description="总耗时（毫秒）")


class TaskRecord(BaseModel):
    """任务记录

    表示任务的持久化记录，对应数据库中的一行。
    """

    task_id: int = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    task_type: str = Field(..., description="任务类型")
    trigger_type: TriggerType = Field(..., description="触发类型")
    status: TaskStatus = Field(..., description="任务状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")


class TaskRunner(Protocol):
    """任务执行器协议

    TaskRunner 是业务用例层，定义"做什么"。

    职责：
    - 定义业务用例
    - 通过 `run()` 方法执行任务

    设计说明：
    - TaskRunner 在构造时获得所需的 repositories
    - run() 只接收运行时参数（task_id、dry_run、cancellation_event）
    - 这样设计消除了对具体 Repository 类型的依赖，保持 Protocol 通用性

    所有具体任务实现必须符合此协议（通过继承或实现相同接口）。
    """

    @property
    def task_type(self) -> str:
        """任务类型"""
        ...

    def run(
        self,
        task_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> TaskStatistics:
        """运行任务

        TaskRunner 通过 `run()` 方法执行任务，内部调用 Pipeline。

        Args:
            task_id: 任务 ID
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancellation_event: 取消事件，用于检查任务是否被取消

        Returns:
            任务统计信息

        Raises:
            Exception: 任务执行过程中的任何异常
        """
        ...
