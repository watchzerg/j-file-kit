"""持久化

包含数据库管理和仓储实现。
"""

# 导出 Protocol 类型（从 interfaces 导入）
from ...interfaces.file.repositories import (
    FileItemRepository,
    FileProcessorRepository,
)
from ...interfaces.repositories import (
    TaskRepository,
    TaskRepositoryRegistry,
)

# 导出实现类（从 sqlite 导入）
from .sqlite import (
    AppConfigRepository,
    FileItemRepositoryImpl,
    FileProcessorRepositoryImpl,
    SQLiteConnectionManager,
    TaskRepositoryImpl,
    TaskRepositoryRegistryImpl,
)
