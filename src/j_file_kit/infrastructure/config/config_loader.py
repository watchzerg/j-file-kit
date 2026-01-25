"""配置加载

提供从数据库加载配置的功能。
配置模型定义在 models/config.py 中。
"""

from j_file_kit.app.config.domain.models import GlobalConfig
from j_file_kit.infrastructure.persistence.sqlite.config.global_config_repository import (
    GlobalConfigRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


def load_global_config_from_db(conn_manager: SQLiteConnectionManager) -> GlobalConfig:
    """从数据库加载全局配置

    Args:
        conn_manager: SQLite 连接管理器

    Returns:
        全局配置对象

    Raises:
        ValueError: 如果配置加载失败
    """
    try:
        global_config_repository = GlobalConfigRepositoryImpl(conn_manager)
        return global_config_repository.get_global_config()
    except Exception as e:
        raise ValueError(f"从数据库加载全局配置失败: {e}") from e
