"""视频文件整理任务

完整的视频文件整理任务实现。
组合使用各种处理器实现文件分类、番号提取、文件移动等功能。
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from ..domain.models import TaskReport, TaskType
from ..domain.processors.analyzers import (
    ActionDecider,
    FileClassifier,
    SerialIdExtractor,
)
from ..domain.processors.finalizers import ReportGenerator
from ..domain.task import BaseTask
from ..infrastructure.config.config import FileOrganizeConfig, TaskConfig
from ..infrastructure.persistence.db import DatabaseManager
from ..services.pipeline import Pipeline


class VideoFileOrganizer(BaseTask):
    """视频文件整理任务

    这是一个完整的文件整理任务实现，展示了如何组合使用各种处理器。
    """

    def __init__(self, config: TaskConfig):
        """初始化视频文件整理任务

        Args:
            config: 任务配置
        """
        self.config = config
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

    @property
    def task_type(self) -> TaskType:
        """任务类型"""
        return TaskType.VIDEO_ORGANIZER

    def create_pipeline(self, task_id: int, db_manager: DatabaseManager) -> Pipeline:
        """创建处理管道

        Args:
            task_id: 任务ID
            db_manager: 数据库管理器实例

        Returns:
            配置好的处理管道
        """
        # 创建管道
        pipeline = Pipeline(self.config, self.task_type.value, task_id, db_manager)

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
        pipeline.add_executor(pipeline.create_unified_executor())

        # 添加终结器
        pipeline.add_finalizer(
            ReportGenerator(self.config.global_.report_dir, pipeline.report)
        )

        return pipeline

    def run(
        self,
        task_id: int,
        db_manager: DatabaseManager,
        dry_run: bool = False,
        cancelled_event: threading.Event | None = None,
    ) -> TaskReport:
        """运行文件整理

        Args:
            task_id: 任务ID
            db_manager: 数据库管理器实例
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancelled_event: 取消事件，用于检查任务是否被取消

        Returns:
            任务报告
        """
        pipeline = self.create_pipeline(task_id, db_manager)
        return pipeline.run(dry_run=dry_run, cancelled_event=cancelled_event)
