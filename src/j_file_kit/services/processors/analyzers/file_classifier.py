"""文件类型分类器

根据文件扩展名判断文件类型（视频/图片/压缩/Misc）。
"""

from ....interfaces.processors import Analyzer
from ....models import PathEntryContext, PathEntryType, ProcessorResult
from ....utils.file_utils import get_file_type


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
