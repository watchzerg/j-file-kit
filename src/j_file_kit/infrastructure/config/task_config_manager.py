"""任务配置管理器

实现 TaskConfigManager Protocol，管理任务配置的内存状态。
"""

from j_file_kit.app.task_config.domain.models import TaskConfig
from j_file_kit.infrastructure.persistence.sqlite.config.task_config_repository import (
    TaskConfigRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)


class TaskConfigManagerImpl:
    """任务配置管理器实现

    持有任务配置的内存缓存，提供重新加载功能。

    设计意图：
    - 实现 TaskConfigManager Protocol
    - 按需（lazy loading）从数据库加载任务配置
    - 提供 reload 方法支持配置热更新
    - 单一职责：只管理任务配置
    """

    def __init__(self, conn_manager: SQLiteConnectionManager) -> None:
        """初始化任务配置管理器

        Args:
            conn_manager: SQLite 连接管理器
        """
        self._conn_manager = conn_manager
        self._task_configs: dict[str, TaskConfig] = {}

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
