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


def validate_serial_pattern(pattern: str) -> bool:
    """验证番号正则表达式模式的有效性
    
    Args:
        pattern: 要验证的正则表达式模式
        
    Returns:
        模式是否有效
        
    Examples:
        >>> validate_serial_pattern(r"(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\\d{2,5})(?![0-9])")
        True
        >>> validate_serial_pattern("invalid[pattern")
        False
    """
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def get_pattern_info(pattern: str) -> dict[str, str | int | bool]:
    """获取正则表达式模式的详细信息
    
    Args:
        pattern: 正则表达式模式
        
    Returns:
        包含模式信息的字典
        
    Examples:
        >>> info = get_pattern_info(DEFAULT_SERIAL_PATTERN)
        >>> info['is_valid']
        True
        >>> info['groups_count']
        2
    """
    try:
        compiled_pattern = re.compile(pattern)
        return {
            'is_valid': True,
            'groups_count': compiled_pattern.groups,
            'pattern': pattern,
            'flags': compiled_pattern.flags
        }
    except re.error as e:
        return {
            'is_valid': False,
            'error': str(e),
            'pattern': pattern,
            'groups_count': 0,
            'flags': 0
        }


def find_all_serial_ids(filename: str, pattern: str = DEFAULT_SERIAL_PATTERN) -> list[str]:
    """从文件名中提取所有匹配的番号
    
    Args:
        filename: 文件名
        pattern: 番号正则表达式（默认：`(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\\d{2,5})(?![0-9])`）
        
    Returns:
        所有匹配的番号列表（统一大写，标准化格式：字母-数字）
        
    Examples:
        >>> find_all_serial_ids("ABC-123_DEF-456.mp4")
        ["ABC-123", "DEF-456"]
        >>> find_all_serial_ids("ABC-123.mp4")
        ["ABC-123"]
        >>> find_all_serial_ids("no_serial.mp4")
        []
    """
    matches = re.findall(pattern, filename)
    if not matches:
        return []
    
    # 处理所有匹配结果
    serial_ids = []
    for match in matches:
        if isinstance(match, tuple):
            # 如果有多个捕获组
            letters = match[0].upper()
            digits = match[1]
        else:
            # 如果只有一个捕获组
            letters = match.upper()
            digits = ""
        
        # 标准化格式：字母-数字
        serial_ids.append(f"{letters}-{digits}")
    
    return serial_ids


def is_valid_serial_format(serial_id: str) -> bool:
    """验证番号格式是否符合标准
    
    Args:
        serial_id: 要验证的番号
        
    Returns:
        番号格式是否有效
        
    Examples:
        >>> is_valid_serial_format("ABC-123")
        True
        >>> is_valid_serial_format("ABC123")
        False
        >>> is_valid_serial_format("AB-12")
        True
        >>> is_valid_serial_format("ABCDE-12345")
        True
    """
    # 标准格式：字母-数字
    pattern = r"^[A-Z]{2,5}-\d{2,5}$"
    return bool(re.match(pattern, serial_id))


def normalize_serial_id(serial_id: str) -> str | None:
    """标准化番号格式
    
    将各种格式的番号统一转换为标准格式：字母-数字（大写）
    
    Args:
        serial_id: 要标准化的番号
        
    Returns:
        标准化后的番号，如果格式无效则返回 None
        
    Examples:
        >>> normalize_serial_id("abc-123")
        "ABC-123"
        >>> normalize_serial_id("ABC_123")
        "ABC-123"
        >>> normalize_serial_id("ABC123")
        "ABC-123"
        >>> normalize_serial_id("invalid")
        None
    """
    # 尝试提取番号
    extracted = extract_serial_id(serial_id)
    if extracted:
        return extracted
    
    # 如果提取失败，尝试直接匹配和标准化
    # 匹配格式：字母-数字 或 字母_数字 或 字母数字
    pattern = r"^([a-zA-Z]{2,5})[-_]?(\d{2,5})$"
    match = re.match(pattern, serial_id)
    
    if match:
        letters = match.group(1).upper()
        digits = match.group(2)
        return f"{letters}-{digits}"
    
    return None


# 导出所有公共函数和常量
__all__ = [
    "DEFAULT_SERIAL_PATTERN",
    "extract_serial_id",
    "validate_serial_pattern", 
    "get_pattern_info",
    "find_all_serial_ids",
    "is_valid_serial_format",
    "normalize_serial_id"
]
