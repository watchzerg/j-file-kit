"""文件名生成模块

提供根据番号重构文件名的功能。

业务规则：
1. 文件名分解为4部分：番号之前的内容、番号、番号之后的内容、扩展名
2. 对第1、2、3部分分别执行trim操作：去除前后的空格、连字符(-)、下划线(_)、点号(.)
3. 根据第1部分trim后是否为空判断番号是否在开头
4. 按不同规则拼接新文件名

拼接规则：
- 番号在开头（第1部分trim后为空）：
  - 标准番号 + [空格 + 第3部分trim后的内容] + 扩展名
  - 如果第3部分trim后为空，则只输出：标准番号 + 扩展名
  
- 番号不在开头（第1部分trim后不为空）：
  - 标准番号 + 空格 + 第1部分 + 占位符 + 扩展名
  - 占位符：第3部分trim后为空 → "-serialId"，否则 → "-serialId-" + 第3部分

标准化番号格式：大写字母 + 连字符 + 数字（如 ABC-123）
"""

from __future__ import annotations

import re
from pathlib import Path

from .regex_patterns import extract_serial_id


def trim_separators(text: str) -> str:
    """去除字符串前后的分隔符
    
    去除前后的：空格、连字符(-)、下划线(_)
    注意：不处理点号(.)，因为点号可能是文件名内容的一部分
    
    Args:
        text: 要处理的字符串
        
    Returns:
        处理后的字符串
        
    Examples:
        >>> trim_separators("  _abc-123_  ")
        "abc-123"
        >>> trim_separators("...ABC-001...")
        "...ABC-001..."  # 点号不会被trim
        >>> trim_separators("")
        ""
    """
    return text.strip(" -_")


def generate_new_filename(
    original_path: Path, 
    pattern: str
) -> tuple[Path, str | None]:
    """根据番号生成新文件名
    
    内部调用 extract_serial_id 提取番号，然后将文件名分解为4部分，按业务规则重构文件名。
    
    Args:
        original_path: 原文件路径
        pattern: 番号正则表达式
        
    Returns:
        元组：(新文件路径, 提取到的番号)。如果没有找到番号，返回 (原路径, None)
        
    Examples:
        >>> new_path, serial_id = generate_new_filename(Path("video_ABC-001_hd.mp4"), pattern)
        >>> new_path
        Path("ABC-001 video-serialId-hd.mp4")
        >>> serial_id
        "ABC-001"
        
        >>> new_path, serial_id = generate_new_filename(Path("ABC-001_video.mp4"), pattern)
        >>> new_path
        Path("ABC-001 video.mp4")
        >>> serial_id
        "ABC-001"
        
        >>> new_path, serial_id = generate_new_filename(Path("no_serial.mp4"), pattern)
        >>> new_path
        Path("no_serial.mp4")
        >>> serial_id
        None
    """
    filename = original_path.name
    stem = original_path.stem
    suffix = original_path.suffix
    parent = original_path.parent
    
    # 提取番号
    serial_id = extract_serial_id(filename, pattern)
    if not serial_id:
        # 未匹配到番号，保持原文件名
        return original_path, None
    
    # 查找番号在文件名中的位置（用于分解文件名）
    match = re.search(pattern, filename, re.IGNORECASE)
    if not match:
        # 这种情况理论上不会发生，因为 extract_serial_id 已经验证过
        return original_path, None
    
    # 分解文件名为4部分
    start, end = match.span()
    part1 = filename[:start]  # 番号之前的内容
    part2 = filename[start:end]  # 番号
    part3 = filename[end:].replace(suffix, "")  # 番号之后的内容（不含扩展名）
    part4 = suffix  # 扩展名
    
    # 对第1、2、3部分执行trim操作
    trimmed_part1 = trim_separators(part1)
    trimmed_part2 = trim_separators(part2)
    trimmed_part3 = trim_separators(part3)
    
    # 判断番号是否在开头（第1部分trim后为空）
    if not trimmed_part1:
        # 番号在开头，按照规则重构文件名
        if not trimmed_part3:
            # 第3部分trim后为空，只输出：标准番号 + 扩展名
            new_filename = f"{serial_id}{part4}"
        else:
            # 第3部分trim后不为空，输出：标准番号 + 空格 + 第3部分 + 扩展名
            new_filename = f"{serial_id} {trimmed_part3}{part4}"
    else:
        # 番号不在开头
        if not trimmed_part3:
            # 第3部分trim后为空，占位符为 "-serialId"
            placeholder = "-serialId"
        else:
            # 第3部分trim后不为空，占位符为 "-serialId-" + 第3部分
            placeholder = f"-serialId-{trimmed_part3}"
        
        # 拼接：标准番号 + 空格 + 第1部分 + 占位符 + 扩展名
        new_filename = f"{serial_id} {trimmed_part1}{placeholder}{part4}"
    
    return parent / new_filename, serial_id
