"""配置状态管理器

实现 ConfigStateManager Protocol，管理配置的内存状态。
"""

from j_file_kit.app.config.domain.models import GlobalConfig, TaskConfig
from j_file_kit.infrastructure.config.config_loader import (
    load_global_config_from_db,
    load_task_configs_from_db,
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
        self._task_configs = load_task_configs_from_db(conn_manager)

    def get_global_config(self) -> GlobalConfig:
        """获取当前全局配置

        Returns:
            当前全局配置对象
        """
        return self._global_config

    def get_task_configs(self) -> list[TaskConfig]:
        """获取当前任务配置列表

        Returns:
            当前任务配置列表
        """
        return self._task_configs

    def reload_global(self) -> None:
        """从数据库重新加载全局配置到内存

        Raises:
            ValueError: 如果配置加载失败
        """
        self._global_config = load_global_config_from_db(self._conn_manager)

    def reload_tasks(self) -> None:
        """从数据库重新加载任务配置到内存

        Raises:
            ValueError: 如果配置加载失败
        """
        self._task_configs = load_task_configs_from_db(self._conn_manager)
