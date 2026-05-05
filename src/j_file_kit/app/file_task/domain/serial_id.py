"""JAV 番号值对象与数字段校验

与 `jav_filename_util` 内固定 grammar 对齐：`SerialId`、长度与有效位数规则。
供文件名解析、executor、decisions 与测试使用。
"""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# Pydantic model_validator 需要接受 Any 类型
# 这是框架接口边界：输入可能来自外部原始数据，无法提前类型化
# ruff: noqa: ANN401

# JAV 番号数字段：与 `jav_filename_util` 固定规则一致（文件名解析与领域对象同一语义）
SERIAL_DIGIT_CHARS_MIN = 3
SERIAL_DIGIT_CHARS_MAX = 5
SERIAL_EFFECTIVE_DIGITS_MIN = 1
SERIAL_EFFECTIVE_DIGITS_MAX = 4


def effective_serial_digit_len(raw: str) -> int | None:
    """文件名/番号中连续数字串的「有效位数」（与补零展示无关）。

    - 非全 ``0``：十进制数值的位数（如 ``00399`` -> 3）。
    - 全 ``0``：按占位长度计（如 ``000`` -> 3），避免 ``int`` 退化为单 0。
    """
    if not raw or not raw.isdigit():
        return None
    if set(raw) == {"0"}:
        return len(raw)
    return len(str(int(raw, 10)))


def serial_number_raw_is_valid(raw: str) -> bool:
    """原始数字串是否满足固定规则：仅数字、长度 3–5、有效位数 1–4。"""
    if not raw.isdigit():
        return False
    if not (SERIAL_DIGIT_CHARS_MIN <= len(raw) <= SERIAL_DIGIT_CHARS_MAX):
        return False
    eff = effective_serial_digit_len(raw)
    if eff is None:
        return False
    return SERIAL_EFFECTIVE_DIGITS_MIN <= eff <= SERIAL_EFFECTIVE_DIGITS_MAX


class SerialId(BaseModel):
    """番号值对象

    结构化表示番号，包含字母前缀和数字部分。
    支持从字符串解析（"ABC-123"、"ABC_123"、"ABC123"）和转换为字符串。
    这是文件 domain 的核心值对象，用于 JAV 视频文件的番号识别和整理。

    设计意图：
    - 封装番号的验证逻辑，确保番号格式的一致性
    - 提供统一的番号表示方式，便于文件名生成和目录组织
    - 原始 number 须为 3–5 位数字且有效位数 1–4（见 ``serial_number_raw_is_valid``），与文件名解析一致
    - 校验通过后自动规范化：先 zfill 至最少 3 位；若长度仍大于 3，则去掉前导 0 直至长度为 3
    """

    prefix: str = Field(..., description="字母前缀（2-6个大写字母）")
    number: str = Field(
        ...,
        description=(
            "数字部分（原始 3–5 位数字，有效位 1–4；"
            "规范化：先 zfill(3)，再对长度>3 去前导 0 直至 3 位）"
        ),
    )

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        """验证字母前缀"""
        v_upper = v.upper()
        if not v_upper.isalpha():
            raise ValueError("前缀必须只包含字母")
        if not (2 <= len(v_upper) <= 6):
            raise ValueError("前缀长度必须在2-6个字符之间")
        return v_upper

    @field_validator("number")
    @classmethod
    def validate_number(cls, v: str) -> str:
        """验证并规范化数字部分。

        先按固定规则校验原始串，再 zfill 至最少 3 位；若长度仍大于 3，则反复去掉最左侧的 0，
        直到长度为 3（保留 3 位时的前导 0，如 012）。
        例如：'123'→'123'，'0123'→'123'，'01234'→'1234'。
        """
        if not v.isdigit():
            raise ValueError("数字部分必须只包含数字")
        if not serial_number_raw_is_valid(v):
            raise ValueError(
                "数字部分须为3-5位且有效位数在1-4之间（与番号匹配规则一致）",
            )
        s = v.zfill(3)
        while len(s) > 3 and s.startswith("0"):
            s = s[1:]
        return s

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
        pattern = r"^([A-Za-z]{2,6})[-_]?(\d{3,5})$"
        match = re.match(pattern, value)
        if not match:
            raise ValueError(f"无效的番号格式: {value}")
        prefix = match.group(1).upper()
        number = match.group(2)
        return cls(prefix=prefix, number=number)

    @model_validator(mode="before")
    @classmethod
    # 保持 Any 是框架要求；这里仅做字符串到结构化数据的桥接
    def parse_string_input(cls, data: Any) -> Any:  # noqa: ANN401
        """支持从字符串自动解析（向后兼容）"""
        if isinstance(data, str):
            return cls.from_string(data).model_dump()
        return data

    def __str__(self) -> str:
        """转换为字符串格式：PREFIX-NUMBER"""
        return f"{self.prefix}-{self.number}"
