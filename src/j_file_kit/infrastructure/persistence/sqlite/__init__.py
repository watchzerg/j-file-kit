"""SQLite 持久化

提供 SQLite 数据库的连接管理和仓储实现。
"""

from .config_repository import AppConfigRepository
from .connection import SQLiteConnectionManager
from .crawler_processor_repository import CrawlerProcessorRepositoryImpl
from .file_processor_repository import FileProcessorRepositoryImpl
from .item_result_repository import ItemResultRepositoryImpl
from .operation_repository import OperationRepositoryImpl
from .task_repository import TaskRepositoryImpl
from .task_repository_registry import TaskRepositoryRegistryImpl

__all__ = [
    "SQLiteConnectionManager",
    "AppConfigRepository",
    "TaskRepositoryImpl",
    "ItemResultRepositoryImpl",
    "OperationRepositoryImpl",
    "FileProcessorRepositoryImpl",
    "CrawlerProcessorRepositoryImpl",
    "TaskRepositoryRegistryImpl",
]
