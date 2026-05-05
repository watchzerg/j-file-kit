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

    调用方：应用 lifespan 中若配置文件缺失，则以此初始化磁盘上的 `task_config.yaml`。
    扩展名分类、站标去噪、Misc 删除扩展名不在此字典中，运行时由 `organizer_defaults` 注入 `JavAnalyzeConfig`。
    """
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": "/media/jav_workspace/inbox",
            "sorted_dir": "/media/jav_workspace/sorted",
            "unsorted_dir": "/media/jav_workspace/unsorted",
            "archive_dir": "/media/jav_workspace/archive",
            "misc_dir": "/media/jav_workspace/misc",
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
    """生成 raw_file_organizer 默认 `TaskConfig`（写入 YAML 时仅含路径键，扩展名由运行时注入分析配置）。"""
    base = "/media/raw_workspace"
    return TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": f"{base}/inbox",
            "folders_to_delete": f"{base}/folders_to_delete",
            "folders_video": f"{base}/folders_video",
            "folders_compressed": f"{base}/folders_compressed",
            "folders_pic": f"{base}/folders_pic",
            "folders_audio": f"{base}/folders_audio",
            "folders_misc": f"{base}/folders_misc",
            "files_video_to_delete": f"{base}/files_video_to_delete",
            "files_video_jav": f"{base}/files_video_jav",
            "files_video_us": f"{base}/files_video_us",
            "files_video_jav_vr": f"{base}/files_video_jav_vr",
            "files_video_us_vr": f"{base}/files_video_us_vr",
            "files_video_movie": f"{base}/files_video_movie",
            "files_video_misc": f"{base}/files_video_misc",
            "files_compressed": f"{base}/files_compressed",
            "files_pic": f"{base}/files_pic",
            "files_audio": f"{base}/files_audio",
            "files_misc": f"{base}/files_misc",
        },
    )
