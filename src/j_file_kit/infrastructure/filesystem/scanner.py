"""文件扫描操作

封装文件系统扫描相关的操作。
提供底层文件扫描功能，由服务层的FileScanner使用。
"""

import os
from collections.abc import Generator
from pathlib import Path

from j_file_kit.shared.models.path_entry import PathEntryType

from .operations import is_directory, path_exists


def scan_directory_items(root: Path) -> Generator[tuple[Path, PathEntryType]]:
    """扫描目录下的所有文件和目录（自底向上遍历）

    自底向上遍历确保子目录先于父目录被处理，这样当子目录被删除后，
    父目录可能变为空目录，可以在后续遍历中被清理。
    先返回文件再返回目录，确保同一目录下的文件先处理，文件移动后目录可能变空。

    Args:
        root: 根目录路径

    Yields:
        tuple[Path, PathEntryType]: (路径, 路径项类型) 元组，返回 PathEntryType.FILE 或 PathEntryType.DIRECTORY

    Raises:
        FileNotFoundError: 目录不存在
        NotADirectoryError: 路径不是目录

    Note:
        使用os.walk的topdown=False实现自底向上遍历，确保深度最深的目录先处理。
    """
    if not path_exists(root):
        raise FileNotFoundError(f"扫描目录不存在: {root}")

    if not is_directory(root):
        raise NotADirectoryError(f"路径不是目录: {root}")

    # 使用os.walk实现自底向上遍历（topdown=False）
    # 这样确保子目录先于父目录被处理
    for dirpath, _dirnames, filenames in os.walk(root, topdown=False):
        dir_path = Path(dirpath)

        # 先yield所有文件（确保同一目录下的文件先于目录被处理）
        for filename in filenames:
            file_path = dir_path / filename
            yield (file_path, PathEntryType.FILE)

        # 再yield当前目录（包括根目录，由业务层决定是否处理）
        yield (dir_path, PathEntryType.DIRECTORY)
