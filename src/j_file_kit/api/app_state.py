"""应用状态管理

管理应用的全局状态，包括配置和任务管理器。
在应用启动时初始化，提供统一的配置和任务管理接口。
"""

import os
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
from j_file_kit.shared.utils.file_utils import ensure_directory


class AppState:
    """应用状态

    管理应用的全局状态，包括配置和任务管理器。

    作为 Composition Root，负责组装所有依赖：
    - 创建数据库连接
    - 创建 repositories（单例）
    - 创建 ConfigManager（管理配置状态）
    - 创建 TaskManager
    """

    def __init__(self) -> None:
        """初始化应用状态

        从环境变量 J_FILE_KIT_BASE_DIR 读取基础目录（默认 `.app-data`），
        确定固定路径，创建配置仓储，从数据库加载配置。
        """
        # 从环境变量读取基础目录
        self.base_dir = Path(os.getenv("J_FILE_KIT_BASE_DIR", ".app-data"))

        # 确定固定路径
        self.db_path = self.base_dir / "sqlite" / "j_file_kit.db"
        self.log_dir = self.base_dir / "logs"

        # 创建必要的目录
        ensure_directory(self.base_dir / "sqlite", parents=True)
        ensure_directory(self.log_dir, parents=True)

        # 创建 SQLite 连接管理器（表结构在 __init__ 中自动创建）
        self.sqlite_conn = SQLiteConnectionManager(self.db_path)

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
