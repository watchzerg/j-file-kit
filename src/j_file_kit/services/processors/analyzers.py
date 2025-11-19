"""分析器实现

实现文件分析功能，如文件类型分类、番号提取、动作决策等。
分析器只负责分析，不执行文件操作。

这些处理器位于服务层，可以依赖infrastructure层。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...interfaces.processors import Analyzer
from ...models import (
    FileType,
    PathEntryAction,
    PathEntryContext,
    PathEntryType,
    ProcessorResult,
)
from ...utils.file_utils import generate_sorted_dir, get_file_type
from ...utils.filename_generation import generate_new_filename


class FileClassifier(Analyzer):
    """文件类型分类器

    根据文件扩展名判断文件类型（视频/图片/压缩/Misc）。
    """

    def __init__(
        self,
        video_extensions: set[str],
        image_extensions: set[str],
        archive_extensions: set[str],
    ):
        """初始化文件分类器

        Args:
            video_extensions: 视频文件扩展名集合
            image_extensions: 图片文件扩展名集合
            archive_extensions: 压缩文件扩展名集合
        """
        super().__init__("FileClassifier")
        self.video_extensions = video_extensions
        self.image_extensions = image_extensions
        self.archive_extensions = archive_extensions

    def process(self, ctx: PathEntryContext) -> ProcessorResult:  # type: ignore[override]
        """分析文件类型

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        # 类型检查：只处理文件类型的项
        if ctx.item_type != PathEntryType.FILE:
            return ProcessorResult.skip("不是文件，跳过文件类型分析")

        try:
            # 获取文件类型
            file_type = get_file_type(
                ctx.item_info.path,
                self.video_extensions,
                self.image_extensions,
                self.archive_extensions,
            )

            # 更新上下文
            ctx.file_type = file_type

            return ProcessorResult.success(f"文件类型: {file_type.value}，继续处理")

        except Exception as e:
            return ProcessorResult.error(f"文件类型分析失败: {str(e)}")


class FileSerialIdExtractor(Analyzer):
    """番号提取器

    从文件名中提取番号，并生成重构后的文件名。
    只负责提取番号和生成文件名，不设置完整路径。
    """

    def __init__(self) -> None:
        """初始化番号提取器"""
        super().__init__("FileSerialIdExtractor")

    def process(self, ctx: PathEntryContext) -> ProcessorResult:  # type: ignore[override]
        """提取番号并生成重构后的文件名

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        # 类型检查：只处理文件类型的项
        if ctx.item_type != PathEntryType.FILE:
            return ProcessorResult.skip("不是文件，跳过番号提取")

        try:
            # 只处理视频和图片文件
            if ctx.file_type not in [FileType.VIDEO, FileType.IMAGE]:
                return ProcessorResult.skip("非视频/图片文件，跳过番号提取")

            # 生成新文件名并提取番号
            new_path, serial_id = generate_new_filename(ctx.item_info.path)

            if serial_id:
                # 检查新路径是否与原路径相同
                if new_path == ctx.item_info.path:
                    # 即使路径相同，也要设置番号信息
                    ctx.serial_id = serial_id
                    ctx.renamed_filename = new_path.name
                    return ProcessorResult.skip("文件名已经是标准格式，无需重命名")

                # 更新上下文：设置番号和重构后的文件名
                ctx.serial_id = serial_id
                ctx.renamed_filename = new_path.name

                return ProcessorResult.success(
                    f"提取到番号: {serial_id}",
                    {
                        "serial_id": str(serial_id),
                        "renamed_filename": ctx.renamed_filename,
                    },
                )
            else:
                # 没有番号
                return ProcessorResult.success("未找到番号，将移动到待处理目录")

        except Exception as e:
            return ProcessorResult.error(f"番号提取失败: {str(e)}")


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


class FileNameAnalyzer(Analyzer):
    """文件名分析器

    分析文件名特征，如长度、特殊字符等。
    """

    def __init__(self, max_length: int = 255):
        """初始化文件名分析器

        Args:
            max_length: 最大文件名长度
        """
        super().__init__("FileNameAnalyzer")
        self.max_length = max_length

    def process(self, ctx: PathEntryContext) -> ProcessorResult:  # type: ignore[override]
        """分析文件名

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        # 类型检查：只处理文件类型的项
        if ctx.item_type != PathEntryType.FILE:
            return ProcessorResult.skip("不是文件，跳过文件名分析")

        try:
            filename = ctx.item_info.stem
            filename_length = len(filename)

            # 检查文件名长度
            if filename_length > self.max_length:
                return ProcessorResult.warning(f"文件名过长: {filename_length} 字符")

            # 检查特殊字符
            special_chars = set('<>:"/\\|?*')
            found_chars = special_chars.intersection(filename)

            if found_chars:
                return ProcessorResult.warning(f"文件名包含特殊字符: {found_chars}")

            # 将分析结果存储到自定义数据中
            ctx.custom_data["filename_length"] = filename_length
            ctx.custom_data["special_chars"] = list(found_chars)

            return ProcessorResult.success(f"文件名分析完成: {filename_length} 字符")

        except Exception as e:
            return ProcessorResult.error(f"文件名分析失败: {str(e)}")


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


