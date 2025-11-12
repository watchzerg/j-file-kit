"""文件扫描器

提供文件目录扫描功能。
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from .models import FileInfo


class FileScanner:
    """文件扫描器

    提供文件目录扫描功能，支持多个根目录。
    """

    def __init__(self, root_paths: list[Path]):
        """初始化扫描器

        Args:
            root_paths: 扫描根目录列表
        """
        self.root_paths = root_paths

    def scan_files(self) -> Generator[FileInfo]:
        """扫描文件

        Yields:
            FileInfo: 文件信息
        """
        for root_path in self.root_paths:
            if not root_path.exists():
                raise FileNotFoundError(f"扫描目录不存在: {root_path}")

            if not root_path.is_dir():
                raise NotADirectoryError(f"路径不是目录: {root_path}")

            for file_path in root_path.rglob("*"):
                if file_path.is_file():
                    file_info = FileInfo.from_path(file_path)
                    yield file_info
