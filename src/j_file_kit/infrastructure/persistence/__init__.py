"""持久化

包含数据库管理和仓储实现。
"""

from .sqlite import (
    FileResultRepository,
    OperationRepository,
    OperationType,
    SQLiteConnectionManager,
    TaskRepository,
)

__all__ = [
    "SQLiteConnectionManager",
    "TaskRepository",
    "FileResultRepository",
    "OperationRepository",
    "OperationType",
]
