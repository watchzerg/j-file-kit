"""配置管理

提供配置模型和从数据库加载配置的功能。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..persistence import ConfigRepository, SQLiteConnectionManager

T = TypeVar("T", bound=BaseModel)


class GlobalConfig(BaseModel):
    """全局配置"""

    inbox_dir: Path | None = Field(None, description="待处理目录")
    sorted_dir: Path | None = Field(None, description="已整理目录（有番号）")
    unsorted_dir: Path | None = Field(None, description="未整理目录（无番号）")
    archive_dir: Path | None = Field(None, description="归档目录")
    misc_dir: Path | None = Field(None, description="杂项目录")
    starred_dir: Path | None = Field(None, description="精选/收藏目录")


class FileOrganizeConfig(BaseModel):
    """文件整理任务配置"""

    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    archive_extensions: set[str] = Field(..., description="压缩文件扩展名")
    misc_file_delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Misc文件删除规则配置（keywords, extensions, max_size）",
    )

    @model_validator(mode="after")
    def validate_extensions(self) -> FileOrganizeConfig:
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


class TaskDefinition(BaseModel):
    """任务定义"""

    name: str = Field(..., description="任务名称")
    type: Literal["file_organize", "db_update"] = Field(..., description="任务类型")
    enabled: bool = Field(True, description="是否启用")
    config: dict[str, Any] = Field(..., description="任务特定配置")

    def get_config(self, config_type: type[T]) -> T:  # type: ignore[valid-type]
        """获取类型化的配置对象"""
        return config_type.model_validate(self.config)  # type: ignore[no-any-return, attr-defined]


class TaskConfig(BaseModel):
    """完整任务配置"""

    model_config = ConfigDict(populate_by_name=True)

    global_: GlobalConfig = Field(alias="global", description="全局配置")
    tasks: list[TaskDefinition] = Field(..., description="任务列表")

    @property
    def enabled_tasks(self) -> list[TaskDefinition]:
        """获取启用的任务"""
        return [task for task in self.tasks if task.enabled]

    def get_task(self, name: str) -> TaskDefinition | None:
        """根据名称获取任务"""
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


def create_default_task_configs() -> list[TaskDefinition]:
    """创建默认任务配置

    Returns:
        默认任务配置列表（包含 jav_video_organizer）
    """
    return [
        TaskDefinition(
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


def load_config_from_db(conn_manager: SQLiteConnectionManager) -> TaskConfig:
    """从数据库加载配置

    Args:
        conn_manager: SQLite 连接管理器

    Returns:
        配置对象

    Raises:
        ValueError: 如果配置加载失败
    """
    config_repository = ConfigRepository(conn_manager)

    try:
        global_config = config_repository.get_global_config()
        tasks = config_repository.get_all_tasks()
        return TaskConfig.model_validate({"global": global_config, "tasks": tasks})
    except Exception as e:
        raise ValueError(f"从数据库加载配置失败: {e}") from e
