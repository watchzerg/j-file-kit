"""视频文件整理规则示例

这是一个完整的视频文件整理规则示例，展示了如何使用 j-file-kit 进行文件整理。
"""

from pathlib import Path
from typing import Any

from ..core.config import FileOrganizeConfig, load_config
from ..core.pipeline import Pipeline
from ..processors.analyzers import ActionDecider, FileClassifier, SerialIdExtractor
from ..processors.executors import UnifiedFileExecutor
from ..processors.finalizers import ReportGenerator


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

        # 获取类型化的配置对象
        self.file_config: FileOrganizeConfig = self.task_config.get_config(
            FileOrganizeConfig
        )

        # 设置目录路径
        self.organized_dir: Path = self.file_config.organized_dir
        self.unorganized_dir: Path = self.file_config.unorganized_dir
        self.archive_dir: Path = self.file_config.archive_dir
        self.misc_dir: Path = self.file_config.misc_dir

        # 设置文件类型扩展名
        self.video_extensions: set[str] = self.file_config.video_extensions
        self.image_extensions: set[str] = self.file_config.image_extensions
        self.archive_extensions: set[str] = self.file_config.archive_extensions

        # 设置删除规则
        self.delete_rules: dict[str, Any] = self.file_config.delete_rules

    def create_pipeline(self) -> Pipeline:
        """创建处理管道

        Returns:
            配置好的处理管道
        """
        # 创建管道
        pipeline = Pipeline(self.config, "video_file_organizer")

        # 添加分析器
        pipeline.add_analyzer(
            FileClassifier(
                self.video_extensions,
                self.image_extensions,
                self.archive_extensions,
            )
        )
        pipeline.add_analyzer(SerialIdExtractor())
        pipeline.add_analyzer(
            ActionDecider(
                self.organized_dir,
                self.unorganized_dir,
                self.archive_dir,
                self.misc_dir,
                self.delete_rules,
            )
        )

        # 添加执行器
        pipeline.add_executor(UnifiedFileExecutor(pipeline.transaction_log))

        # 添加终结器
        pipeline.add_finalizer(
            ReportGenerator(self.config.global_.report_dir, pipeline.report)
        )

        return pipeline

    def run(self, dry_run: bool = False) -> Any:
        """运行文件整理

        Args:
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）

        Returns:
            任务报告
        """
        pipeline = self.create_pipeline()
        return pipeline.run(dry_run=dry_run)

    def run_dry(self) -> Any:
        """运行预览模式（已废弃，请使用 run(dry_run=True)）

        Returns:
            任务报告
        """
        return self.run(dry_run=True)


# 使用示例
if __name__ == "__main__":
    # 加载配置
    config_path = "configs/task_config.yaml"

    # 创建整理器
    organizer = VideoFileOrganizer(config_path)

    # 运行整理（预览模式）
    print("运行预览模式...")
    report = organizer.run(dry_run=True)
    print(f"预览完成，处理了 {report.total_files} 个文件")

    # 如果预览结果满意，可以运行实际整理
    # print("运行实际整理...")
    # report = organizer.run()
    # print(f"整理完成，成功处理 {report.success_files} 个文件")
