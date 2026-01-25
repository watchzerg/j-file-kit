"""配置服务

提供配置相关的业务逻辑，包括配置合并、验证和保存。
将配置管理逻辑从API层提取到服务层，符合分层架构原则。
"""

from pathlib import Path
from typing import Any

from j_file_kit.app.config.application.config_validator import validate_global_config
from j_file_kit.app.config.application.schemas import (
    UpdateGlobalConfigRequest,
    UpdateTaskConfigRequest,
)
from j_file_kit.app.config.domain.exceptions import (
    ConfigReloadError,
    ConfigUpdateError,
    InvalidConfigError,
    InvalidPathError,
    InvalidTaskConfigError,
    MissingTaskNameError,
    TaskConfigNotFoundError,
)
from j_file_kit.app.config.domain.models import GlobalConfig, TaskConfig
from j_file_kit.app.config.domain.ports import (
    ConfigStateManager,
    GlobalConfigRepository,
    TaskConfigRepository,
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
    def merge_task_config(
        current: TaskConfig,
        update: UpdateTaskConfigRequest,
    ) -> TaskConfig:
        """合并任务配置更新

        Args:
            current: 当前任务配置
            update: 更新请求

        Returns:
            合并后的任务配置
        """
        update_dict: dict[str, Any] = {}
        if update.name is not None:
            update_dict["name"] = update.name
        if update.enabled is not None:
            update_dict["enabled"] = update.enabled
        if update.config is not None:
            merged_config = ConfigService._merge_task_config_dict(
                current.config,
                update.config,
            )
            update_dict["config"] = merged_config

        if not update_dict:
            return current

        return current.model_copy(update=update_dict)

    @staticmethod
    def _merge_task_config_dict(
        current: dict[str, Any],
        update: dict[str, Any],
    ) -> dict[str, Any]:
        """合并任务配置字典更新

        Args:
            current: 当前任务配置字典
            update: 更新字典

        Returns:
            合并后的任务配置字典
        """
        if not update:
            return current

        merged = current.copy()
        merged.update(update)
        return merged

    @staticmethod
    def merge_all_task_configs(
        current_tasks: list[TaskConfig],
        task_updates: list[UpdateTaskConfigRequest],
    ) -> list[TaskConfig]:
        """合并所有任务配置更新

        Args:
            current_tasks: 当前任务列表
            task_updates: 任务更新请求列表

        Returns:
            合并后的任务列表

        Raises:
            MissingTaskNameError: 如果任务更新缺少任务名称
            TaskConfigNotFoundError: 如果任务不存在
            InvalidTaskConfigError: 如果任务配置无效
        """
        merged_tasks = current_tasks.copy()
        for task_update in task_updates:
            if task_update.name is None:
                raise MissingTaskNameError()

            task_index = None
            for i, task in enumerate(merged_tasks):
                if task.name == task_update.name:
                    task_index = i
                    break

            if task_index is None:
                raise TaskConfigNotFoundError(task_update.name)

            try:
                merged_task = ConfigService.merge_task_config(
                    merged_tasks[task_index],
                    task_update,
                )
                merged_tasks[task_index] = merged_task
            except Exception as e:
                raise InvalidTaskConfigError(task_update.name, str(e)) from e

        return merged_tasks

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

    @staticmethod
    def validate_and_save_task_configs(
        merged_tasks: list[TaskConfig],
        task_config_repository: TaskConfigRepository,
        config_manager: ConfigStateManager,
    ) -> None:
        """验证并保存任务配置列表

        验证任务配置的有效性，然后保存到数据库并重新加载到内存。

        Args:
            merged_tasks: 合并后的任务配置列表
            task_config_repository: 任务配置仓储（用于更新数据库）
            config_manager: 配置状态管理器（用于刷新内存状态）

        Raises:
            InvalidConfigError: 如果配置验证失败
            ConfigUpdateError: 如果配置更新失败
            ConfigReloadError: 如果配置重载失败
        """
        try:
            for task in merged_tasks:
                TaskConfig.model_validate(task.model_dump())
        except Exception as e:
            raise InvalidConfigError(str(e)) from e

        try:
            for task in merged_tasks:
                task_config_repository.update_task_config(task)
        except Exception as e:
            raise ConfigUpdateError(str(e)) from e

        try:
            config_manager.reload_tasks()
        except Exception as e:
            raise ConfigReloadError(str(e)) from e
