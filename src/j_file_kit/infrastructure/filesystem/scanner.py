"""文件扫描操作

封装文件系统扫描相关的操作。
提供底层文件扫描功能，由服务层的FileScanner使用。
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from .operations import is_directory, is_file, path_exists


def scan_directory_files(root: Path) -> Generator[Path]:
    """扫描目录下的所有文件

    Args:
        root: 根目录路径

    Yields:
        Path: 文件路径

    Raises:
        FileNotFoundError: 目录不存在
        NotADirectoryError: 路径不是目录
    """
    if not path_exists(root):
        raise FileNotFoundError(f"扫描目录不存在: {root}")

    if not is_directory(root):
        raise NotADirectoryError(f"路径不是目录: {root}")

    for file_path in root.rglob("*"):
        if is_file(file_path):
            yield file_path
