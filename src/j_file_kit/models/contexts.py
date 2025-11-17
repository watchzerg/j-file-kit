"""领域上下文模型

定义处理过程中的上下文对象，携带分析结果和中间状态。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .enums import FileType, PathItemAction, PathItemType
from .value_objects import PathItemInfo, SerialId


class ItemContext(BaseModel):
    """Item 处理上下文基类

    所有 item 处理上下文的基类，包含通用的处理状态和扩展字段。
    """

    skip_remaining: bool = Field(False, description="短路标记，跳过后续处理器")
    custom_data: dict[str, Any] = Field(default_factory=dict, description="自定义数据")


class PathItemContext(ItemContext):
    """路径项处理上下文模型

    统一处理文件和文件夹的上下文对象，携带分析结果和中间状态。
    贯穿整个路径项处理流程，支持文件和文件夹的统一处理。

    字段说明：
    - item_type: 路径项类型（文件或文件夹），用于区分处理逻辑
    - file_type: 文件类型（视频/图片/压缩/其他），仅在 item_type=FILE 时有效
    - renamed_filename: 重构后的完整文件名（含扩展名，不含路径），由 FileSerialIdExtractor 设置
    - target_path: 完整的目标路径（目录+文件名），由 FileActionDecider 设置
    """

    item_info: PathItemInfo = Field(..., description="路径项基础信息")
    item_type: PathItemType = Field(..., description="路径项类型（文件或文件夹）")
    file_type: FileType | None = Field(
        None, description="文件类型（视频/图片/压缩/其他），仅在 item_type=FILE 时有效"
    )
    serial_id: SerialId | None = Field(None, description="提取的番号")
    renamed_filename: str | None = Field(
        None, description="重构后的完整文件名（含扩展名，不含路径）"
    )
    target_path: Path | None = Field(None, description="计划的目标路径（完整路径）")
    action: PathItemAction | None = Field(None, description="决策的动作类型")
    should_delete: bool = Field(False, description="是否应该删除")
    file_size: int | None = Field(None, description="文件大小（字节）")
    item_result_id: int | None = Field(None, description="Item结果ID")
