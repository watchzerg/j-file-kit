"""正则表达式模式匹配工具

提供番号提取相关的正则表达式功能，包括：
- 番号提取函数
- 正则表达式模式定义
- 匹配结果标准化处理

番号规则（基于正则表达式：`(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\\d{2,5})(?![0-9])`）：
- 字母部分：2-5个英文字母（大小写都可以）
- 分隔符：可选，支持 `-`、`_` 或无分隔符
- 数字部分：2-5个数字
- 边界条件：
  - 前面不能紧挨着字母（使用负向后查找 `(?<![a-zA-Z])`）
  - 后面不能紧挨着数字（使用负向前查找 `(?![0-9])`）
- 输出格式：统一标准化为 `字母-数字` 格式（大写字母）

示例：
- `ABC-123.mp4` → `ABC-123`
- `ABC_123.mp4` → `ABC-123`
- `ABC123.mp4` → `ABC-123`
- `video_ABC-001_hd.mp4` → `ABC-001`
- `XABC-123.mp4` → `XABC-123`（XABC-123是有效的4字母+3数字番号）
"""

from __future__ import annotations

import re
from typing import Literal


# 默认番号提取正则表达式模式
DEFAULT_SERIAL_PATTERN = r"(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\d{2,5})(?![0-9])"


def extract_serial_id(filename: str, pattern: str = DEFAULT_SERIAL_PATTERN) -> str | None:
    """从文件名提取番号
    
    番号规则：
    - 字母部分：2-5个英文字母（大小写都可以）
    - 分隔符：可选，支持 `-`、`_` 或无分隔符
    - 数字部分：2-5个数字
    - 边界条件：番号前面不能紧挨着字母，番号后面不能紧挨着数字
    
    Args:
        filename: 文件名
        pattern: 番号正则表达式（默认：`(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\\d{2,5})(?![0-9])`）
        
    Returns:
        提取到的番号（统一大写，标准化格式：字母-数字），如果没有找到则返回 None
        
    Examples:
        >>> extract_serial_id("ABCD-123.mp4")
        "ABCD-123"
        >>> extract_serial_id("video_ABC-001_hd.mp4")
        "ABC-001"
        >>> extract_serial_id("ABC123.mp4")
        "ABC-123"
        >>> extract_serial_id("ABC_123.mp4")
        "ABC-123"
        >>> extract_serial_id("no_serial.mp4")
        None
    """
    match = re.search(pattern, filename)
    if not match:
        return None
    
    # 获取匹配的字母和数字部分
    letters = match.group(1).upper()
    digits = match.group(2)
    
    # 标准化格式：字母-数字
    return f"{letters}-{digits}"




# 导出所有公共函数和常量
__all__ = [
    "DEFAULT_SERIAL_PATTERN",
    "extract_serial_id"
]
