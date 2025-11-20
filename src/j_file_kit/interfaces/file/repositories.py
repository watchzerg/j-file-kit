"""file 领域专用仓储协议

此模块定义 file 领域的专用仓储协议，与抽象仓储协议区分。

设计思路：
- 抽象仓储协议位于 interfaces/repositories.py，定义通用接口（如 TaskRepository）
- 领域专用仓储协议位于 interfaces/{domain}/repositories.py，定义特定领域的接口
- 这种组织方式与 services 层保持一致，便于理解和维护

适用场景：
- FileItemRepository: 用于文件处理结果的持久化
- FileProcessorRepository: 用于文件操作记录的持久化
"""

from pathlib import Path
from typing import Any, Protocol

from ...models import (
    FileItemResult,
    Operation,
    OperationType,
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
