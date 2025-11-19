"""文件处理仓储实现

封装文件处理相关的 Repository。
实现 FileProcessorRepository Protocol。
"""

from __future__ import annotations

from j_file_kit.interfaces.repositories import (
    ItemResultRepository,
    OperationRepository,
)

from .connection import SQLiteConnectionManager
from .item_result_repository import ItemResultRepositoryImpl
from .operation_repository import OperationRepositoryImpl


class FileProcessorRepositoryImpl:
    """文件处理仓储实现

    封装文件处理相关的 Repository，包含 ItemResultRepository 和 OperationRepository。
    实现 FileProcessorRepository Protocol。
    """

    def __init__(
        self, connection_manager: SQLiteConnectionManager, task_id: int
    ) -> None:
        """初始化文件处理仓储

        Args:
            connection_manager: SQLite 连接管理器
            task_id: 任务 ID
        """
        self._item_result_repository = ItemResultRepositoryImpl(
            connection_manager, task_id
        )
        self._operation_repository = OperationRepositoryImpl(
            connection_manager, task_id
        )

    @property
    def item_result_repository(self) -> ItemResultRepository:
        """Item 结果仓储实例"""
        return self._item_result_repository

    @property
    def operation_repository(self) -> OperationRepository:
        """操作记录仓储实例"""
        return self._operation_repository
