"""文件扫描服务

提供文件目录扫描功能，支持多个根目录。
使用infrastructure层的文件系统操作进行实际扫描。
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from ..domain.models import DirectoryInfo, FileInfo
from ..infrastructure.filesystem.scanner import scan_directory_items


class FileScanner:
    """文件扫描器

    提供文件目录扫描功能，支持多个根目录。
    统一扫描接口，返回文件和目录的统一抽象，支持在遍历过程中处理两种类型。
    """

    def __init__(self, root_paths: list[Path]):
        """初始化扫描器

        Args:
            root_paths: 扫描根目录列表
        """
        self.root_paths = root_paths

    def scan_items(self) -> Generator[FileInfo | DirectoryInfo]:
        """扫描文件和目录

        统一扫描接口，返回文件和目录的统一抽象，支持在遍历过程中处理两种类型。
        设计意图：在文件处理流程中，需要同时处理文件和目录，此方法提供了统一的扫描接口。

        Yields:
            FileInfo | DirectoryInfo: 文件或目录信息
        """
        for root_path in self.root_paths:
            for path, is_file in scan_directory_items(root_path):
                if is_file:
                    yield FileInfo.from_path(path)
                else:
                    yield DirectoryInfo.from_path(path)
