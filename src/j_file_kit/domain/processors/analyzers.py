"""分析器实现

实现文件分析功能，如文件类型分类、番号提取、动作决策等。
分析器只负责分析，不执行文件操作。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...utils.file_utils import generate_organized_path, get_file_type
from ...utils.filename_generation import generate_new_filename
from ..models import FileAction, FileType, ProcessingContext, ProcessorResult
from ..processor import Analyzer


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

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """分析文件类型

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        try:
            # 获取文件类型
            file_type = get_file_type(
                ctx.file_info.path,
                self.video_extensions,
                self.image_extensions,
                self.archive_extensions,
            )

            # 更新上下文
            ctx.file_type = file_type

            return ProcessorResult.success(f"文件类型: {file_type.value}，继续处理")

        except Exception as e:
            return ProcessorResult.error(f"文件类型分析失败: {str(e)}")


class SerialIdExtractor(Analyzer):
    """番号提取器

    从文件名中提取番号，并生成新的文件名。
    """

    def __init__(self) -> None:
        """初始化番号提取器"""
        super().__init__("SerialIdExtractor")

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """提取番号

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        try:
            # 只处理视频和图片文件
            if ctx.file_type not in [FileType.VIDEO, FileType.IMAGE]:
                return ProcessorResult.skip("非视频/图片文件，跳过番号提取")

            # 生成新文件名并提取番号
            new_path, serial_id = generate_new_filename(ctx.file_info.path)

            if serial_id:
                # 检查新路径是否与原路径相同
                if new_path == ctx.file_info.path:
                    # 即使路径相同，也要设置番号信息
                    ctx.serial_id = serial_id
                    return ProcessorResult.skip("文件名已经是标准格式，无需重命名")

                # 更新上下文
                ctx.serial_id = serial_id
                ctx.target_path = new_path

                return ProcessorResult.success(
                    f"提取到番号: {serial_id}",
                    {"serial_id": str(serial_id), "new_path": str(new_path)},
                )
            else:
                # 没有番号，设置目标路径为待处理目录
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

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """分析文件大小

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        # 只处理Misc文件
        if ctx.file_type != FileType.MISC:
            return ProcessorResult.skip("非Misc文件，跳过大小分析")

        try:
            file_size = ctx.file_info.path.stat().st_size
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

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """分析文件名

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        try:
            filename = ctx.file_info.name
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

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """判断Misc文件是否应该删除

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        # 只处理Misc文件
        if ctx.file_type != FileType.MISC:
            return ProcessorResult.skip("非Misc文件，跳过删除判断")

        try:
            ctx.should_delete = self._should_delete(ctx)

            if ctx.should_delete:
                return ProcessorResult.success("Misc文件符合删除条件")
            else:
                return ProcessorResult.success(
                    "Misc文件不符合删除条件，将移动到misc目录"
                )

        except Exception as e:
            return ProcessorResult.error(f"Misc文件删除判断失败: {str(e)}")

    def _should_delete(self, ctx: ProcessingContext) -> bool:
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
                if ctx.file_info.suffix.lower() in extensions_normalized:
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
            if not any(kw in ctx.file_info.name for kw in keywords):
                # 文件名不包含关键字，不删除
                return False

            # 两者都满足，删除
            return True

        # 如果只配置了其中一个或都没配置，不删除
        return False


class ActionDecider(Analyzer):
    """动作决策器

    根据文件类型、番号等信息，决定应该执行什么动作。
    """

    def __init__(
        self,
        organized_dir: Path,
        unorganized_dir: Path,
        archive_dir: Path,
        misc_dir: Path,
    ):
        """初始化动作决策器

        Args:
            organized_dir: 整理后的视频图片存储目录（B类）
            unorganized_dir: 无番号视频图片存储目录（C类）
            archive_dir: 压缩文件存储目录
            misc_dir: Misc文件存储目录（D类）
        """
        super().__init__("ActionDecider")
        self.organized_dir = organized_dir
        self.unorganized_dir = unorganized_dir
        self.archive_dir = archive_dir
        self.misc_dir = misc_dir

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """决策动作类型

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        try:
            # 视频/图片文件
            if ctx.file_type in [FileType.VIDEO, FileType.IMAGE]:
                if ctx.serial_id:
                    # 有番号：移动到整理目录，需要动态路径
                    ctx.action = FileAction.MOVE_TO_ORGANIZED
                    ctx.target_dir = generate_organized_path(
                        self.organized_dir, ctx.serial_id, ctx.file_info.suffix
                    )
                else:
                    # 无番号：移动到C目录
                    ctx.action = FileAction.MOVE_TO_UNORGANIZED
                    ctx.target_dir = self.unorganized_dir

            # 压缩文件
            elif ctx.file_type == FileType.ARCHIVE:
                ctx.action = FileAction.MOVE_TO_ARCHIVE
                ctx.target_dir = self.archive_dir

            # Misc文件
            elif ctx.file_type == FileType.MISC:
                if ctx.should_delete:
                    ctx.action = FileAction.DELETE
                else:
                    ctx.action = FileAction.MOVE_TO_MISC
                    ctx.target_dir = self.misc_dir
            else:
                ctx.action = FileAction.SKIP

            return ProcessorResult.success(
                f"决策动作: {ctx.action.value}",
                {
                    "action": ctx.action.value,
                    "target_dir": str(ctx.target_dir) if ctx.target_dir else None,
                },
            )

        except Exception as e:
            return ProcessorResult.error(f"动作决策失败: {str(e)}")