class FileActionDecider(Analyzer):
    """动作决策器

    根据文件类型、番号等信息，决定应该执行什么动作。
    """

    def __init__(
        self,
        sorted_dir: Path | None,
        unsorted_dir: Path | None,
        archive_dir: Path | None,
        misc_dir: Path | None,
    ):
        """初始化动作决策器

        Args:
            sorted_dir: 整理后的视频图片存储目录（B类）
            unsorted_dir: 无番号视频图片存储目录（C类）
            archive_dir: 压缩文件存储目录
            misc_dir: Misc文件存储目录（D类）
        """
        super().__init__("FileActionDecider")
        self.sorted_dir = sorted_dir
        self.unsorted_dir = unsorted_dir
        self.archive_dir = archive_dir
        self.misc_dir = misc_dir

    def _process_video_image(self, ctx: PathEntryContext) -> ProcessorResult | None:
        """处理视频/图片文件

        Args:
            ctx: 处理上下文

        Returns:
            处理结果，如果无法处理则返回None
        """
        if ctx.serial_id:
            # 有番号：移动到整理目录
            if self.sorted_dir is None:
                return ProcessorResult.error("sorted_dir 未设置，无法移动有番号文件")

            if not ctx.renamed_filename:
                return ProcessorResult.error(
                    "番号存在但重构后的文件名未设置，请确保 FileSerialIdExtractor 已执行"
                )

            ctx.action = PathEntryAction.MOVE_TO_SORTED
            target_dir = generate_sorted_dir(self.sorted_dir, ctx.serial_id)
            ctx.target_path = target_dir / ctx.renamed_filename
        else:
            # 无番号：移动到C目录
            if self.unsorted_dir is None:
                return ProcessorResult.error("unsorted_dir 未设置，无法移动无番号文件")

            ctx.action = PathEntryAction.MOVE_TO_UNSORTED
            ctx.target_path = self.unsorted_dir / ctx.item_info.path.name
        return None

    def _process_archive(self, ctx: PathEntryContext) -> ProcessorResult | None:
        """处理压缩文件

        Args:
            ctx: 处理上下文

        Returns:
            处理结果，如果无法处理则返回None
        """
        if self.archive_dir is None:
            return ProcessorResult.error("archive_dir 未设置，无法移动压缩文件")

        ctx.action = PathEntryAction.MOVE_TO_ARCHIVE
        ctx.target_path = self.archive_dir / ctx.item_info.path.name
        return None

    def _process_misc(self, ctx: PathEntryContext) -> ProcessorResult | None:
        """处理Misc文件

        Args:
            ctx: 处理上下文

        Returns:
            处理结果，如果无法处理则返回None
        """
        # 如果 action 已经设置（例如由 MiscFileDeleteAnalyzer 设置的 DELETE），直接返回
        if ctx.action is not None:
            return None

        if self.misc_dir is None:
            return ProcessorResult.error("misc_dir 未设置，无法移动Misc文件")

        ctx.action = PathEntryAction.MOVE_TO_MISC
        ctx.target_path = self.misc_dir / ctx.item_info.path.name
        return None

    def _process_by_file_type(self, ctx: PathEntryContext) -> ProcessorResult | None:
        """根据文件类型处理

        Args:
            ctx: 处理上下文

        Returns:
            处理结果，如果无法处理则返回None
        """
        if ctx.file_type in [FileType.VIDEO, FileType.IMAGE]:
            return self._process_video_image(ctx)
        if ctx.file_type == FileType.ARCHIVE:
            return self._process_archive(ctx)
        if ctx.file_type == FileType.MISC:
            return self._process_misc(ctx)
        ctx.action = PathEntryAction.SKIP
        return None

    def process(self, ctx: PathEntryContext) -> ProcessorResult:  # type: ignore[override]
        """决策动作类型并组装完整路径

        根据文件类型、番号等信息，决定应该执行什么动作，并组装完整的目标路径。

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        # 类型检查：只处理文件类型的项
        if ctx.item_type != PathEntryType.FILE:
            return ProcessorResult.skip("不是文件，跳过动作决策")

        # 如果 action 已经被设置（例如由 MiscFileDeleteAnalyzer 设置），直接跳过
        if ctx.action is not None:
            return ProcessorResult.skip("动作已设置，跳过决策")

        try:
            result = self._process_by_file_type(ctx)
            if result:
                return result

            # 确保action已设置
            if ctx.action is None:
                return ProcessorResult.error("未能决策动作类型")

            return ProcessorResult.success(
                f"决策动作: {ctx.action.value}",
                {
                    "action": ctx.action.value,
                    "target_path": str(ctx.target_path) if ctx.target_path else None,
                },
            )

        except Exception as e:
            return ProcessorResult.error(f"动作决策失败: {str(e)}")
