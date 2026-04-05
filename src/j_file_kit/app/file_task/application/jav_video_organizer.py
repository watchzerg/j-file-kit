"""JAV视频文件整理任务

完整的JAV视频文件整理任务实现。
使用 Decision 模式进行文件分析和处理。
"""

import threading
from pathlib import Path

from j_file_kit.app.file_task.application.config import (
    AnalyzeConfig,
    JavVideoOrganizeConfig,
)
from j_file_kit.app.file_task.application.jav_filename_util import build_serial_pattern
from j_file_kit.app.file_task.application.pipeline import FilePipeline
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import FileTaskRunStatistics, TaskConfig
from j_file_kit.app.file_task.domain.ports import FileResultRepository


class JavVideoOrganizer:
    """JAV视频文件整理任务

    FileTaskRunner 是业务用例层，定义"做什么"。

    职责：
    - 定义业务用例，配置 Pipeline
    - 通过 `run()` 方法执行任务

    设计意图：
    - 使用 Decision 模式进行文件分析和处理
    - 简化的 Pipeline 设计，不使用 ProcessorChain
    - 构造时注入所需的 repositories，支持依赖注入
    - 所有配置（目录路径 + 文件规则）统一来自 TaskConfig
    """

    def __init__(
        self,
        task_config: TaskConfig,
        log_dir: Path,
        file_result_repository: FileResultRepository,
    ) -> None:
        """初始化JAV视频文件整理任务

        Args:
            task_config: 任务配置（包含目录路径和文件处理规则）
            log_dir: 日志目录
            file_result_repository: 文件处理结果仓储
        """
        self._task_config = task_config
        self.log_dir = log_dir
        self._file_result_repository = file_result_repository

        self.file_config: JavVideoOrganizeConfig = self._task_config.get_config(
            JavVideoOrganizeConfig,
        )

    @property
    def task_type(self) -> str:
        """任务类型"""
        return TASK_TYPE_JAV_VIDEO_ORGANIZER

    def _create_analyze_config(self) -> AnalyzeConfig:
        """创建分析配置

        将任务配置转换为分析配置。

        Returns:
            分析配置对象
        """
        return AnalyzeConfig(
            video_extensions=self.file_config.video_extensions,
            image_extensions=self.file_config.image_extensions,
            subtitle_extensions=self.file_config.subtitle_extensions,
            archive_extensions=self.file_config.archive_extensions,
            sorted_dir=self.file_config.sorted_dir,
            unsorted_dir=self.file_config.unsorted_dir,
            archive_dir=self.file_config.archive_dir,
            misc_dir=self.file_config.misc_dir,
            misc_file_delete_rules=self.file_config.misc_file_delete_rules,
            serial_pattern=build_serial_pattern(
                self.file_config.serial_id_combinations,
            ),
        )

    def run(
        self,
        run_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """运行文件整理

        Args:
            run_id: 执行实例 ID
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancellation_event: 取消事件，用于检查任务是否被取消
        """
        if self.file_config.inbox_dir is None:
            raise ValueError("inbox_dir 未设置")

        analyze_config = self._create_analyze_config()

        pipeline = FilePipeline(
            run_id=run_id,
            run_name=self.task_type,
            scan_root=self.file_config.inbox_dir,
            analyze_config=analyze_config,
            log_dir=self.log_dir,
            file_result_repository=self._file_result_repository,
        )
        return pipeline.run(dry_run=dry_run, cancellation_event=cancellation_event)
