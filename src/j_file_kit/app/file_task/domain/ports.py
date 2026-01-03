"""文件任务仓储接口

定义文件任务相关的仓储协议接口，遵循依赖倒置原则。
"""

from pathlib import Path
from typing import Any, Protocol

from j_file_kit.app.file_task.domain.decisions import FileItemData
from j_file_kit.app.file_task.domain.models import Operation, OperationType
from j_file_kit.app.task.domain.ports import TaskRepository


class FileItemRepository(Protocol):
    """文件处理结果仓储协议

    定义文件处理结果持久化操作的接口。
    专门用于文件处理结果，不处理目录操作（目录操作已在 operations 表中记录）。
    提供保存结果、获取统计信息等功能。
    """

    def save_result(self, result: FileItemData) -> int:
        """保存单个文件处理结果

        Args:
            result: 文件处理结果数据

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


class FileProcessorRepository(Protocol):
    """文件处理操作仓储协议

    定义文件操作日志持久化操作的接口。
    只处理文件操作（MOVE、DELETE、RENAME），不处理目录操作。
    提供创建操作记录、查询操作历史等功能。
    """

    def create_operation(
        self,
        operation: OperationType,
        source_path: Path,
        target_path: Path | None = None,
        file_item_id: int | None = None,
        file_type: str | None = None,
        serial_id: str | None = None,
    ) -> str:
        """创建操作记录

        只接受文件操作类型（MOVE、DELETE、RENAME），拒绝目录操作类型。

        Args:
            operation: 操作类型（必须是文件操作，不能是 CREATE_DIR 或 DELETE_DIR）
            source_path: 源路径
            target_path: 目标路径（可选）
            file_item_id: 文件项 ID（可选）
            file_type: 文件类型（冗余字段，避免 JOIN）
            serial_id: 番号（冗余字段，避免 JOIN）

        Returns:
            生成的操作 ID（UUID 字符串）

        Raises:
            ValueError: 如果操作类型是目录操作（CREATE_DIR 或 DELETE_DIR）
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
        - by_item_type: 按文件类型统计操作数量

        使用冗余字段 file_type 直接统计，无需 JOIN file_items 表。

        Returns:
            操作统计字典
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
