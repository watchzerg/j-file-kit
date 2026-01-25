"""配置状态管理器

实现 ConfigStateManager Protocol，管理配置的内存状态。
"""

from j_file_kit.app.config.domain.models import GlobalConfig, TaskConfig
from j_file_kit.infrastructure.config.config_loader import load_global_config_from_db
from j_file_kit.infrastructure.persistence.sqlite.config.task_config_repository import (
    TaskConfigRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class ConfigManagerImpl:
    """配置状态管理实现

    持有配置的内存缓存，提供分离的重新加载功能。

    设计意图：
    - 从 AppState 提取配置状态管理职责
    - 作为 ConfigStateManager Protocol 的实现
    - 在 infrastructure 层实现，由 AppState (Composition Root) 创建
    """

    def __init__(self, conn_manager: SQLiteConnectionManager) -> None:
        """初始化配置管理器

        Args:
            conn_manager: SQLite 连接管理器
        """
        self._conn_manager = conn_manager
        self._global_config = load_global_config_from_db(conn_manager)
        self._task_configs: dict[str, TaskConfig] = {}

    def get_global_config(self) -> GlobalConfig:
        """获取当前全局配置

        Returns:
            当前全局配置对象
        """
        return self._global_config

    def get_task_config_by_type(self, task_type: str) -> TaskConfig | None:
        """根据任务类型获取任务配置

        Args:
            task_type: 任务类型

        Returns:
            任务配置对象，如果不存在则返回 None
        """
        if task_type not in self._task_configs:
            repository = TaskConfigRepositoryImpl(self._conn_manager)
            config = repository.get_by_type(task_type)
            if config is None:
                return None
            self._task_configs[task_type] = config
        return self._task_configs[task_type]

    def reload_global(self) -> None:
        """从数据库重新加载全局配置到内存

        Raises:
            ValueError: 如果配置加载失败
        """
        self._global_config = load_global_config_from_db(self._conn_manager)

    def reload_task(self, task_type: str) -> None:
        """从数据库重新加载指定任务配置到内存

        Args:
            task_type: 任务类型

        Raises:
            ValueError: 如果配置加载失败
        """
        repository = TaskConfigRepositoryImpl(self._conn_manager)
        config = repository.get_by_type(task_type)
        if config is None:
            raise ValueError(f"任务配置不存在: {task_type}")
        self._task_configs[task_type] = config
