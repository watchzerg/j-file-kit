"""文件扫描服务

提供文件目录扫描功能，支持多个根目录。
使用infrastructure层的文件系统操作进行实际扫描。
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from ..domain.models import FileInfo
from ..infrastructure.filesystem.scanner import scan_directory_files


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
            for file_path in scan_directory_files(root_path):
                file_info = FileInfo.from_path(file_path)
                yield file_info
