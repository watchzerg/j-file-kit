"""配置加载

提供从数据库加载配置的功能。
配置模型定义在 models/config.py 中。
"""

from __future__ import annotations

from j_file_kit.models.config import AppConfig, GlobalConfig, TaskConfig

from ..persistence import AppConfigRepository, SQLiteConnectionManager


def create_default_global_config() -> GlobalConfig:
    """创建默认全局配置

    Returns:
        默认全局配置对象（所有目录字段为 None）
    """
    return GlobalConfig(
        inbox_dir=None,
        sorted_dir=None,
        unsorted_dir=None,
        archive_dir=None,
        misc_dir=None,
        starred_dir=None,
    )


def create_default_task_configs() -> list[TaskConfig]:
    """创建默认任务配置

    Returns:
        默认任务配置列表（包含 jav_video_organizer）
    """
    return [
        TaskConfig(
            name="jav_video_organizer",
            type="file_organize",
            enabled=True,
            config={
                "video_extensions": [
                    ".mp4",
                    ".avi",
                    ".mkv",
                    ".mov",
                    ".wmv",
                    ".flv",
                    ".webm",
                ],
                "image_extensions": [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                    ".bmp",
                    ".gif",
                    ".tiff",
                ],
                "archive_extensions": [
                    ".zip",
                    ".rar",
                    ".7z",
                    ".tar",
                    ".gz",
                    ".bz2",
                    ".xz",
                ],
                "misc_file_delete_rules": {
                    "keywords": ["rarbg", "sample", "preview", "temp"],
                    "extensions": [".tmp", ".temp", ".bak", ".old"],
                    "max_size": 1048576,
                },
            },
        )
    ]


def load_config_from_db(conn_manager: SQLiteConnectionManager) -> AppConfig:
    """从数据库加载配置

    Args:
        conn_manager: SQLite 连接管理器

    Returns:
        应用配置对象（AppConfig）

    Raises:
        ValueError: 如果配置加载失败
    """
    app_config_repository = AppConfigRepository(conn_manager)

    try:
        global_config = app_config_repository.get_global_config()
        tasks = app_config_repository.get_all_tasks()
        return AppConfig.model_validate({"global": global_config, "tasks": tasks})
    except Exception as e:
        raise ValueError(f"从数据库加载配置失败: {e}") from e
