"""任务仓储接口

定义任务相关的仓储协议接口，遵循依赖倒置原则。
"""

from datetime import datetime
from typing import Any, Protocol

from j_file_kit.app.task.domain.models import (
    TaskRecord,
    TaskStatus,
    TaskType,
    TriggerType,
)


class TaskRepository(Protocol):
    """任务仓储协议

    定义任务数据持久化操作的接口。
    提供任务的创建、更新、查询等功能。
    """

    def create_task(
        self,
        task_name: str,
        task_type: TaskType,
        trigger_type: TriggerType,
        status: TaskStatus,
        start_time: datetime,
    ) -> int:
        """创建任务记录

        Args:
            task_name: 任务名称
            task_type: 任务类型
            trigger_type: 触发类型
            status: 任务状态
            start_time: 开始时间

        Returns:
            生成的任务 ID
        """
        ...

    def update_task(
        self,
        task_id: int,
        status: TaskStatus | None = None,
        end_time: datetime | None = None,
        error_message: str | None = None,
        statistics: dict[str, Any] | None = None,
    ) -> None:
        """更新任务记录

        Args:
            task_id: 任务 ID
            status: 任务状态（可选）
            end_time: 结束时间（可选）
            error_message: 错误消息（可选）
            statistics: 统计信息字典（可选）
        """
        ...

    def get_task(self, task_id: int) -> TaskRecord | None:
        """获取任务记录

        Args:
            task_id: 任务 ID

        Returns:
            任务对象，如果不存在则返回 None
        """
        ...

    def list_tasks(self) -> list[TaskRecord]:
        """列出所有任务

        Returns:
            任务列表
        """
        ...

    def get_running_task(self) -> TaskRecord | None:
        """获取运行中的任务

        Returns:
            运行中的任务，如果没有则返回 None
        """
        ...

    def get_pending_or_running_tasks(self) -> list[TaskRecord]:
        """获取所有待处理或运行中的任务

        Returns:
            待处理或运行中的任务列表
        """
        ...
