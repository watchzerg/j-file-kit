"""文件工具函数

提供文件操作相关的纯函数工具，如路径冲突处理等。
不包含I/O操作，所有文件系统操作应使用infrastructure/filesystem/operations。
不包含业务逻辑，所有函数都是通用的文件工具函数。
"""

import random
import re
import string
from pathlib import Path


def generate_alternative_filename(target_path: Path) -> Path:
    """生成候选文件名路径，用于处理文件移动时的路径冲突

    如果输入路径已带 `-jfk-xxxx` 后缀，会提取原始文件名并基于原始文件名生成新候选文件名。
    始终基于原始文件名生成，避免文件名越来越长。
    目录部分保持不变，仅修改文件名部分。
    这是纯函数，不执行任何 I/O 操作。

    Args:
        target_path: 目标路径（可能已带 `-jfk-xxxx` 后缀）

    Returns:
        新的候选路径，格式为 `{原始stem}-jfk-{4个随机字符}{suffix}`（目录保持不变）

    Examples:
        >>> generate_alternative_filename(Path("test.mp4"))
        Path("test-jfk-a3b2.mp4")

        >>> generate_alternative_filename(Path("test-jfk-a3b2.mp4"))
        Path("test-jfk-xyz1.mp4")  # 基于原始文件名 test.mp4 生成

        >>> generate_alternative_filename(Path(".hidden"))
        Path(".hidden-jfk-a3b2")  # 空 stem 时使用完整文件名
    """
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent

    # 处理空 stem 的情况（如 .hidden 文件或只有扩展名的文件）
    # 如果 stem 为空，使用完整文件名作为基础进行匹配
    base_name = stem if stem else target_path.name

    # 尝试提取原始路径（如果已带 -jfk-xxxx 后缀）
    pattern = r"^(.+)-jfk-[a-z0-9]{4}$"
    match = re.match(pattern, base_name)
    if match:
        original_stem = match.group(1)
    else:
        original_stem = base_name

    # 生成新的候选路径
    chars = string.ascii_lowercase + string.digits
    random_suffix = "-jfk-" + "".join(random.choices(chars, k=4))  # noqa: S311
    new_name = f"{original_stem}{random_suffix}{suffix}"
    return parent / new_name
