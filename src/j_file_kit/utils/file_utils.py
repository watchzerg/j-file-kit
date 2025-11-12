"""文件工具函数

提供文件操作相关的工具函数，如路径冲突处理等。
"""

from __future__ import annotations

import random
import string
from pathlib import Path

from ..core.models import FileType, SerialId


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
        return FileType.OTHER


def resolve_unique_path(target_path: Path) -> Path:
    """处理路径冲突，生成唯一路径

    如果目标路径已存在，自动追加 `-a3b2` 后缀（连字符加4个小写字母或数字），
    重试直到找到不冲突的路径。

    Args:
        target_path: 目标路径

    Returns:
        唯一路径

    Examples:
        >>> resolve_unique_path(Path("test.mp4"))
        Path("test.mp4")  # 如果文件不存在

        >>> resolve_unique_path(Path("test.mp4"))
        Path("test-a3b2.mp4")  # 如果 test.mp4 已存在
    """
    if not target_path.exists():
        return target_path

    # 分离文件名和扩展名
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent

    # 生成唯一路径
    max_attempts = 100  # 防止无限循环
    chars = string.ascii_lowercase + string.digits
    for _ in range(max_attempts):
        # 生成4个小写字母或数字（非密码学场景，使用标准随机数生成器即可）
        random_suffix = "-" + "".join(random.choices(chars, k=4))  # noqa: S311
        new_name = f"{stem}{random_suffix}{suffix}"
        new_path = parent / new_name

        if not new_path.exists():
            return new_path

    # 如果100次尝试后仍有冲突，抛出异常
    raise RuntimeError(f"无法为 {target_path} 生成唯一路径，已尝试 {max_attempts} 次")


def generate_organized_path(
    organized_dir: Path, serial_id: SerialId, suffix: str
) -> Path:
    """生成整理目录路径：A/ABCD/ABCD-123.ext

    根据番号生成整理目录的完整路径，格式为：organized_dir/首字母/完整前缀/番号.扩展名

    Args:
        organized_dir: 整理目录根路径
        serial_id: 番号对象
        suffix: 文件扩展名（含点号）

    Returns:
        完整的目标路径

    Examples:
        >>> from j_file_kit.core.models import SerialId
        >>> generate_organized_path(Path("/organized"), SerialId(prefix="ABCD", number="123"), ".mp4")
        Path("/organized/A/ABCD/ABCD-123.mp4")

        >>> generate_organized_path(Path("/organized"), SerialId(prefix="XYZ", number="456"), ".jpg")
        Path("/organized/X/XYZ/XYZ-456.jpg")
    """
    # 提取前缀首字母（A）和完整前缀（ABCD）
    prefix = serial_id.prefix
    first_letter = prefix[0]
    full_prefix = prefix

    # 构建路径：organized_dir/A/ABCD/ABCD-123.ext
    target_dir = organized_dir / first_letter / full_prefix
    filename = f"{serial_id}{suffix}"
    return target_dir / filename
