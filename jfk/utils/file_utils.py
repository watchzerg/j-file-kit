"""文件工具函数

提供文件操作相关的工具函数，如番号提取、路径冲突处理等。
"""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Literal

from ..core.models import FileType


def extract_serial_id(filename: str, pattern: str = r"[A-Za-z]{2,5}-\d+") -> str | None:
    """从文件名提取番号
    
    Args:
        filename: 文件名
        pattern: 番号正则表达式
        
    Returns:
        提取到的番号（统一大写），如果没有找到则返回 None
        
    Examples:
        >>> extract_serial_id("ABCD-123.mp4")
        "ABCD-123"
        >>> extract_serial_id("video_ABC-001_hd.mp4")
        "ABC-001"
        >>> extract_serial_id("no_serial.mp4")
        None
    """
    match = re.search(pattern, filename)
    return match.group(1).upper() if match else None


def is_video_or_image(
    path: Path, 
    video_exts: set[str], 
    image_exts: set[str]
) -> Literal["video", "image", "other"]:
    """判断文件类型
    
    Args:
        path: 文件路径
        video_exts: 视频文件扩展名集合
        image_exts: 图片文件扩展名集合
        
    Returns:
        文件类型：video、image 或 other
    """
    suffix = path.suffix.lower()
    
    if suffix in video_exts:
        return "video"
    elif suffix in image_exts:
        return "image"
    else:
        return "other"


def resolve_unique_path(target_path: Path) -> Path:
    """处理路径冲突，生成唯一路径
    
    如果目标路径已存在，自动追加 `-Dup1234` 后缀（4位随机数），
    重试直到找到不冲突的路径。
    
    Args:
        target_path: 目标路径
        
    Returns:
        唯一路径
        
    Examples:
        >>> resolve_unique_path(Path("test.mp4"))
        Path("test.mp4")  # 如果文件不存在
        
        >>> resolve_unique_path(Path("test.mp4"))
        Path("test-Dup1234.mp4")  # 如果 test.mp4 已存在
    """
    if not target_path.exists():
        return target_path
    
    # 分离文件名和扩展名
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    
    # 生成唯一路径
    max_attempts = 100  # 防止无限循环
    for _ in range(max_attempts):
        # 生成4位随机数
        random_suffix = f"-Dup{random.randint(1000, 9999)}"
        new_name = f"{stem}{random_suffix}{suffix}"
        new_path = parent / new_name
        
        if not new_path.exists():
            return new_path
    
    # 如果100次尝试后仍有冲突，抛出异常
    raise RuntimeError(f"无法为 {target_path} 生成唯一路径，已尝试 {max_attempts} 次")


def generate_new_filename(
    original_path: Path, 
    serial_id: str, 
    pattern: str = r"[A-Za-z]{2,5}-\d+"
) -> Path:
    """根据番号生成新文件名
    
    将番号提取到文件名开头，原位置替换为 `-serialId-`。
    如果番号已在开头，则返回原路径。
    
    Args:
        original_path: 原文件路径
        serial_id: 番号
        pattern: 番号正则表达式
        
    Returns:
        新文件路径
        
    Examples:
        >>> generate_new_filename(Path("video_ABC-001_hd.mp4"), "ABC-001")
        Path("ABC-001-serialId-hd.mp4")
        
        >>> generate_new_filename(Path("ABC-001_video.mp4"), "ABC-001")
        Path("ABC-001_video.mp4")  # 已在开头，不修改
    """
    filename = original_path.name
    stem = original_path.stem
    suffix = original_path.suffix
    parent = original_path.parent
    
    # 检查番号是否已在开头
    if filename.upper().startswith(serial_id.upper()):
        return original_path
    
    # 查找番号在文件名中的位置
    match = re.search(pattern, filename, re.IGNORECASE)
    if not match:
        return original_path
    
    # 替换番号位置为 -serialId-
    start, end = match.span()
    new_stem = filename[:start] + "-serialId-" + filename[end:]
    new_stem = new_stem.replace(suffix, "")  # 移除扩展名
    
    # 将番号添加到开头
    new_filename = f"{serial_id}_{new_stem}{suffix}"
    return parent / new_filename


def find_empty_dirs(root: Path) -> list[Path]:
    """递归查找空目录
    
    自底向上查找所有空目录，返回需要删除的目录列表。
    
    Args:
        root: 根目录
        
    Returns:
        空目录列表（自底向上排序）
    """
    empty_dirs = []
    
    def _find_empty_dirs(path: Path) -> bool:
        """递归查找空目录
        
        Returns:
            目录是否为空
        """
        if not path.is_dir():
            return False
        
        # 检查目录是否为空
        try:
            items = list(path.iterdir())
            if not items:
                empty_dirs.append(path)
                return True
        except (PermissionError, OSError):
            return False
        
        # 递归检查子目录
        all_empty = True
        for item in items:
            if item.is_dir():
                if not _find_empty_dirs(item):
                    all_empty = False
        
        # 如果所有子目录都为空，则当前目录也为空
        if all_empty:
            empty_dirs.append(path)
            return True
        
        return False
    
    _find_empty_dirs(root)
    return empty_dirs


def safe_remove_empty_dirs(dirs: list[Path]) -> list[Path]:
    """安全删除空目录
    
    Args:
        dirs: 要删除的目录列表（自底向上排序）
        
    Returns:
        成功删除的目录列表
    """
    removed_dirs = []
    
    for dir_path in dirs:
        try:
            if dir_path.exists() and dir_path.is_dir():
                # 再次检查是否为空（防止并发删除）
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    removed_dirs.append(dir_path)
        except (PermissionError, OSError) as e:
            # 记录错误但继续处理其他目录
            print(f"无法删除目录 {dir_path}: {e}")
    
    return removed_dirs


def get_file_type_from_path(path: Path, video_exts: set[str], image_exts: set[str]) -> FileType:
    """从路径获取文件类型枚举
    
    Args:
        path: 文件路径
        video_exts: 视频文件扩展名集合
        image_exts: 图片文件扩展名集合
        
    Returns:
        文件类型枚举
    """
    file_type = is_video_or_image(path, video_exts, image_exts)
    
    if file_type == "video":
        return FileType.VIDEO
    elif file_type == "image":
        return FileType.IMAGE
    else:
        return FileType.OTHER
