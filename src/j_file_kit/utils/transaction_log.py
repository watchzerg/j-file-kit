"""事务日志模块

记录所有文件操作到 SQLite 数据库。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.db import DatabaseManager


class OperationType:
    """操作类型常量"""

    RENAME = "rename"
    MOVE = "move"
    DELETE = "delete"
    CREATE_DIR = "create_dir"
    DELETE_DIR = "delete_dir"


class TransactionLog:
    """事务日志管理器

    记录文件操作到 SQLite 数据库。
    """

    def __init__(self, db_manager: DatabaseManager, task_id: str) -> None:
        """初始化事务日志

        Args:
            db_manager: 数据库管理器实例
            task_id: 任务ID
        """
        self.db_manager = db_manager
        self.task_id = task_id

    def log_rename(
        self,
        source_path: Path,
        target_path: Path,
        data: dict[str, Any] | None = None,
    ) -> None:
        """记录重命名操作

        Args:
            source_path: 源路径
            target_path: 目标路径
            data: 附加数据
        """
        self.db_manager.log_operation(
            self.task_id, OperationType.RENAME, source_path, target_path, data
        )

    def log_move(
        self,
        source_path: Path,
        target_path: Path,
        data: dict[str, Any] | None = None,
    ) -> None:
        """记录移动操作

        Args:
            source_path: 源路径
            target_path: 目标路径
            data: 附加数据
        """
        self.db_manager.log_operation(
            self.task_id, OperationType.MOVE, source_path, target_path, data
        )

    def log_delete(self, path: Path, data: dict[str, Any] | None = None) -> None:
        """记录删除操作

        Args:
            path: 删除路径
            data: 附加数据
        """
        self.db_manager.log_operation(
            self.task_id, OperationType.DELETE, path, None, data
        )

    def log_create_dir(self, path: Path, data: dict[str, Any] | None = None) -> None:
        """记录创建目录操作

        Args:
            path: 目录路径
            data: 附加数据
        """
        self.db_manager.log_operation(
            self.task_id, OperationType.CREATE_DIR, path, None, data
        )

    def log_delete_dir(self, path: Path, data: dict[str, Any] | None = None) -> None:
        """记录删除目录操作

        Args:
            path: 目录路径
            data: 附加数据
        """
        self.db_manager.log_operation(
            self.task_id, OperationType.DELETE_DIR, path, None, data
        )
