"""SQLite 持久化

提供 SQLite 数据库的连接管理和仓储实现。
"""

from .connection import SQLiteConnectionManager
from .operation_repository import OperationRepository, OperationType
from .task_repository import TaskRepository
from .task_result_repository import TaskResultRepository

__all__ = [
    "SQLiteConnectionManager",
    "TaskRepository",
    "TaskResultRepository",
    "OperationRepository",
    "OperationType",
]
