"""首次落盘 `task_config.yaml` 时的默认 `TaskConfig` 工厂。

与具体 Pydantic 模型分离，是因为默认字典只需覆盖持久化字段；避免 lifespan 初始化链路与分析 DTO 相互 import。
"""

from j_file_kit.app.file_task.domain.constants import (
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
)
from j_file_kit.app.file_task.domain.task_config import TaskConfig


def create_default_jav_video_organizer_task_config() -> TaskConfig:
    """生成「一份可写入 YAML」的 jav_video_organizer 默认 `TaskConfig`。

    仅持久化 ``workspace_root`` 与可调删除策略；inbox/sorted 等由代码派生。
    """
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "workspace_root": "/media/jav_workspace",
            "inbox_delete_rules": {
                "exact_stems": [],
                "max_size_bytes": 0,
            },
            "video_small_delete_bytes": 200 * 1024 * 1024,
            "misc_file_delete_rules": {
                "max_size": 1048576,
            },
        },
    )


def create_default_raw_file_organizer_task_config() -> TaskConfig:
    """生成 raw_file_organizer 默认 `TaskConfig`（仅 workspace 根）。"""
    return TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={
            "workspace_root": "/media/raw_workspace",
        },
    )
