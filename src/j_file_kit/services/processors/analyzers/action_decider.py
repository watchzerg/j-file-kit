"""动作决策器

根据文件类型、番号等信息，决定应该执行什么动作。
"""

from pathlib import Path

from ....interfaces.processors import Analyzer
from ....models import (
    FileType,
    PathEntryAction,
    PathEntryContext,
    PathEntryType,
    ProcessorResult,
)
from ....utils.file_utils import generate_sorted_dir


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
