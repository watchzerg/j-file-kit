"""番号提取器

从文件名中提取番号，并生成重构后的文件名。
只负责提取番号和生成文件名，不设置完整路径。
"""

from ....interfaces.processors import Analyzer
from ....models import FileType, PathEntryContext, PathEntryType, ProcessorResult
from ....utils.filename_generation import generate_new_filename


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
