"""文件任务领域模型

定义文件任务domain专用的领域模型和核心概念。

本模块包含文件处理相关的所有领域模型，包括：
- 路径项类型枚举（PathEntryType）
- 文件类型枚举（FileType）
- 操作类型枚举（OperationType）
- 番号值对象（SerialId）
- 操作记录模型（Operation）

这些模型是文件domain的核心概念，专门用于文件处理任务，不属于跨domain的通用模型。
"""

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# Pydantic model_validator 需要接受 Any 类型
# ruff: noqa: ANN401


# ============================================================================
# 枚举类型
# ============================================================================


class PathEntryType(str, Enum):
    """路径项类型枚举

    区分路径项是文件还是文件夹，用于目录扫描和遍历操作。
    """

    FILE = "file"
    DIRECTORY = "directory"


class FileType(str, Enum):
    """文件类型枚举

    用于区分不同类型的文件（视频、图片、压缩包、其他）。
    这是文件domain的核心概念，用于文件分类和处理决策。
    """

    VIDEO = "video"
    IMAGE = "image"
    ARCHIVE = "archive"
    MISC = "misc"


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
