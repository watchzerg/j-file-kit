"""配置领域模型

定义应用配置相关的数据模型，包括全局配置、任务配置等。
这些模型是纯数据模型，无外部依赖（仅标准库和Pydantic）。
"""

from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class GlobalConfig(BaseModel):
    """全局配置"""

    inbox_dir: Path | None = Field(None, description="待处理目录")
    sorted_dir: Path | None = Field(None, description="已整理目录（有番号）")
    unsorted_dir: Path | None = Field(None, description="未整理目录（无番号）")
    archive_dir: Path | None = Field(None, description="归档目录")
    misc_dir: Path | None = Field(None, description="杂项目录")
    starred_dir: Path | None = Field(None, description="精选/收藏目录")


class TaskConfig(BaseModel):
    """任务配置

    定义单个任务的配置，包括任务名称、类型、启用状态和任务特定配置。
    """

    name: str = Field(..., description="任务名称")
    type: str = Field(..., description="任务类型（如 jav_video_organizer）")
    enabled: bool = Field(True, description="是否启用")
    config: dict[str, Any] = Field(..., description="任务特定配置")

    # TODO: 未来将 config 替换为判别联合配置模型，消除 Any 与 type ignore
    # 方向：为不同任务类型定义显式 Pydantic 配置模型并统一解析入口
    def get_config(self, config_type: type[T]) -> T:  # type: ignore[valid-type]
        """获取类型化的配置对象"""
        return config_type.model_validate(self.config)  # type: ignore[no-any-return, attr-defined]


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
            type="jav_video_organizer",
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
        ),
    ]
