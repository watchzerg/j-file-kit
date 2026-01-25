"""配置加载

提供从数据库加载配置的功能。
配置模型定义在 models/config.py 中。
"""

from j_file_kit.app.config.domain.models import AppConfig
from j_file_kit.infrastructure.persistence.sqlite.config.global_config_repository import (
    GlobalConfigRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.config.task_config_repository import (
    TaskConfigRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


def load_app_config_from_db(conn_manager: SQLiteConnectionManager) -> AppConfig:
    """从数据库加载配置

    Args:
        conn_manager: SQLite 连接管理器

    Returns:
        应用配置对象（AppConfig）

    Raises:
        ValueError: 如果配置加载失败
    """
    global_config_repository = GlobalConfigRepositoryImpl(conn_manager)
    task_config_repository = TaskConfigRepositoryImpl(conn_manager)

    try:
        global_config = global_config_repository.get_global_config()
        tasks = task_config_repository.get_all_task_configs()
        return AppConfig.model_validate({"global": global_config, "tasks": tasks})
    except Exception as e:
        raise ValueError(f"从数据库加载配置失败: {e}") from e
