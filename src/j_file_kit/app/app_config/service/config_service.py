"""配置服务

提供配置相关的业务逻辑，包括配置合并、验证和保存。
将配置管理逻辑从API层提取到服务层，符合分层架构原则。
"""

from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from j_file_kit.app.app_config.domain import AppConfig, GlobalConfig, TaskConfig
from j_file_kit.app.app_config.schemas import (
    UpdateGlobalConfigRequest,
    UpdateTaskConfigRequest,
)
from j_file_kit.infrastructure.app_state import AppState
from j_file_kit.shared.utils.config_utils import validate_global_config


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
            HTTPException: 如果任务更新失败
        """
        merged_tasks = current_tasks.copy()
        for task_update in task_updates:
            if task_update.name is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "MISSING_TASK_NAME",
                        "message": "更新任务配置时必须提供任务名称",
                    },
                )

            task_index = None
            for i, task in enumerate(merged_tasks):
                if task.name == task_update.name:
                    task_index = i
                    break

            if task_index is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "TASK_NOT_FOUND",
                        "message": f"任务不存在: {task_update.name}",
                    },
                )

            try:
                merged_task = ConfigService.merge_task_config(
                    merged_tasks[task_index],
                    task_update,
                )
                merged_tasks[task_index] = merged_task
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_TASK_CONFIG",
                        "message": f"更新任务 '{task_update.name}' 配置失败: {str(e)}",
                    },
                ) from e

        return merged_tasks

    @staticmethod
    def validate_and_save_config(
        merged_global: GlobalConfig,
        merged_tasks: list[TaskConfig],
        app_state: AppState,
    ) -> None:
        """验证并保存配置

        验证配置的有效性，然后保存到数据库并重新加载到内存。

        Args:
            merged_global: 合并后的全局配置
            merged_tasks: 合并后的任务配置列表
            app_state: 应用状态

        Raises:
            HTTPException: 如果配置验证或保存失败
        """
        # 验证配置模型
        try:
            AppConfig.model_validate({"global": merged_global, "tasks": merged_tasks})
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_CONFIG", "message": f"配置验证失败: {str(e)}"},
            ) from e

        # 验证路径（使用统一的验证函数）
        errors = validate_global_config(merged_global)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_PATH",
                    "message": "目录配置验证失败:\n"
                    + "\n".join(f"  - {e}" for e in errors),
                },
            )

        # 更新数据库
        try:
            app_state.app_config_repository.update_global_config(merged_global)
            for task in merged_tasks:
                app_state.app_config_repository.update_task(task)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "CONFIG_UPDATE_FAILED",
                    "message": f"更新配置失败: {str(e)}",
                },
            ) from e

        # 重新加载配置到内存
        try:
            app_state.reload_config()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "CONFIG_RELOAD_FAILED",
                    "message": f"重新加载配置失败: {str(e)}",
                },
            ) from e
