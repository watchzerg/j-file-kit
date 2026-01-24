"""文件任务仓储接口

定义文件任务相关的仓储协议接口，遵循依赖倒置原则。

Repository 方法接收 task_id 参数而非构造时绑定，支持单例复用，简化依赖注入。
"""

from pathlib import Path
from typing import Any, Protocol

from j_file_kit.app.file_task.domain.decisions import FileItemData
from j_file_kit.app.file_task.domain.models import OperationType


class FileItemRepository(Protocol):
    """文件处理结果仓储协议

    定义文件处理结果持久化操作的接口。
    专门用于文件处理结果，不处理目录操作（目录操作已在 operations 表中记录）。
    提供保存结果、获取统计信息等功能。

    设计说明：方法接收 task_id 参数，支持 Repository 作为单例复用。
    """

    def save_result(self, task_id: int, result: FileItemData) -> int:
        """保存单个文件处理结果

        Args:
            task_id: 任务 ID
            result: 文件处理结果数据

        Returns:
            生成的结果 ID
        """
        ...

    def get_statistics(self, task_id: int) -> dict[str, Any]:
        """获取任务统计信息

        Args:
            task_id: 任务 ID

        Returns:
            统计信息字典，包含 total_items, success_items, error_items,
            skipped_items, warning_items, total_duration_ms
        """
        ...


class FileProcessorRepository(Protocol):
    """文件处理操作仓储协议

    定义文件操作日志持久化操作的接口。
    只处理文件操作（MOVE、DELETE、RENAME），不处理目录操作。
    提供创建操作记录、查询操作历史等功能。

    设计说明：方法接收 task_id 参数，支持 Repository 作为单例复用。
    """

    def create_operation(
        self,
        task_id: int,
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
            task_id: 任务 ID
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
