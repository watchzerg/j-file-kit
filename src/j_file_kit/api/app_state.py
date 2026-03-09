"""应用状态管理

管理应用的全局状态，包括配置和文件任务管理器。
在应用启动时初始化，提供统一的配置和任务管理接口。
"""

from pathlib import Path

from j_file_kit.infrastructure.file_task.file_task_manager import FileTaskManager
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_task_repository import (
    FileTaskRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.yaml.file_task_config_repository import (
    FileTaskConfigRepositoryImpl,
)


class AppState:
    """应用状态

    管理应用的全局状态，包括配置和文件任务管理器。

    作为 Composition Root，负责组装所有依赖：
    - 创建数据库连接（用于任务执行记录）
    - 创建配置仓储（YAML 文件）
    - 创建文件任务仓储（SQLite）
    - 创建 FileTaskManager
    """

    def __init__(
        self,
        *,
        base_dir: Path,
        sqlite_conn: SQLiteConnectionManager,
        config_path: Path,
    ) -> None:
        """初始化应用状态

        Args:
            base_dir: 应用基础目录
            sqlite_conn: SQLite 连接管理器
            config_path: 任务配置 YAML 文件路径
        """
        self.base_dir = base_dir
        self.db_path = sqlite_conn.db_path
        self.log_dir = self.base_dir / "logs"

        self.sqlite_conn = sqlite_conn

        # 任务配置仓储（YAML）
        self.file_task_config_repository = FileTaskConfigRepositoryImpl(config_path)

        # 文件任务仓储（SQLite）
        self.file_task_repository = FileTaskRepositoryImpl(self.sqlite_conn)

        # 文件处理结果仓储（单例，方法接收 task_id 参数）
        self.file_result_repository = FileResultRepositoryImpl(self.sqlite_conn)

        # 文件任务管理器
        self.file_task_manager: FileTaskManager = FileTaskManager(
            self.file_task_repository,
        )
