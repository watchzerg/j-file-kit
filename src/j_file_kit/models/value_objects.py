"""领域值对象

定义不可变的值对象，如番号、文件信息等。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


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


class FileInfo(BaseModel):
    """文件基础信息模型

    轻量级模型，仅包含文件名相关的基础信息，避免文件系统开销。
    """

    path: Path = Field(..., description="文件路径")
    name: str = Field(..., description="文件名（不含扩展名）")
    suffix: str = Field(..., description="文件扩展名（含点号）")

    @classmethod
    def from_path(cls, path: Path) -> FileInfo:
        """从路径创建 FileInfo"""
        return cls(path=path, name=path.stem, suffix=path.suffix.lower())


class DirectoryInfo(BaseModel):
    """目录基础信息模型

    用于表示目录信息，与FileInfo对应，支持统一的扫描接口。
    设计意图：在文件处理流程中，需要同时处理文件和目录，DirectoryInfo提供了目录的统一抽象。
    """

    path: Path = Field(..., description="目录路径")
    name: str = Field(..., description="目录名")

    @classmethod
    def from_path(cls, path: Path) -> DirectoryInfo:
        """从路径创建 DirectoryInfo

        Args:
            path: 目录路径

        Returns:
            DirectoryInfo 对象
        """
        return cls(path=path, name=path.name)
