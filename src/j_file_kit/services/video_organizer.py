"""视频文件整理任务

完整的视频文件整理任务实现。
组合使用各种处理器实现文件分类、番号提取、文件移动等功能。

这是用例实现，位于services层。
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from ..infrastructure.config.config import FileOrganizeConfig, TaskConfig
from ..infrastructure.persistence import (
    ItemResultRepository,
    OperationRepository,
    TaskRepository,
)
from ..interfaces.task import BaseTask
from ..models import TaskType
from .pipeline import Pipeline
from .processors.analyzers import (
    FileActionDecider,
    FileClassifier,
    FileSerialIdExtractor,
    MiscFileDeleteAnalyzer,
    MiscFileSizeAnalyzer,
)
from .processors.executors import FileEmptyDirectoryExecutor
from .processors.finalizers import FileTaskStatisticsFinalizer
from .processors.initializers import (
    FileConfigValidatorInitializer,
    FileResourceInitializer,
    FileTaskStatusInitializer,
)


class VideoFileOrganizer(BaseTask):
    """视频文件整理任务

    这是一个完整的文件整理任务实现，展示了如何组合使用各种处理器。
    """

    def __init__(self, config: TaskConfig, log_dir: Path):
        """初始化视频文件整理任务

        Args:
            config: 任务配置
            log_dir: 日志目录
        """
        self.config = config
        self.log_dir = log_dir
        self.task_config = self.config.get_task("video_file_organizer")

        if not self.task_config:
            raise ValueError("未找到 video_file_organizer 任务配置")

        # 获取类型化的配置对象
        self.file_config: FileOrganizeConfig = self.task_config.get_config(
            FileOrganizeConfig
        )

        # 从 GlobalConfig 获取目录路径
        self.inbox_dir: Path | None = self.config.global_.inbox_dir
        self.sorted_dir: Path | None = self.config.global_.sorted_dir
        self.unsorted_dir: Path | None = self.config.global_.unsorted_dir
        self.archive_dir: Path | None = self.config.global_.archive_dir
        self.misc_dir: Path | None = self.config.global_.misc_dir

        # 设置文件类型扩展名
        self.video_extensions: set[str] = self.file_config.video_extensions
        self.image_extensions: set[str] = self.file_config.image_extensions
        self.archive_extensions: set[str] = self.file_config.archive_extensions

        # 设置删除规则
        self.misc_file_delete_rules: dict[str, Any] = (
            self.file_config.misc_file_delete_rules
        )

    @property
    def task_type(self) -> TaskType:
        """任务类型"""
        return TaskType.VIDEO_ORGANIZER

    def create_pipeline(
        self,
        task_id: int,
        log_dir: Path,
        task_repository: TaskRepository,
        operation_repository: OperationRepository,
        item_result_repository: ItemResultRepository,
    ) -> Pipeline:
        """创建处理管道

        Args:
            task_id: 任务ID
            log_dir: 日志目录
            task_repository: 任务仓储实例
            operation_repository: 操作记录仓储实例
            item_result_repository: Item结果仓储实例

        Returns:
            配置好的处理管道
        """
        # 创建管道
        pipeline = Pipeline(
            self.config,
            self.task_type.value,
            log_dir,
            operation_repository,
            item_result_repository,
            task_id,
            task_repository,
        )

        # 添加初始化器（按依赖顺序）
        # 1. 状态更新：确保任务状态正确
        pipeline.add_initializer(
            FileTaskStatusInitializer(
                task_id=task_id,
                task_repository=task_repository,
            )
        )
        # 2. 配置验证：验证配置有效性
        pipeline.add_initializer(
            FileConfigValidatorInitializer(
                config=self.config,
            )
        )
        # 3. 资源初始化：确保目录已准备就绪
        pipeline.add_initializer(
            FileResourceInitializer(
                config=self.config,
            )
        )

        # 添加分析器
        pipeline.add_analyzer(
            FileClassifier(
                self.video_extensions,
                self.image_extensions,
                self.archive_extensions,
            )
        )
        pipeline.add_analyzer(MiscFileSizeAnalyzer())
        pipeline.add_analyzer(MiscFileDeleteAnalyzer(self.misc_file_delete_rules))
        pipeline.add_analyzer(FileSerialIdExtractor())
        pipeline.add_analyzer(
            FileActionDecider(
                self.sorted_dir,
                self.unsorted_dir,
                self.archive_dir,
                self.misc_dir,
            )
        )

        # 添加执行器
        pipeline.add_executor(pipeline.create_unified_executor())

        # 添加空目录清理执行器（放在最后，确保文件处理完成后再清理目录）
        # 设计意图：在文件处理完成后，利用自底向上遍历顺序清理空文件夹
        pipeline.add_executor(
            FileEmptyDirectoryExecutor(self.inbox_dir, operation_repository)
        )

        # 添加任务统计信息终结器
        # finalizer 是全局的，pipeline 会先处理完所有文件的 processors，再执行 finalizers
        # 所以添加顺序不影响执行顺序
        pipeline.add_finalizer(
            FileTaskStatisticsFinalizer(
                task_id=task_id,
                task_repository=task_repository,
                operation_repository=operation_repository,
                item_result_repository=item_result_repository,
            )
        )

        return pipeline

    def run(
        self,
        task_id: int,
        task_repository: TaskRepository,
        operation_repository: OperationRepository,
        item_result_repository: ItemResultRepository,
        dry_run: bool = False,
        cancelled_event: threading.Event | None = None,
    ) -> None:
        """运行文件整理

        Args:
            task_id: 任务ID
            task_repository: 任务仓储实例
            operation_repository: 操作记录仓储实例
            item_result_repository: Item结果仓储实例
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancelled_event: 取消事件，用于检查任务是否被取消
        """
        pipeline = self.create_pipeline(
            task_id,
            self.log_dir,
            task_repository,
            operation_repository,
            item_result_repository,
        )
        pipeline.run(dry_run=dry_run, cancelled_event=cancelled_event)
