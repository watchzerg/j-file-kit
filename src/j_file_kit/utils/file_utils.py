"""文件工具函数

提供文件操作相关的纯函数工具，如路径冲突处理、路径生成、文件类型判断等。
不包含I/O操作，所有文件系统操作应使用infrastructure/filesystem/operations。
"""

from __future__ import annotations

import random
import string
from pathlib import Path

from ..domain.models import FileType, SerialId
from ..infrastructure.filesystem.operations import path_exists


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
    if not path_exists(target_path):
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

        if not path_exists(new_path):
            return new_path

    # 如果100次尝试后仍有冲突，抛出异常
    raise RuntimeError(f"无法为 {target_path} 生成唯一路径，已尝试 {max_attempts} 次")


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
