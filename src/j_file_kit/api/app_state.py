"""应用状态管理

管理应用的全局状态，包括配置和任务管理器。
在应用启动时初始化，提供统一的配置和任务管理接口。
"""

from pathlib import Path

from j_file_kit.app.config.domain.models import AppConfig
from j_file_kit.infrastructure.config.config_manager import ConfigManagerImpl
from j_file_kit.infrastructure.persistence.sqlite.config.config_repository import (
    AppConfigRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.task.file_item_repository import (
    FileItemRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.task.file_processor_repository import (
    FileProcessorRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.task.task_repository import (
    TaskRepositoryImpl,
)
from j_file_kit.infrastructure.task.task_manager import TaskManager


class AppState:
    """应用状态

    管理应用的全局状态，包括配置和任务管理器。

    作为 Composition Root，负责组装所有依赖：
    - 创建数据库连接
    - 创建 repositories（单例）
    - 创建 ConfigManager（管理配置状态）
    - 创建 TaskManager
    """

    def __init__(
        self,
        *,
        base_dir: Path,
        sqlite_conn: SQLiteConnectionManager,
    ) -> None:
        """初始化应用状态

        Args:
            base_dir: 应用基础目录
            sqlite_conn: SQLite 连接管理器
        """
        self.base_dir = base_dir
        self.db_path = sqlite_conn.db_path
        self.log_dir = self.base_dir / "logs"

        # 连接管理器由 lifespan 创建并初始化 schema
        self.sqlite_conn = sqlite_conn

        # 创建应用配置仓储（会自动初始化默认配置）
        self.app_config_repository = AppConfigRepositoryImpl(self.sqlite_conn)

        # 创建配置管理器（替代原来的 self.config 和 reload_config）
        self.config_manager = ConfigManagerImpl(self.sqlite_conn)

        # 创建任务仓储
        self.task_repository = TaskRepositoryImpl(self.sqlite_conn)

        # 创建文件任务 repositories（单例，方法接收 task_id 参数）
        self.file_item_repository = FileItemRepositoryImpl(self.sqlite_conn)
        self.file_processor_repository = FileProcessorRepositoryImpl(self.sqlite_conn)

        # 创建任务管理器
        self.task_manager: TaskManager = TaskManager(self.task_repository)

    @property
    def config(self) -> AppConfig:
        """获取当前配置（委托给 ConfigManager）

        Returns:
            当前应用配置对象
        """
        return self.config_manager.config
