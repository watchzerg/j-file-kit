"""Misc文件分析器

包含Misc文件相关的分析器，如文件大小分析和删除判断。
"""

from typing import Any

from ....interfaces.processors import Analyzer
from ....models import (
    FileType,
    PathEntryAction,
    PathEntryContext,
    PathEntryType,
    ProcessorResult,
)


class MiscFileSizeAnalyzer(Analyzer):
    """Misc文件大小分析器

    只分析Misc文件的大小，写入ctx.file_size。
    """

    def __init__(self) -> None:
        """初始化Misc文件大小分析器"""
        super().__init__("MiscFileSizeAnalyzer")

    def process(self, ctx: PathEntryContext) -> ProcessorResult:  # type: ignore[override]
        """分析文件大小

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        # 类型检查：只处理文件类型的项
        if ctx.item_type != PathEntryType.FILE:
            return ProcessorResult.skip("不是文件，跳过大小分析")

        # 只处理Misc文件
        if ctx.file_type != FileType.MISC:
            return ProcessorResult.skip("非Misc文件，跳过大小分析")

        try:
            file_size = ctx.item_info.path.stat().st_size
            ctx.file_size = file_size

            return ProcessorResult.success(
                f"文件大小: {file_size} 字节", {"file_size": file_size}
            )

        except Exception as e:
            return ProcessorResult.skip(f"无法获取文件大小: {str(e)}")


class MiscFileDeleteAnalyzer(Analyzer):
    """Misc文件删除判断器

    根据配置规则判断Misc文件是否应该删除。
    删除条件：扩展名 or (体积 <= max_size and 文件名包含关键字)
    """

    def __init__(
        self,
        misc_file_delete_rules: dict[str, Any],
    ):
        """初始化Misc文件删除判断器

        Args:
            misc_file_delete_rules: 删除规则配置（keywords, extensions, max_size）
        """
        super().__init__("MiscFileDeleteAnalyzer")
        self.misc_file_delete_rules = misc_file_delete_rules

    def process(self, ctx: PathEntryContext) -> ProcessorResult:  # type: ignore[override]
        """判断Misc文件是否应该删除

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        # 类型检查：只处理文件类型的项
        if ctx.item_type != PathEntryType.FILE:
            return ProcessorResult.skip("不是文件，跳过删除判断")

        # 只处理Misc文件
        if ctx.file_type != FileType.MISC:
            return ProcessorResult.skip("非Misc文件，跳过删除判断")

        try:
            if self._should_delete(ctx):
                ctx.action = PathEntryAction.DELETE
                return ProcessorResult.success("Misc文件符合删除条件")
            else:
                return ProcessorResult.success(
                    "Misc文件不符合删除条件，将移动到misc目录"
                )

        except Exception as e:
            return ProcessorResult.error(f"Misc文件删除判断失败: {str(e)}")

    def _should_delete(self, ctx: PathEntryContext) -> bool:
        """判断Misc文件是否应该删除

        删除条件：扩展名 or (体积 <= max_size and 文件名包含关键字)

        Args:
            ctx: 处理上下文

        Returns:
            是否应该删除
        """
        # 检查扩展名（优先级最高，单独判断）
        if self.misc_file_delete_rules.get("extensions"):
            extensions = self.misc_file_delete_rules["extensions"]
            if isinstance(extensions, list):
                # 确保扩展名以点号开头
                extensions_normalized = {
                    ext if ext.startswith(".") else f".{ext}" for ext in extensions
                }
                if (
                    ctx.item_info.suffix
                    and ctx.item_info.suffix.lower() in extensions_normalized
                ):
                    return True

        # 检查体积和文件名的组合条件
        # 需要同时满足：体积 <= max_size 且 文件名包含关键字
        max_size = self.misc_file_delete_rules.get("max_size")
        keywords = self.misc_file_delete_rules.get("keywords")

        # 如果两者都配置了，需要同时满足
        if max_size is not None and keywords and isinstance(keywords, list):
            # 检查文件大小
            if ctx.file_size is None:
                # 防御性跳过：如果没有文件大小信息，不删除
                return False

            if not isinstance(max_size, (int, float)) or ctx.file_size > max_size:
                # 文件大小超过阈值，不删除
                return False

            # 检查文件名关键字
            if not any(kw in ctx.item_info.stem for kw in keywords):
                # 文件名不包含关键字，不删除
                return False

            # 两者都满足，删除
            return True

        # 如果只配置了其中一个或都没配置，不删除
        return False
