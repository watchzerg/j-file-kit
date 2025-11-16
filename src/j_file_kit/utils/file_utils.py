"""文件工具函数

提供文件操作相关的纯函数工具，如路径冲突处理、路径生成、文件类型判断等。
不包含I/O操作，所有文件系统操作应使用infrastructure/filesystem/operations。
"""

from __future__ import annotations

import random
import re
import string
from pathlib import Path

from ..domain.models import FileType, SerialId


def get_file_type(
    path: Path, video_exts: set[str], image_exts: set[str], archive_exts: set[str]
) -> FileType:
    """判断文件类型并返回枚举

    Args:
        path: 文件路径
        video_exts: 视频文件扩展名集合
        image_exts: 图片文件扩展名集合
        archive_exts: 压缩文件扩展名集合

    Returns:
        文件类型枚举
    """
    suffix = path.suffix.lower()

    if suffix in video_exts:
        return FileType.VIDEO
    elif suffix in image_exts:
        return FileType.IMAGE
    elif suffix in archive_exts:
        return FileType.ARCHIVE
    else:
        return FileType.MISC


def generate_alternative_path(target_path: Path) -> Path:
    """生成候选路径，用于处理文件移动时的路径冲突

    如果输入路径已带 `-jfk-xxxx` 后缀，会提取原始路径并基于原始路径生成新候选路径。
    始终基于原始路径生成，避免路径越来越长。
    这是纯函数，不执行任何 I/O 操作。

    Args:
        target_path: 目标路径（可能已带 `-jfk-xxxx` 后缀）

    Returns:
        新的候选路径，格式为 `{原始stem}-jfk-{4个随机字符}{suffix}`

    Examples:
        >>> generate_alternative_path(Path("test.mp4"))
        Path("test-jfk-a3b2.mp4")

        >>> generate_alternative_path(Path("test-jfk-a3b2.mp4"))
        Path("test-jfk-xyz1.mp4")  # 基于原始路径 test.mp4 生成
    """
    # 提取 stem 和 suffix
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent

    # 尝试提取原始路径（如果已带 -jfk-xxxx 后缀）
    pattern = r"^(.+)-jfk-[a-z0-9]{4}$"
    match = re.match(pattern, stem)
    if match:
        original_stem = match.group(1)
    else:
        original_stem = stem

    # 生成新的候选路径
    chars = string.ascii_lowercase + string.digits
    random_suffix = "-jfk-" + "".join(random.choices(chars, k=4))  # noqa: S311
    new_name = f"{original_stem}{random_suffix}{suffix}"
    return parent / new_name


def generate_organized_dir(organized_dir: Path, serial_id: SerialId) -> Path:
    """生成整理目录路径：A/AB/ABCD/

    根据番号生成整理目录路径，格式为：organized_dir/首字母/前两字母/完整前缀/

    Args:
        organized_dir: 整理目录根路径
        serial_id: 番号对象

    Returns:
        目录路径（不含文件名）

    Examples:
        >>> from j_file_kit.domain.models import SerialId
        >>> generate_organized_dir(Path("/organized"), SerialId(prefix="ABCD", number="123"))
        Path("/organized/A/AB/ABCD")

        >>> generate_organized_dir(Path("/organized"), SerialId(prefix="XYZ", number="456"))
        Path("/organized/X/XY/XYZ")

        >>> generate_organized_dir(Path("/organized"), SerialId(prefix="AB", number="789"))
        Path("/organized/A/AB/AB")
    """
    prefix = serial_id.prefix
    first_letter = prefix[0]
    first_two = prefix[:2] if len(prefix) >= 2 else prefix

    return organized_dir / first_letter / first_two / prefix
