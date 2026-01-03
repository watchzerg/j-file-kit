"""JAV视频文件整理任务

完整的JAV视频文件整理任务实现。
使用 Decision 模式进行文件分析和处理。
"""

import threading
from pathlib import Path

from j_file_kit.app.config.domain.models import AppConfig
from j_file_kit.app.file_task.application.config import (
    AnalyzeConfig,
    JavVideoOrganizeConfig,
)
from j_file_kit.app.file_task.application.pipeline import FilePipeline
from j_file_kit.app.file_task.domain.ports import (
    FileItemRepository,
    FileProcessorRepository,
)
from j_file_kit.app.task.domain.models import TaskType
from j_file_kit.app.task.domain.ports import TaskRepository


class JavVideoOrganizer:
    """JAV视频文件整理任务

    TaskRunner 是业务用例层，定义"做什么"。

    职责：
    - 定义业务用例，配置 Pipeline
    - 通过 `run()` 方法执行任务

    设计意图：
    - 使用 Decision 模式进行文件分析和处理
    - 简化的 Pipeline 设计，不使用 ProcessorChain
    - 构造时注入所需的 repositories，支持依赖注入
    """

    def __init__(
        self,
        config: AppConfig,
        log_dir: Path,
        task_repository: TaskRepository,
        file_item_repository: FileItemRepository,
        file_processor_repository: FileProcessorRepository,
    ) -> None:
        """初始化JAV视频文件整理任务

        Args:
            config: 应用配置
            log_dir: 日志目录
            task_repository: 任务仓储（更新任务状态）
            file_item_repository: 文件处理结果仓储
            file_processor_repository: 文件操作日志仓储
        """
        self.config = config
        self.log_dir = log_dir
        self._task_repository = task_repository
        self._file_item_repository = file_item_repository
        self._file_processor_repository = file_processor_repository

        self.task_config = self.config.get_task("jav_video_organizer")

        if not self.task_config:
            raise ValueError("未找到 jav_video_organizer 任务配置")

        # 获取类型化的配置对象
        self.file_config: JavVideoOrganizeConfig = self.task_config.get_config(
            JavVideoOrganizeConfig,
        )

        # 从 GlobalConfig 获取目录路径
        self.inbox_dir: Path | None = self.config.global_.inbox_dir
        self.sorted_dir: Path | None = self.config.global_.sorted_dir
        self.unsorted_dir: Path | None = self.config.global_.unsorted_dir
        self.archive_dir: Path | None = self.config.global_.archive_dir
        self.misc_dir: Path | None = self.config.global_.misc_dir

    @property
    def task_type(self) -> TaskType:
        """任务类型"""
        return TaskType.JAV_VIDEO_ORGANIZER

    def _create_analyze_config(self) -> AnalyzeConfig:
        """创建分析配置

        将任务配置转换为分析配置。

        Returns:
            分析配置对象
        """
        return AnalyzeConfig(
            video_extensions=self.file_config.video_extensions,
            image_extensions=self.file_config.image_extensions,
            archive_extensions=self.file_config.archive_extensions,
            sorted_dir=self.sorted_dir,
            unsorted_dir=self.unsorted_dir,
            archive_dir=self.archive_dir,
            misc_dir=self.misc_dir,
            misc_file_delete_rules=self.file_config.misc_file_delete_rules,
        )

    def run(
        self,
        task_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> None:
        """运行文件整理

        Args:
            task_id: 任务 ID
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancellation_event: 取消事件，用于检查任务是否被取消
        """
        if self.inbox_dir is None:
            raise ValueError("inbox_dir 未设置")

        # 创建分析配置
        analyze_config = self._create_analyze_config()

        # 创建并运行 Pipeline
        pipeline = FilePipeline(
            task_id=task_id,
            task_name=self.task_type.value,
            scan_root=self.inbox_dir,
            analyze_config=analyze_config,
            log_dir=self.log_dir,
            task_repository=self._task_repository,
            file_processor_repository=self._file_processor_repository,
            file_item_repository=self._file_item_repository,
        )
        pipeline.run(dry_run=dry_run, cancellation_event=cancellation_event)
