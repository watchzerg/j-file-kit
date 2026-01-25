"""任务配置仓储接口

定义任务配置管理的仓储接口，遵循依赖倒置原则。
Infrastructure 层负责实现这些接口。
"""

from typing import Protocol

from j_file_kit.app.global_config.domain.models import GlobalConfig
from j_file_kit.app.task_config.domain.models import TaskConfig


class TaskConfigRepository(Protocol):
    """任务配置仓储协议

    定义任务配置数据持久化操作的接口。
    """

    def get_by_type(self, task_type: str) -> TaskConfig | None:
        """根据任务类型获取任务配置

        Args:
            task_type: 任务类型（如 "jav_video_organizer"）

        Returns:
            任务配置对象，如果不存在则返回 None
        """
        ...

    def update(self, config: TaskConfig) -> None:
        """更新任务配置

        Args:
            config: 任务配置对象

        Raises:
            ValueError: 如果任务不存在
        """
        ...


class ConfigStateManager(Protocol):
    """配置状态管理协议

    管理配置的内存状态，提供读取和刷新功能。

    设计意图：
    - 分离 AppState 的配置状态管理职责
    - 持有配置的内存缓存（包括全局配置和任务配置）
    - 提供重新加载配置的功能
    - 虽然管理两种配置，但作为配置管理的通用基础设施定义在 task_config app
    """

    def get_global_config(self) -> GlobalConfig:
        """获取当前全局配置

        Returns:
            当前全局配置对象
        """
        ...

    def get_task_config_by_type(self, task_type: str) -> TaskConfig | None:
        """根据任务类型获取任务配置

        Args:
            task_type: 任务类型（如 "jav_video_organizer"）

        Returns:
            任务配置对象，如果不存在则返回 None
        """
        ...

    def reload_global(self) -> None:
        """从数据库重新加载全局配置到内存

        Raises:
            ValueError: 如果配置加载失败
        """
        ...

    def reload_task(self, task_type: str) -> None:
        """从数据库重新加载指定任务配置到内存

        Args:
            task_type: 任务类型（如 "jav_video_organizer"）

        Raises:
            ValueError: 如果配置加载失败
        """
        ...
