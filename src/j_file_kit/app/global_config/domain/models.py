"""全局配置领域模型

定义应用的全局配置数据模型，管理业务目录配置。
这些模型是纯数据模型，无外部依赖（仅标准库和 Pydantic）。
"""

from pathlib import Path

from pydantic import BaseModel, Field


class GlobalConfig(BaseModel):
    """全局配置

    管理应用的业务目录配置，包括待处理目录、已整理目录等。
    这些目录用于文件任务处理的输入和输出路径。
    """

    inbox_dir: Path | None = Field(None, description="待处理目录")
    sorted_dir: Path | None = Field(None, description="已整理目录（有番号）")
    unsorted_dir: Path | None = Field(None, description="未整理目录（无番号）")
    archive_dir: Path | None = Field(None, description="归档目录")
    misc_dir: Path | None = Field(None, description="杂项目录")
    starred_dir: Path | None = Field(None, description="精选/收藏目录")


def create_default_global_config() -> GlobalConfig:
    """创建默认全局配置

    返回所有目录字段为 None 的默认配置对象，
    用于数据库初始化时提供初始配置。

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
