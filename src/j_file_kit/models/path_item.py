"""路径项相关模型

定义路径项类型、动作和信息模型。
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class PathItemType(str, Enum):
    """路径项类型枚举

    区分路径项是文件还是文件夹，这是第一层分类。
    """

    FILE = "file"
    DIRECTORY = "directory"


class PathItemAction(str, Enum):
    """路径项动作类型枚举

    统一处理文件和文件夹的操作枚举，支持文件和文件夹的各种操作。
    """

    MOVE_TO_SORTED = "move_to_sorted"  # 移动到整理目录（B/ABCD/...）
    MOVE_TO_UNSORTED = "move_to_unsorted"  # 移动到无番号目录（C）
    MOVE_TO_ARCHIVE = "move_to_archive"  # 移动到压缩文件目录
    MOVE_TO_MISC = "move_to_misc"  # 移动到其他目录（D）
    DELETE = "delete"  # 删除文件
    DELETE_DIRECTORY = "delete_directory"  # 删除目录
    SKIP = "skip"  # 跳过处理

    @property
    def description(self) -> str:
        """获取动作的中文描述"""
        descriptions = {
            PathItemAction.MOVE_TO_SORTED: "整理目录",
            PathItemAction.MOVE_TO_UNSORTED: "无番号目录",
            PathItemAction.MOVE_TO_ARCHIVE: "压缩文件目录",
            PathItemAction.MOVE_TO_MISC: "Misc文件目录",
            PathItemAction.DELETE: "删除",
            PathItemAction.DELETE_DIRECTORY: "删除目录",
            PathItemAction.SKIP: "跳过",
        }
        return descriptions.get(self, self.value)


class PathItemInfo(BaseModel):
    """路径项基础信息模型

    统一文件和文件夹的信息模型，消除类型不匹配问题。
    根据 item_type 区分文件和文件夹，文件包含 suffix，文件夹不包含。
    """

    path: Path = Field(..., description="路径")
    stem: str = Field(..., description="名称（不含扩展名）")
    suffix: str | None = Field(
        None, description="文件扩展名（含点号，仅文件有，文件夹为 None）"
    )
    item_type: str = Field(..., description="路径项类型（文件或文件夹）")

    @classmethod
    def from_path(cls, path: Path, item_type: str | PathItemType) -> PathItemInfo:
        """从路径创建 PathItemInfo

        根据 item_type 决定是否提取 suffix（文件提取，目录为 None）。

        Args:
            path: 路径
            item_type: 路径项类型（PathItemType 枚举值或字符串）

        Returns:
            PathItemInfo 对象
        """
        # 确保 item_type 是 PathItemType 枚举
        if isinstance(item_type, str):
            item_type = PathItemType(item_type)

        if item_type == PathItemType.FILE:
            return cls(
                path=path,
                stem=path.stem,
                suffix=path.suffix.lower() if path.suffix else None,
                item_type=item_type.value,
            )
        else:
            return cls(
                path=path,
                stem=path.stem,
                suffix=None,
                item_type=item_type.value,
            )
