"""领域值对象

定义不可变的值对象，如番号、文件信息等。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator, model_validator

if TYPE_CHECKING:
    from .enums import PathItemType


class SerialId(BaseModel):
    """番号模型

    结构化表示番号，包含字母前缀和数字部分。
    支持从字符串解析（"ABC-123"、"ABC_123"、"ABC123"）和转换为字符串。
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
    def parse_string_input(cls, data: Any) -> Any:
        """支持从字符串自动解析（向后兼容）"""
        if isinstance(data, str):
            return cls.from_string(data).model_dump()
        return data

    def __str__(self) -> str:
        """转换为字符串格式：PREFIX-NUMBER"""
        return f"{self.prefix}-{self.number}"


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
        from .enums import PathItemType

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
