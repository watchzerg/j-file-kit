"""持久化

包含数据库管理和仓储实现。
"""

# 导出 Protocol 类型（从 interfaces 导入）
from ...interfaces.repositories import (
    CrawlerProcessorRepository,
    FileItemRepository,
    OperationRepository,
    TaskRepository,
    TaskRepositoryRegistry,
)

# 导出实现类（从 sqlite 导入）
from .sqlite import (
    AppConfigRepository,
    CrawlerProcessorRepositoryImpl,
    FileItemRepositoryImpl,
    OperationRepositoryImpl,
    SQLiteConnectionManager,
    TaskRepositoryImpl,
    TaskRepositoryRegistryImpl,
)

__all__ = [
    # Protocol 类型
    "FileItemRepository",
    "OperationRepository",
    "TaskRepository",
    "CrawlerProcessorRepository",
    "TaskRepositoryRegistry",
    # 实现类
    "SQLiteConnectionManager",
    "AppConfigRepository",
    "TaskRepositoryImpl",
    "FileItemRepositoryImpl",
    "OperationRepositoryImpl",
    "CrawlerProcessorRepositoryImpl",
    "TaskRepositoryRegistryImpl",
]
