"""Repository 协议定义

定义所有 Repository 的 Protocol 接口。
遵循依赖倒置原则：interface 层定义抽象，infra 层实现具体细节。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from ..models import (
    FileItemResult,
    Operation,
    OperationType,
    Task,
    TaskStatus,
    TaskType,
    TriggerType,
)


class FileItemRepository(Protocol):
    """文件处理结果仓储协议

    定义文件处理结果持久化操作的接口。
    专门用于文件处理结果，不处理目录操作（目录操作已在 operations 表中记录）。
    提供保存结果、获取统计信息等功能。
    """

    def save_result(self, result: FileItemResult) -> int:
        """保存单个文件处理结果

        Args:
            result: 文件处理结果

        Returns:
            生成的结果 ID
        """
        ...

    def get_statistics(self) -> dict[str, Any]:
        """获取任务统计信息

        Returns:
            统计信息字典，包含 total_items, success_items, error_items,
            skipped_items, warning_items, total_duration_ms
        """
        ...

    def get_detailed_statistics(self) -> dict[str, Any]:
        """获取任务的详细统计信息

        包含两个部分：
        - by_item_type: 按文件类型统计（video/image/archive/misc）
        - performance_metrics: 性能指标

        Returns:
            详细统计字典
        """
        ...


class OperationRepository(Protocol):
    """操作记录仓储协议

    定义文件操作日志持久化操作的接口。
    提供创建操作记录、查询操作历史等功能。
    """

    def create_operation(
        self,
        operation: OperationType,
        source_path: Path,
        target_path: Path | None = None,
        data: dict[str, Any] | None = None,
        item_result_id: int | None = None,
    ) -> str:
        """创建操作记录

        Args:
            operation: 操作类型
            source_path: 源路径
            target_path: 目标路径（可选）
            data: 附加数据（可选）
            item_result_id: Item 结果 ID（可选）

        Returns:
            生成的操作 ID（UUID 字符串）
        """
        ...

    def get_operations(self) -> list[Operation]:
        """获取任务的操作记录

        Returns:
            操作记录列表
        """
        ...

    def get_operation_statistics(self) -> dict[str, Any]:
        """获取任务的操作统计信息

        统计操作数量，包含两个维度：
        - by_operation_type: 按操作类型统计
        - by_item_type: 按 item 类型统计操作数量

        Returns:
            操作统计字典
        """
        ...


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


class FileProcessorRepository(Protocol):
    """文件处理仓储协议

    封装文件处理相关的 Repository。
    包含 FileItemRepository 和 OperationRepository。
    """

    @property
    def file_item_repository(self) -> FileItemRepository:
        """文件处理结果仓储实例"""
        ...

    @property
    def operation_repository(self) -> OperationRepository:
        """操作记录仓储实例"""
        ...


class CrawlerProcessorRepository(Protocol):
    """爬虫处理仓储协议

    预留接口，用于未来爬虫处理相关的 Repository。
    当前为空协议，等待后续实现。
    """

    ...


class TaskRepositoryRegistry(Protocol):
    """任务仓储注册表协议

    管理所有类型的 Repository，提供统一的获取接口。
    作为依赖注入容器，统一管理 Repository 的生命周期。
    """

    def get_file_processor_repository(self) -> FileProcessorRepository:
        """获取文件处理仓储

        Returns:
            文件处理仓储实例
        """
        ...

    def get_task_repository(self) -> TaskRepository:
        """获取任务仓储

        Returns:
            任务仓储实例
        """
        ...

    def get_crawler_processor_repository(self) -> CrawlerProcessorRepository:
        """获取爬虫处理仓储

        Returns:
            爬虫处理仓储实例（预留）
        """
        ...
