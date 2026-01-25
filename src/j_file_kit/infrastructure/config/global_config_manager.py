"""全局配置管理器

实现 GlobalConfigManager Protocol，管理全局配置的内存状态。
"""

from j_file_kit.app.global_config.domain.models import GlobalConfig
from j_file_kit.infrastructure.persistence.sqlite.config.global_config_repository import (
    GlobalConfigRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class GlobalConfigManagerImpl:
    """全局配置管理器实现

    持有全局配置的内存缓存，提供重新加载功能。

    设计意图：
    - 实现 GlobalConfigManager Protocol
    - 在启动时从数据库加载配置到内存
    - 提供 reload 方法支持配置热更新
    - 单一职责：只管理全局配置
    """

    def __init__(self, conn_manager: SQLiteConnectionManager) -> None:
        """初始化全局配置管理器

        Args:
            conn_manager: SQLite 连接管理器
        """
        self._conn_manager = conn_manager
        self._global_config = self._load_from_db()

    def get_global_config(self) -> GlobalConfig:
        """获取当前全局配置

        Returns:
            当前全局配置对象
        """
        return self._global_config

    def reload_global(self) -> None:
        """从数据库重新加载全局配置到内存

        Raises:
            ValueError: 如果配置加载失败
        """
        self._global_config = self._load_from_db()

    def _load_from_db(self) -> GlobalConfig:
        """从数据库加载全局配置

        Returns:
            全局配置对象

        Raises:
            ValueError: 如果配置加载失败
        """
        try:
            repository = GlobalConfigRepositoryImpl(self._conn_manager)
            return repository.get_global_config()
        except Exception as e:
            raise ValueError(f"从数据库加载全局配置失败: {e}") from e
