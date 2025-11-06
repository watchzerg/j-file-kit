"""分析器模块

实现文件分析功能，如文件类型分类、番号提取等。
"""

from __future__ import annotations

from ..core.models import FileType, ProcessingContext, ProcessorResult
from ..core.processor import Analyzer
from ..utils.file_utils import get_file_type_from_path
from ..utils.filename_generation import generate_new_filename


class FileClassifier(Analyzer):
    """文件类型分类器

    根据文件扩展名判断文件类型（视频/图片/其他）。
    """

    def __init__(self, video_extensions: set[str], image_extensions: set[str]):
        """初始化文件分类器

        Args:
            video_extensions: 视频文件扩展名集合
            image_extensions: 图片文件扩展名集合
        """
        super().__init__("FileClassifier")
        self.video_extensions = video_extensions
        self.image_extensions = image_extensions

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """分析文件类型

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        try:
            # 获取文件类型
            file_type = get_file_type_from_path(
                ctx.file_info.path, self.video_extensions, self.image_extensions
            )

            # 更新上下文
            ctx.file_type = file_type

            # 根据文件类型决定是否短路
            if file_type == FileType.OTHER:
                # 非视频/图片文件，设置短路标记
                ctx.skip_remaining = True
                return ProcessorResult.success(
                    f"文件类型: {file_type.value}，跳过后续处理"
                )
            else:
                return ProcessorResult.success(f"文件类型: {file_type.value}，继续处理")

        except Exception as e:
            return ProcessorResult.error(f"文件类型分析失败: {str(e)}")


class SerialIdExtractor(Analyzer):
    """番号提取器

    从文件名中提取番号，并生成新的文件名。
    """

    def __init__(self):
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
                    {"serial_id": serial_id, "new_path": str(new_path)},
                )
            else:
                # 没有番号，设置目标路径为待处理目录
                return ProcessorResult.success("未找到番号，将移动到待处理目录")

        except Exception as e:
            return ProcessorResult.error(f"番号提取失败: {str(e)}")


class FileSizeAnalyzer(Analyzer):
    """文件大小分析器

    分析文件大小，可用于过滤或分类。
    """

    def __init__(self, min_size: int = 0, max_size: int | None = None):
        """初始化文件大小分析器

        Args:
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节），None 表示无限制
        """
        super().__init__("FileSizeAnalyzer")
        self.min_size = min_size
        self.max_size = max_size

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """分析文件大小

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        try:
            file_size = ctx.file_info.path.stat().st_size

            # 检查大小限制
            if file_size < self.min_size:
                ctx.skip_remaining = True
                return ProcessorResult.skip(f"文件太小: {file_size} 字节")

            if self.max_size is not None and file_size > self.max_size:
                ctx.skip_remaining = True
                return ProcessorResult.skip(f"文件太大: {file_size} 字节")

            # 将文件大小信息存储到自定义数据中
            ctx.custom_data["file_size"] = file_size

            return ProcessorResult.success(
                f"文件大小: {file_size} 字节", {"file_size": file_size}
            )

        except Exception as e:
            return ProcessorResult.error(f"文件大小分析失败: {str(e)}")


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


class DuplicateDetector(Analyzer):
    """重复文件检测器

    检测可能的重复文件。
    """

    def __init__(self):
        """初始化重复文件检测器"""
        super().__init__("DuplicateDetector")
        self.seen_files = set()

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """检测重复文件

        Args:
            ctx: 处理上下文

        Returns:
            分析结果
        """
        try:
            # 使用文件名和大小作为重复检测的依据
            file_key = (ctx.file_info.name, ctx.file_info.path.stat().st_size)

            if file_key in self.seen_files:
                ctx.custom_data["is_duplicate"] = True
                return ProcessorResult.warning("检测到可能的重复文件")
            else:
                self.seen_files.add(file_key)
                ctx.custom_data["is_duplicate"] = False
                return ProcessorResult.success("文件唯一性检查通过")

        except Exception as e:
            return ProcessorResult.error(f"重复文件检测失败: {str(e)}")
