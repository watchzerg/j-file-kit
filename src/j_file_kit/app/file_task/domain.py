"""文件任务领域模型

定义文件任务domain专用的领域模型和核心概念。

本模块包含文件处理相关的所有领域模型，包括：
- 文件类型枚举（FileType）
- 路径项相关模型（PathEntryType、PathEntryAction、PathEntryInfo）
- 路径项处理上下文（PathEntryContext）
- 文件处理结果（FileItemResult）
- 文件操作相关模型（OperationType、Operation）
- 番号值对象（SerialId）

这些模型是文件domain的核心概念，专门用于文件处理任务，不属于跨domain的通用模型。
"""

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from j_file_kit.shared.models.contexts import ItemContext
from j_file_kit.shared.models.results import ItemResult

# Pydantic model_validator 需要接受 Any 类型
# ruff: noqa: ANN401


# ============================================================================
# 枚举类型
# ============================================================================


class FileType(str, Enum):
    """文件类型枚举

    用于区分不同类型的文件（视频、图片、压缩包、其他）。
    这是文件domain的核心概念，用于文件分类和处理决策。
    """

    VIDEO = "video"
    IMAGE = "image"
    ARCHIVE = "archive"
    MISC = "misc"


class PathEntryType(str, Enum):
    """路径项类型枚举

    区分路径项是文件还是文件夹，这是第一层分类。
    用于统一处理文件和文件夹的处理流程。
    """

    FILE = "file"
    DIRECTORY = "directory"


