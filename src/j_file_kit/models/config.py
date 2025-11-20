"""配置数据模型

定义应用配置相关的数据模型，包括全局配置、任务配置等。
这些模型是纯数据模型，无外部依赖（仅标准库和Pydantic）。
"""

from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T", bound=BaseModel)


class GlobalConfig(BaseModel):
    """全局配置"""

    inbox_dir: Path | None = Field(None, description="待处理目录")
    sorted_dir: Path | None = Field(None, description="已整理目录（有番号）")
    unsorted_dir: Path | None = Field(None, description="未整理目录（无番号）")
    archive_dir: Path | None = Field(None, description="归档目录")
    misc_dir: Path | None = Field(None, description="杂项目录")
    starred_dir: Path | None = Field(None, description="精选/收藏目录")


class JavVideoOrganizeConfig(BaseModel):
    """JAV视频文件整理任务配置"""

    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    archive_extensions: set[str] = Field(..., description="压缩文件扩展名")
    misc_file_delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Misc文件删除规则配置（keywords, extensions, max_size）",
    )

    @model_validator(mode="after")
    def validate_extensions(self) -> JavVideoOrganizeConfig:
        """验证扩展名格式"""
        # 确保扩展名以点号开头
        self.video_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in self.video_extensions
        }
        self.image_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in self.image_extensions
        }
        self.archive_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in self.archive_extensions
        }
        return self


class TaskConfig(BaseModel):
    """任务配置

    定义单个任务的配置，包括任务名称、类型、启用状态和任务特定配置。
    """

    name: str = Field(..., description="任务名称")
    type: Literal["file_organize", "db_update"] = Field(..., description="任务类型")
    enabled: bool = Field(True, description="是否启用")
    config: dict[str, Any] = Field(..., description="任务特定配置")

    def get_config(self, config_type: type[T]) -> T:  # type: ignore[valid-type]
        """获取类型化的配置对象"""
        return config_type.model_validate(self.config)  # type: ignore[no-any-return, attr-defined]


class AppConfig(BaseModel):
    """应用级配置

    应用级配置聚合根，包含全局配置和所有任务配置列表。
    这是应用配置的顶层模型，用于管理整个应用的配置状态。
    """

    model_config = ConfigDict(populate_by_name=True)

    global_: GlobalConfig = Field(alias="global", description="全局配置")
    tasks: list[TaskConfig] = Field(..., description="任务配置列表")

    @property
    def enabled_tasks(self) -> list[TaskConfig]:
        """获取启用的任务配置"""
        return [task for task in self.tasks if task.enabled]

    def get_task(self, name: str) -> TaskConfig | None:
        """根据名称获取任务配置"""
        for task in self.tasks:
            if task.name == name:
                return task
        return None


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
