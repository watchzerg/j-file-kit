"""配置服务

提供配置相关的业务逻辑，包括配置合并、验证和保存。
将配置管理逻辑从API层提取到服务层，符合分层架构原则。
"""

from pathlib import Path
from typing import Any

from j_file_kit.app.config.application.config_validator import validate_global_config
from j_file_kit.app.config.application.schemas import UpdateGlobalConfigRequest
from j_file_kit.app.config.domain.exceptions import (
    ConfigReloadError,
    ConfigUpdateError,
    InvalidConfigError,
    InvalidPathError,
)
from j_file_kit.app.config.domain.models import GlobalConfig
from j_file_kit.app.config.domain.ports import (
    ConfigStateManager,
    GlobalConfigRepository,
)


class ConfigService:
    """配置服务

    负责配置相关的业务逻辑，包括配置合并、验证和保存。
    """

    @staticmethod
    def merge_global_config(
        current: GlobalConfig,
        update: UpdateGlobalConfigRequest,
    ) -> GlobalConfig:
        """合并全局配置更新

        Args:
            current: 当前全局配置
            update: 更新请求

        Returns:
            合并后的全局配置
        """
        update_dict: dict[str, Any] = {}
        if update.inbox_dir is not None:
            update_dict["inbox_dir"] = (
                Path(update.inbox_dir) if update.inbox_dir else None
            )
        if update.sorted_dir is not None:
            update_dict["sorted_dir"] = (
                Path(update.sorted_dir) if update.sorted_dir else None
            )
        if update.unsorted_dir is not None:
            update_dict["unsorted_dir"] = (
                Path(update.unsorted_dir) if update.unsorted_dir else None
            )
        if update.archive_dir is not None:
            update_dict["archive_dir"] = (
                Path(update.archive_dir) if update.archive_dir else None
            )
        if update.misc_dir is not None:
            update_dict["misc_dir"] = Path(update.misc_dir) if update.misc_dir else None
        if update.starred_dir is not None:
            update_dict["starred_dir"] = (
                Path(update.starred_dir) if update.starred_dir else None
            )

        if not update_dict:
            return current

        return current.model_copy(update=update_dict)

    @staticmethod
    def validate_and_save_global_config(
        merged_global: GlobalConfig,
        global_config_repository: GlobalConfigRepository,
        config_manager: ConfigStateManager,
    ) -> None:
        """验证并保存全局配置

        验证全局配置的有效性，然后保存到数据库并重新加载到内存。

        设计意图：
        - 接收 Protocol 接口而非具体实现（AppState）
        - 抛出领域异常而非 HTTPException
        - 符合依赖倒置原则，application 层不依赖 api 层

        Args:
            merged_global: 合并后的全局配置
            global_config_repository: 全局配置仓储（用于更新数据库）
            config_manager: 配置状态管理器（用于刷新内存状态）

        Raises:
            InvalidConfigError: 如果配置验证失败
            InvalidPathError: 如果路径验证失败
            ConfigUpdateError: 如果配置更新失败
            ConfigReloadError: 如果配置重载失败
        """
        try:
            GlobalConfig.model_validate(merged_global.model_dump(exclude_none=True))
        except Exception as e:
            raise InvalidConfigError(str(e)) from e

        errors = validate_global_config(merged_global)
        if errors:
            raise InvalidPathError(errors)

        try:
            global_config_repository.update_global_config(merged_global)
        except Exception as e:
            raise ConfigUpdateError(str(e)) from e

        try:
            config_manager.reload_global()
        except Exception as e:
            raise ConfigReloadError(str(e)) from e
