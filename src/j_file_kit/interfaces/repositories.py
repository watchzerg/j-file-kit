"""抽象仓储协议定义

此模块只包含抽象仓储协议，不包含领域专用协议。

设计思路：
- 抽象协议定义通用接口，不依赖特定领域（如 TaskRepository、TaskRepositoryRegistry）
- 领域专用协议位于 interfaces/{domain}/repositories.py（如 interfaces/file/repositories.py）
- 这种组织方式与 services 层的领域组织保持一致，便于理解和维护

遵循依赖倒置原则：interface 层定义抽象，infra 层实现具体细节。
"""

from datetime import datetime
from typing import Any, Protocol

from j_file_kit.models.task import Task, TaskStatus, TaskType, TriggerType

from .file.repositories import FileItemRepository, FileProcessorRepository


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

    def get_task(self, task_id: int) -> Task | None:
        """获取任务记录

        Args:
            task_id: 任务 ID

        Returns:
            任务对象，如果不存在则返回 None
        """
        ...

    def list_tasks(self) -> list[Task]:
        """列出所有任务

        Returns:
            任务列表
        """
        ...

    def get_running_task(self) -> Task | None:
        """获取运行中的任务

        Returns:
            运行中的任务，如果没有则返回 None
        """
        ...

    def get_pending_or_running_tasks(self) -> list[Task]:
        """获取所有待处理或运行中的任务

        Returns:
            待处理或运行中的任务列表
        """
        ...


class TaskRepositoryRegistry(Protocol):
    """任务仓储注册表协议

    管理所有类型的 Repository，提供统一的获取接口。
    作为依赖注入容器，统一管理 Repository 的生命周期。
    """

    def get_task_repository(self) -> TaskRepository:
        """获取任务仓储

        Returns:
            任务仓储实例
        """
        ...

    def get_file_item_repository(self) -> FileItemRepository:
        """获取文件处理结果仓储

        Returns:
            文件处理结果仓储实例
        """
        ...

    def get_file_processor_repository(self) -> FileProcessorRepository:
        """获取文件处理操作仓储

        Returns:
            文件处理操作仓储实例
        """
        ...
