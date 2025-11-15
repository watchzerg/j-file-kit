"""SQLite 持久化

提供 SQLite 数据库的连接管理和仓储实现。
"""

from .connection import SQLiteConnectionManager
from .file_result_repository import FileResultRepository
from .operation_repository import OperationRepository, OperationType
from .task_repository import TaskRepository

__all__ = [
    "SQLiteConnectionManager",
    "TaskRepository",
    "FileResultRepository",
    "OperationRepository",
    "OperationType",
]
