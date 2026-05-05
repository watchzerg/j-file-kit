"""File task 配置服务。

提供 file task 配置的读取、验证和更新功能。
"""

from typing import Any

from j_file_kit.app.file_task.application.config_validator import (
    validate_jav_video_organizer_config,
    validate_raw_file_organizer_config,
)
from j_file_kit.app.file_task.application.jav_task_config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.raw_task_config import RawFileOrganizeConfig
from j_file_kit.app.file_task.domain.constants import (
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
)
from j_file_kit.app.file_task.domain.ports import TaskConfigRepository
from j_file_kit.app.file_task.domain.task_config import TaskConfig


class FileTaskConfigService:
    """File task 配置服务。

    负责 file task 配置的业务逻辑，包括读取、验证和保存。
    """

    @staticmethod
    def get_jav_video_organizer_config(
        task_config_repository: TaskConfigRepository,
    ) -> JavVideoOrganizeConfig:
        """获取 JAV 视频整理任务配置。

        Args:
            task_config_repository: 任务配置仓储

        Returns:
            类型化的配置对象

        Raises:
            ValueError: 如果配置不存在或解析失败
        """
        task_config = task_config_repository.get_by_type(
            TASK_TYPE_JAV_VIDEO_ORGANIZER,
        )
        if task_config is None:
            raise ValueError(f"任务配置不存在: {TASK_TYPE_JAV_VIDEO_ORGANIZER}")

        return JavVideoOrganizeConfig.model_validate(task_config.config)

    @staticmethod
    def merge_jav_video_organizer_config(
        current_raw: dict[str, Any],
        update: dict[str, Any],
    ) -> JavVideoOrganizeConfig:
        """合并 JAV 视频整理任务配置更新。

        从存储的原始 dict 出发做合并，避免对旧数据重复触发 model_validator（如 JAV_MEDIA_ROOT 约束）。

        Args:
            current_raw: 存储层的原始配置字典
            update: 更新字典（部分更新）

        Returns:
            合并后的配置对象
        """
        merged_dict = {**current_raw, **update}
        return JavVideoOrganizeConfig.model_validate(merged_dict)

    @staticmethod
    def validate_and_save_jav_video_organizer_config(
        merged_config: JavVideoOrganizeConfig,
        task_config_repository: TaskConfigRepository,
        enabled: bool | None = None,
    ) -> None:
        """验证并保存 JAV 视频整理任务配置。

        验证目录配置（inbox_dir 必填、路径冲突检查），然后在单次写入中同时持久化
        config 和可选的 enabled 字段，避免多次 I/O。

        Args:
            merged_config: 合并后的配置
            task_config_repository: 任务配置仓储
            enabled: 可选，如果提供则同时更新启用状态

        Raises:
            ValueError: 如果配置验证失败（目录缺失、路径冲突等）
        """
        errors = validate_jav_video_organizer_config(merged_config)
        if errors:
            raise ValueError(
                "目录配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors),
            )

        task_config = FileTaskConfigService._get_jav_video_task_config(
            task_config_repository,
        )

        update_dict: dict[str, object] = {
            "config": merged_config.model_dump(mode="json"),
        }
        if enabled is not None:
            update_dict["enabled"] = enabled

        updated_task_config = task_config.model_copy(update=update_dict)
        task_config_repository.update(updated_task_config)

    @staticmethod
    def get_raw_file_organizer_config(
        task_config_repository: TaskConfigRepository,
    ) -> RawFileOrganizeConfig:
        """获取 Raw 收件箱整理任务配置。"""
        task_config = task_config_repository.get_by_type(TASK_TYPE_RAW_FILE_ORGANIZER)
        if task_config is None:
            raise ValueError(f"任务配置不存在: {TASK_TYPE_RAW_FILE_ORGANIZER}")
        return RawFileOrganizeConfig.model_validate(task_config.config)

    @staticmethod
    def merge_raw_file_organizer_config(
        current_raw: dict[str, Any],
        update: dict[str, Any],
    ) -> RawFileOrganizeConfig:
        """合并 Raw 任务部分更新为强类型配置。"""
        merged_dict = {**current_raw, **update}
        return RawFileOrganizeConfig.model_validate(merged_dict)

    @staticmethod
    def validate_and_save_raw_file_organizer_config(
        merged_config: RawFileOrganizeConfig,
        task_config_repository: TaskConfigRepository,
        enabled: bool | None = None,
    ) -> None:
        """验证并保存 raw_file_organizer 配置。"""
        errors = validate_raw_file_organizer_config(merged_config)
        if errors:
            raise ValueError(
                "目录配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors),
            )

        task_config = FileTaskConfigService._get_raw_file_task_config(
            task_config_repository,
        )
        update_dict: dict[str, object] = {
            "config": merged_config.model_dump(mode="json"),
        }
        if enabled is not None:
            update_dict["enabled"] = enabled

        updated_task_config = task_config.model_copy(update=update_dict)
        task_config_repository.update(updated_task_config)

    @staticmethod
    def _get_raw_file_task_config(
        task_config_repository: TaskConfigRepository,
    ) -> TaskConfig:
        task_config = task_config_repository.get_by_type(
            TASK_TYPE_RAW_FILE_ORGANIZER,
        )
        if task_config is None:
            raise ValueError(f"任务配置不存在: {TASK_TYPE_RAW_FILE_ORGANIZER}")
        return task_config

    @staticmethod
    def _get_jav_video_task_config(
        task_config_repository: TaskConfigRepository,
    ) -> TaskConfig:
        task_config = task_config_repository.get_by_type(
            TASK_TYPE_JAV_VIDEO_ORGANIZER,
        )
        if task_config is None:
            raise ValueError(f"任务配置不存在: {TASK_TYPE_JAV_VIDEO_ORGANIZER}")
        return task_config
