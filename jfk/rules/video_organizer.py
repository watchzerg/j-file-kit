"""视频文件整理规则示例

这是一个完整的视频文件整理规则示例，展示了如何使用 j-file-kit 进行文件整理。
"""

from pathlib import Path
from typing import Any

from ..core.config import TaskConfig, load_config
from ..core.models import ProcessingContext, ProcessorResult
from ..core.pipeline import Pipeline
from ..core.processor import Analyzer, Executor, Finalizer
from ..processors.analyzers import FileClassifier, SerialIdExtractor
from ..processors.executors import FileMover, FileRenamer
from ..processors.finalizers import EmptyDirCleaner, ReportGenerator
from ..utils.file_utils import get_file_type_from_path


class VideoFileOrganizer:
    """视频文件整理器
    
    这是一个完整的文件整理规则示例，展示了如何组合使用各种处理器。
    """
    
    def __init__(self, config_path: str | Path):
        """初始化视频文件整理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = load_config(config_path)
        self.task_config = self.config.get_task("video_file_organizer")
        
        if not self.task_config:
            raise ValueError("未找到 video_file_organizer 任务配置")
        
        # 获取任务配置
        self.file_config = self.task_config.get_config(dict)  # 这里应该使用具体的配置类型
        
        # 设置路径
        self.todo_non_vidpic_dir = Path(self.file_config["todo_non_vidpic_dir"])
        self.todo_vidpic_dir = Path(self.file_config["todo_vidpic_dir"])
        
        # 设置文件类型
        self.video_extensions = set(self.file_config["video_extensions"])
        self.image_extensions = set(self.file_config["image_extensions"])
        
        # 设置番号模式
        self.serial_id_pattern = self.file_config["serial_id_pattern"]
    
    def create_pipeline(self) -> Pipeline:
        """创建处理管道
        
        Returns:
            配置好的处理管道
        """
        # 创建管道
        pipeline = Pipeline(self.config, "video_file_organizer")
        
        # 添加分析器
        pipeline.add_analyzer(
            FileClassifier(self.video_extensions, self.image_extensions)
        )
        pipeline.add_analyzer(
            SerialIdExtractor(self.serial_id_pattern)
        )
        
        # 添加执行器
        pipeline.add_executor(
            FileRenamer(pipeline.transaction_log)
        )
        pipeline.add_executor(
            FileMover(self.todo_non_vidpic_dir, pipeline.transaction_log)
        )
        pipeline.add_executor(
            FileMover(self.todo_vidpic_dir, pipeline.transaction_log)
        )
        
        # 添加终结器
        pipeline.add_finalizer(
            EmptyDirCleaner(self.config.global_.scan_root, pipeline.transaction_log)
        )
        pipeline.add_finalizer(
            ReportGenerator(self.config.global_.report_dir, pipeline.report)
        )
        
        return pipeline
    
    def run(self) -> Any:
        """运行文件整理
        
        Returns:
            任务报告
        """
        pipeline = self.create_pipeline()
        return pipeline.run()
    
    def run_dry(self) -> Any:
        """运行预览模式
        
        Returns:
            任务报告
        """
        pipeline = self.create_pipeline()
        return pipeline.run_dry()


class CustomVideoAnalyzer(Analyzer):
    """自定义视频分析器
    
    这是一个自定义分析器示例，展示了如何扩展分析功能。
    """
    
    def __init__(self, min_duration: int = 60):
        """初始化自定义视频分析器
        
        Args:
            min_duration: 最小视频时长（秒）
        """
        super().__init__("CustomVideoAnalyzer")
        self.min_duration = min_duration
    
    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """分析视频文件
        
        Args:
            ctx: 处理上下文
            
        Returns:
            分析结果
        """
        try:
            # 只处理视频文件
            if ctx.file_type != "video":
                return ProcessorResult.skip("非视频文件，跳过分析")
            
            # 这里可以添加视频分析逻辑
            # 例如：检查视频时长、分辨率、编码格式等
            
            # 示例：检查文件大小
            file_size = ctx.file_info.path.stat().st_size
            if file_size < 1024 * 1024:  # 小于1MB
                return ProcessorResult.warning("视频文件过小，可能损坏")
            
            # 将分析结果存储到自定义数据中
            ctx.custom_data["file_size"] = file_size
            ctx.custom_data["analysis_completed"] = True
            
            return ProcessorResult.success(
                f"视频分析完成，文件大小: {file_size} 字节"
            )
            
        except Exception as e:
            return ProcessorResult.error(f"视频分析失败: {str(e)}")


class CustomFileMover(Executor):
    """自定义文件移动器
    
    这是一个自定义执行器示例，展示了如何扩展执行功能。
    """
    
    def __init__(self, target_dir: Path, file_type: str, transaction_log=None):
        """初始化自定义文件移动器
        
        Args:
            target_dir: 目标目录
            file_type: 文件类型
            transaction_log: 事务日志记录器
        """
        super().__init__("CustomFileMover")
        self.target_dir = target_dir
        self.file_type = file_type
        self.transaction_log = transaction_log
    
    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """执行文件移动
        
        Args:
            ctx: 处理上下文
            
        Returns:
            执行结果
        """
        try:
            # 检查文件类型
            if ctx.file_type != self.file_type:
                return ProcessorResult.skip(f"文件类型不匹配: {ctx.file_type}")
            
            # 检查是否需要移动
            if not self._should_move(ctx):
                return ProcessorResult.skip("无需移动")
            
            # 执行移动逻辑
            # 这里可以添加自定义的移动逻辑
            # 例如：根据文件大小、创建时间等条件决定移动目标
            
            return ProcessorResult.success("自定义移动逻辑执行完成")
            
        except Exception as e:
            return ProcessorResult.error(f"自定义移动失败: {str(e)}")
    
    def _should_move(self, ctx: ProcessingContext) -> bool:
        """判断是否需要移动文件
        
        Args:
            ctx: 处理上下文
            
        Returns:
            是否需要移动
        """
        # 这里可以添加自定义的移动条件
        # 例如：文件大小、创建时间、文件名模式等
        return True


def create_video_organizer_rule(config_path: str | Path) -> VideoFileOrganizer:
    """创建视频文件整理器
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        视频文件整理器实例
    """
    return VideoFileOrganizer(config_path)


def run_video_organizer(config_path: str | Path, dry_run: bool = False) -> Any:
    """运行视频文件整理
    
    Args:
        config_path: 配置文件路径
        dry_run: 是否预览模式
        
    Returns:
        任务报告
    """
    organizer = create_video_organizer_rule(config_path)
    
    if dry_run:
        return organizer.run_dry()
    else:
        return organizer.run()


# 使用示例
if __name__ == "__main__":
    # 加载配置
    config_path = "configs/task_config.yaml"
    
    # 创建整理器
    organizer = VideoFileOrganizer(config_path)
    
    # 运行整理（预览模式）
    print("运行预览模式...")
    report = organizer.run_dry()
    print(f"预览完成，处理了 {report.total_files} 个文件")
    
    # 如果预览结果满意，可以运行实际整理
    # print("运行实际整理...")
    # report = organizer.run()
    # print(f"整理完成，成功处理 {report.success_files} 个文件")
