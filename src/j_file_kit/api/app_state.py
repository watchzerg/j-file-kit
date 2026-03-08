"""应用状态管理

管理应用的全局状态，包括配置和任务管理器。
在应用启动时初始化，提供统一的配置和任务管理接口。
"""

from pathlib import Path

from j_file_kit.app.global_config.domain.models import GlobalConfig
from j_file_kit.infrastructure.persistence.sqlite.config.global_config_repository import (
    GlobalConfigRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.config.task_config_repository import (
    TaskConfigRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.task.file_result_repository import (
    FileResultRepositoryImpl,
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
    - 创建配置仓储（读取与更新）
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

        # 创建配置仓储（按 global/task 拆分）
        self.global_config_repository = GlobalConfigRepositoryImpl(self.sqlite_conn)
        self.task_config_repository = TaskConfigRepositoryImpl(self.sqlite_conn)

        # 创建任务仓储
        self.task_repository = TaskRepositoryImpl(self.sqlite_conn)

        # 创建文件任务 repositories（单例，方法接收 task_id 参数）
        self.file_result_repository = FileResultRepositoryImpl(self.sqlite_conn)

        # 创建任务管理器
        self.task_manager: TaskManager = TaskManager(self.task_repository)

    def get_global_config(self) -> GlobalConfig:
        """获取当前全局配置"""
        return self.global_config_repository.get_global_config()