class PathEntryAction(str, Enum):
    """路径项动作类型枚举

    统一处理文件和文件夹的操作枚举，支持文件和文件夹的各种操作。
    用于决策处理器应该执行什么操作（移动、删除、跳过等）。
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
            PathEntryAction.MOVE_TO_SORTED: "整理目录",
            PathEntryAction.MOVE_TO_UNSORTED: "无番号目录",
            PathEntryAction.MOVE_TO_ARCHIVE: "压缩文件目录",
            PathEntryAction.MOVE_TO_MISC: "Misc文件目录",
            PathEntryAction.DELETE: "删除",
            PathEntryAction.DELETE_DIRECTORY: "删除目录",
            PathEntryAction.SKIP: "跳过",
        }
        return descriptions.get(self, self.value)


class OperationType(str, Enum):
    """操作类型枚举

    只用于文件操作，不包含目录操作。
    用于记录文件操作历史（移动、删除、重命名等）。
    """

    RENAME = "rename"
    MOVE = "move"
    DELETE = "delete"


# ============================================================================
# 值对象
# ============================================================================


class SerialId(BaseModel):
    """番号值对象

    结构化表示番号，包含字母前缀和数字部分。
    支持从字符串解析（"ABC-123"、"ABC_123"、"ABC123"）和转换为字符串。
    这是文件domain的核心值对象，用于JAV视频文件的番号识别和整理。

    设计意图：
    - 封装番号的验证逻辑，确保番号格式的一致性
    - 提供统一的番号表示方式，便于文件名生成和目录组织
    """

    prefix: str = Field(..., description="字母前缀（2-5个大写字母）")
    number: str = Field(..., description="数字部分（2-5个数字）")

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        """验证字母前缀"""
        v_upper = v.upper()
        if not v_upper.isalpha():
            raise ValueError("前缀必须只包含字母")
        if not (2 <= len(v_upper) <= 5):
            raise ValueError("前缀长度必须在2-5个字符之间")
        return v_upper

    @field_validator("number")
    @classmethod
    def validate_number(cls, v: str) -> str:
        """验证数字部分"""
        if not v.isdigit():
            raise ValueError("数字部分必须只包含数字")
        if not (2 <= len(v) <= 5):
            raise ValueError("数字部分长度必须在2-5个字符之间")
        return v

    @classmethod
    def from_string(cls, value: str) -> SerialId:
        """从字符串解析番号

        支持格式：
        - "ABC-123"（连字符分隔）
        - "ABC_123"（下划线分隔）
        - "ABC123"（无分隔符）

        Args:
            value: 番号字符串

        Returns:
            SerialId 对象

        Raises:
            ValueError: 如果字符串格式无效

        Examples:
            >>> SerialId.from_string("ABC-123")
            SerialId(prefix='ABC', number='123')
            >>> SerialId.from_string("ABC_123")
            SerialId(prefix='ABC', number='123')
            >>> SerialId.from_string("ABC123")
            SerialId(prefix='ABC', number='123')
        """
        # 支持连字符、下划线或无分隔符
        pattern = r"^([A-Za-z]{2,5})[-_]?(\d{2,5})$"
        match = re.match(pattern, value)
        if not match:
            raise ValueError(f"无效的番号格式: {value}")
        prefix = match.group(1).upper()
        number = match.group(2)
        return cls(prefix=prefix, number=number)

    @model_validator(mode="before")
    @classmethod
    def parse_string_input(cls, data: Any) -> Any:  # noqa: ANN401
        """支持从字符串自动解析（向后兼容）"""
        if isinstance(data, str):
            return cls.from_string(data).model_dump()
        return data

    def __str__(self) -> str:
        """转换为字符串格式：PREFIX-NUMBER"""
        return f"{self.prefix}-{self.number}"


# ============================================================================
# 数据模型
# ============================================================================


class PathEntryInfo(BaseModel):
    """路径项基础信息模型

    统一文件和文件夹的信息模型，消除类型不匹配问题。
    根据 item_type 区分文件和文件夹，文件包含 suffix，文件夹不包含。

    设计意图：
    - 统一文件和文件夹的信息表示，简化处理流程
    - 封装路径解析逻辑，确保路径信息的一致性
    """

    path: Path = Field(..., description="路径")
    stem: str = Field(..., description="名称（不含扩展名）")
    suffix: str | None = Field(
        None,
        description="文件扩展名（含点号，仅文件有，文件夹为 None）",
    )
    item_type: str = Field(..., description="路径项类型（文件或文件夹）")

    @classmethod
    def from_path(cls, path: Path, item_type: str | PathEntryType) -> PathEntryInfo:
        """从路径创建 PathEntryInfo

        根据 item_type 决定是否提取 suffix（文件提取，目录为 None）。

        Args:
            path: 路径
            item_type: 路径项类型（PathEntryType 枚举值或字符串）

        Returns:
            PathEntryInfo 对象
        """
        # 确保 item_type 是 PathEntryType 枚举
        if isinstance(item_type, str):
            item_type = PathEntryType(item_type)

        if item_type == PathEntryType.FILE:
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


class PathEntryContext(ItemContext):
    """路径项处理上下文模型

    统一处理文件和文件夹的上下文对象，携带分析结果和中间状态。
    贯穿整个路径项处理流程，支持文件和文件夹的统一处理。

    设计意图：
    - 作为处理器链中传递的上下文对象，携带分析结果和决策信息
    - 支持文件和文件夹的统一处理流程，简化处理器实现

    字段说明：
    - item_type: 路径项类型（文件或文件夹），用于区分处理逻辑
    - file_type: 文件类型（视频/图片/压缩/其他），仅在 item_type=FILE 时有效
    - renamed_filename: 重构后的完整文件名（含扩展名，不含路径），由 FileSerialIdExtractor 设置
    - target_path: 完整的目标路径（目录+文件名），由 FileActionDecider 设置
    """

    item_info: PathEntryInfo = Field(..., description="路径项基础信息")
    item_type: PathEntryType = Field(..., description="路径项类型（文件或文件夹）")
    file_type: FileType | None = Field(
        None,
        description="文件类型（视频/图片/压缩/其他），仅在 item_type=FILE 时有效",
    )
    serial_id: SerialId | None = Field(None, description="提取的番号")
    renamed_filename: str | None = Field(
        None,
        description="重构后的完整文件名（含扩展名，不含路径）",
    )
    target_path: Path | None = Field(None, description="计划的目标路径（完整路径）")
    action: PathEntryAction | None = Field(None, description="决策的动作类型")
    file_size: int | None = Field(None, description="文件大小（字节）")
    item_result_id: int | None = Field(None, description="Item结果ID")


class Operation(BaseModel):
    """操作记录模型

    表示一个文件操作记录，包含操作类型、路径信息、时间戳等。
    用于持久化文件操作历史，支持查询和统计。
    只记录文件操作，不记录目录操作。

    设计意图：
    - 记录文件操作历史，支持审计和统计
    - 使用冗余字段（file_type、serial_id）避免JOIN查询，提高性能
    """

    id: str = Field(..., description="操作ID（UUID字符串）")
    task_id: int = Field(..., description="任务ID")
    file_item_id: int | None = Field(None, description="文件项ID（可选）")
    timestamp: datetime = Field(..., description="操作时间")
    operation: OperationType = Field(..., description="操作类型")
    source_path: Path = Field(..., description="源路径")
    target_path: Path | None = Field(None, description="目标路径（可选）")
    file_type: str | None = Field(None, description="文件类型（冗余字段，避免JOIN）")
    serial_id: str | None = Field(None, description="番号（冗余字段，避免JOIN）")


class FileItemResult(ItemResult):
    """文件处理结果

    文件类型的 item 处理结果，继承 ItemResult 并添加文件特定的字段。
    现在统一处理文件和文件夹，但主要用于文件处理结果。

    设计意图：
    - 封装文件处理结果，包含处理上下文和处理结果
    - 支持文件处理流程的结果持久化和查询
    """

    item_info: PathEntryInfo = Field(..., description="路径项信息")
    context: PathEntryContext = Field(..., description="处理上下文")
