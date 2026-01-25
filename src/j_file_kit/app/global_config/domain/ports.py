"""全局配置仓储接口

定义全局配置仓储的协议接口，遵循依赖倒置原则。
Infrastructure 层负责实现这些接口。
"""

from typing import Protocol

from j_file_kit.app.global_config.domain.models import GlobalConfig


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


class GlobalConfigManager(Protocol):
    """全局配置管理器协议

    管理全局配置的内存状态，提供读取和刷新功能。

    设计意图：
    - 持有全局配置的内存缓存
    - 提供重新加载配置的功能
    - 分离 global_config 和 task_config 的管理职责
    """

    def get_global_config(self) -> GlobalConfig:
        """获取当前全局配置

        Returns:
            当前全局配置对象
        """
        ...

    def reload_global(self) -> None:
        """从数据库重新加载全局配置到内存

        Raises:
            ValueError: 如果配置加载失败
        """
        ...
