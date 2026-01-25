"""任务配置仓储接口

定义任务配置管理的仓储接口，遵循依赖倒置原则。
Infrastructure 层负责实现这些接口。
"""

from typing import Protocol

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


class TaskConfigManager(Protocol):
    """任务配置管理器协议

    管理任务配置的内存状态，提供读取和刷新功能。

    设计意图：
    - 持有任务配置的内存缓存
    - 提供重新加载配置的功能
    - 专注于任务配置管理，不涉及全局配置
    """

    def get_task_config_by_type(self, task_type: str) -> TaskConfig | None:
        """根据任务类型获取任务配置

        Args:
            task_type: 任务类型（如 "jav_video_organizer"）

        Returns:
            任务配置对象，如果不存在则返回 None
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
