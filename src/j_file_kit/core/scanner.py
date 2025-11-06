"""文件扫描器

提供文件目录扫描功能，支持各种过滤器。
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from pathlib import Path

from .models import FileInfo


class FileFilter:
    """文件过滤器基类"""

    def __init__(self, name: str):
        """初始化过滤器

        Args:
            name: 过滤器名称
        """
        self.name = name

    def matches(self, file_info: FileInfo) -> bool:
        """检查文件是否匹配过滤器

        Args:
            file_info: 文件信息

        Returns:
            是否匹配
        """
        return True


class ExtensionFilter(FileFilter):
    """扩展名过滤器"""

    def __init__(self, extensions: set[str], name: str = "extension"):
        """初始化扩展名过滤器

        Args:
            extensions: 允许的扩展名集合
            name: 过滤器名称
        """
        super().__init__(name)
        self.extensions = {ext.lower() for ext in extensions}

    def matches(self, file_info: FileInfo) -> bool:
        """检查文件扩展名是否匹配"""
        return file_info.suffix.lower() in self.extensions


class ExcludeExtensionFilter(FileFilter):
    """排除扩展名过滤器"""

    def __init__(self, extensions: set[str], name: str = "exclude_extension"):
        """初始化排除扩展名过滤器

        Args:
            extensions: 要排除的扩展名集合
            name: 过滤器名称
        """
        super().__init__(name)
        self.extensions = {ext.lower() for ext in extensions}

    def matches(self, file_info: FileInfo) -> bool:
        """检查文件扩展名是否不在排除列表中"""
        return file_info.suffix.lower() not in self.extensions


class NamePatternFilter(FileFilter):
    """文件名模式过滤器"""

    def __init__(self, pattern: str, name: str = "name_pattern"):
        """初始化文件名模式过滤器

        Args:
            pattern: 文件名正则表达式模式
            name: 过滤器名称
        """
        super().__init__(name)
        self.pattern = pattern

    def matches(self, file_info: FileInfo) -> bool:
        """检查文件名是否匹配模式"""
        import re

        return bool(re.search(self.pattern, file_info.name))


class CustomFilter(FileFilter):
    """自定义过滤器"""

    def __init__(self, filter_func: Callable[[FileInfo], bool], name: str = "custom"):
        """初始化自定义过滤器

        Args:
            filter_func: 过滤函数
            name: 过滤器名称
        """
        super().__init__(name)
        self.filter_func = filter_func

    def matches(self, file_info: FileInfo) -> bool:
        """使用自定义函数检查文件"""
        return self.filter_func(file_info)


class FileScanner:
    """文件扫描器

    提供文件目录扫描功能，支持多个根目录和多种过滤器。
    """

    def __init__(self, root_paths: list[Path] | Path):
        """初始化扫描器

        Args:
            root_paths: 扫描根目录列表或单个根目录（向后兼容）
        """
        if isinstance(root_paths, Path):
            # 向后兼容：单个路径
            self.root_paths = [root_paths]
        else:
            self.root_paths = root_paths
        self.filters: list[FileFilter] = []

    def add_filter(self, filter_obj: FileFilter) -> FileScanner:
        """添加过滤器

        Args:
            filter_obj: 过滤器对象

        Returns:
            扫描器实例（支持链式调用）
        """
        self.filters.append(filter_obj)
        return self

    def add_extension_filter(self, extensions: set[str]) -> FileScanner:
        """添加扩展名过滤器

        Args:
            extensions: 允许的扩展名集合

        Returns:
            扫描器实例
        """
        return self.add_filter(ExtensionFilter(extensions))

    def add_exclude_extension_filter(self, extensions: set[str]) -> FileScanner:
        """添加排除扩展名过滤器

        Args:
            extensions: 要排除的扩展名集合

        Returns:
            扫描器实例
        """
        return self.add_filter(ExcludeExtensionFilter(extensions))

    def add_name_pattern_filter(self, pattern: str) -> FileScanner:
        """添加文件名模式过滤器

        Args:
            pattern: 文件名正则表达式模式

        Returns:
            扫描器实例
        """
        return self.add_filter(NamePatternFilter(pattern))

    def add_custom_filter(
        self, filter_func: Callable[[FileInfo], bool], name: str = "custom"
    ) -> FileScanner:
        """添加自定义过滤器

        Args:
            filter_func: 过滤函数
            name: 过滤器名称

        Returns:
            扫描器实例
        """
        return self.add_filter(CustomFilter(filter_func, name))

    def _matches_all_filters(self, file_info: FileInfo) -> bool:
        """检查文件是否匹配所有过滤器

        Args:
            file_info: 文件信息

        Returns:
            是否匹配所有过滤器
        """
        return all(filter_obj.matches(file_info) for filter_obj in self.filters)

    def scan_files(self) -> Generator[FileInfo]:
        """扫描文件

        Yields:
            FileInfo: 匹配过滤器的文件信息
        """
        for root_path in self.root_paths:
            if not root_path.exists():
                raise FileNotFoundError(f"扫描目录不存在: {root_path}")

            if not root_path.is_dir():
                raise NotADirectoryError(f"路径不是目录: {root_path}")

            for file_path in root_path.rglob("*"):
                if file_path.is_file():
                    file_info = FileInfo.from_path(file_path)

                    if self._matches_all_filters(file_info):
                        yield file_info

    def scan_files_list(self) -> list[FileInfo]:
        """扫描文件并返回列表

        Returns:
            匹配过滤器的文件信息列表
        """
        return list(self.scan_files())

    def count_files(self) -> int:
        """统计匹配的文件数量

        Returns:
            匹配的文件数量
        """
        count = 0
        for _ in self.scan_files():
            count += 1
        return count

    def get_file_types(self) -> dict[str, int]:
        """统计文件类型分布

        Returns:
            文件类型统计字典
        """
        type_counts = {}

        for file_info in self.scan_files():
            suffix = file_info.suffix.lower()
            type_counts[suffix] = type_counts.get(suffix, 0) + 1

        return type_counts

    def clear_filters(self) -> FileScanner:
        """清空所有过滤器

        Returns:
            扫描器实例
        """
        self.filters.clear()
        return self

    def get_filter_info(self) -> list[dict[str, str]]:
        """获取过滤器信息

        Returns:
            过滤器信息列表
        """
        return [
            {"name": filter_obj.name, "type": filter_obj.__class__.__name__}
            for filter_obj in self.filters
        ]
