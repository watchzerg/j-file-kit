"""配置仓储接口

定义配置仓储的协议接口，遵循依赖倒置原则。
"""

from typing import Protocol

from j_file_kit.app.config.domain.models import GlobalConfig, TaskConfig


class GlobalConfigRepository(Protocol):
    """全局配置仓储协议

    定义全局配置数据持久化操作的接口。
    """

    def get_global_config(self) -> GlobalConfig:
        """获取全局配置

        Returns:
            全局配置对象

        Raises:
            ValueError: 如果全局配置不存在
        """
        ...

    def update_global_config(self, config: GlobalConfig) -> None:
        """更新全局配置

        Args:
            config: 全局配置对象
        """
        ...


class TaskConfigRepository(Protocol):
    """任务配置仓储协议

    定义任务配置数据持久化操作的接口。
    """

    def get_all_task_configs(self) -> list[TaskConfig]:
        """获取所有任务配置

        Returns:
            任务配置列表
        """
        ...

    def get_task_config(self, name: str) -> TaskConfig | None:
        """获取单个任务配置

        Args:
            name: 任务名称

        Returns:
            任务配置对象，如果不存在则返回 None
        """
        ...

    def update_task_config(self, task: TaskConfig) -> None:
        """更新任务配置

        Args:
            task: 任务配置对象

        Raises:
            ValueError: 如果任务不存在
        """
        ...

    def create_task_config(self, task: TaskConfig) -> None:
        """创建任务配置

        Args:
            task: 任务配置对象

        Raises:
            ValueError: 如果任务已存在
        """
        ...

    def delete_task_config(self, name: str) -> None:
        """删除任务配置

        Args:
            name: 任务名称

        Raises:
            ValueError: 如果任务不存在
        """
        ...


class ConfigStateManager(Protocol):
    """配置状态管理协议

    管理配置的内存状态，提供读取和刷新功能。

    设计意图：
    - 分离 AppState 的配置状态管理职责
    - 持有配置的内存缓存
    - 提供重新加载配置的功能
    """

    def get_global_config(self) -> GlobalConfig:
        """获取当前全局配置

        Returns:
            当前全局配置对象
        """
        ...

    def get_task_configs(self) -> list[TaskConfig]:
        """获取当前任务配置列表

        Returns:
            当前任务配置列表
        """
        ...

    def reload_global(self) -> None:
        """从数据库重新加载全局配置到内存

        Raises:
            ValueError: 如果配置加载失败
        """
        ...

    def reload_tasks(self) -> None:
        """从数据库重新加载任务配置到内存

        Raises:
            ValueError: 如果配置加载失败
        """
        ...
