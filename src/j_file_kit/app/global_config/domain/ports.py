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
