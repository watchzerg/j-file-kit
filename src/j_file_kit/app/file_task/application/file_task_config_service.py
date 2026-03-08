"""File task 配置服务。

提供 file task 配置的读取、验证和更新功能。
"""

from typing import Any

from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.task_config.domain.models import TaskConfig
from j_file_kit.app.task_config.domain.ports import TaskConfigRepository


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
        current: JavVideoOrganizeConfig,
        update: dict[str, Any],
    ) -> JavVideoOrganizeConfig:
        """合并 JAV 视频整理任务配置更新。

        Args:
            current: 当前配置
            update: 更新字典（部分更新）

        Returns:
            合并后的配置对象
        """
        if not update:
            return current

        merged_dict = current.model_dump()
        merged_dict.update(update)
        return JavVideoOrganizeConfig.model_validate(merged_dict)

    @staticmethod
    def validate_and_save_jav_video_organizer_config(
        merged_config: JavVideoOrganizeConfig,
        task_config_repository: TaskConfigRepository,
    ) -> None:
        """验证并保存 JAV 视频整理任务配置。

        Args:
            merged_config: 合并后的配置
            task_config_repository: 任务配置仓储

        Raises:
            ValueError: 如果配置验证或保存失败
        """
        task_config = FileTaskConfigService._get_jav_video_task_config(
            task_config_repository,
        )

        updated_task_config = task_config.model_copy(
            update={"config": merged_config.model_dump(exclude_none=True)},
        )

        task_config_repository.update(updated_task_config)

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
