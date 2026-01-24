"""配置状态管理器

实现 ConfigStateManager Protocol，管理配置的内存状态。
"""

from j_file_kit.app.config.domain.models import AppConfig
from j_file_kit.infrastructure.config.config_loader import load_app_config_from_db
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class ConfigManagerImpl:
    """配置状态管理实现

    持有配置的内存缓存，提供重新加载功能。

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
        self._config = load_app_config_from_db(conn_manager)

    @property
    def config(self) -> AppConfig:
        """获取当前配置

        Returns:
            当前应用配置对象
        """
        return self._config

    def reload(self) -> None:
        """从数据库重新加载配置到内存

        从数据库重新加载配置，更新内存中的配置缓存。

        Raises:
            ValueError: 如果配置加载失败
        """
        self._config = load_app_config_from_db(self._conn_manager)
