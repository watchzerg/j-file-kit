"""JAV 收件箱整理任务入口（FileTaskRunner 实现）。

本模块只做「配置绑定 + 管道组装」：具体扫描 / 分析 / 执行 / 落库循环在
`FilePipeline`（`pipeline.py`）中；分析与决策在 `analyzer` + Decision 模型中。
"""

import threading
from pathlib import Path

from j_file_kit.app.file_task.application.config import (
    JavAnalyzeConfig,
    JavVideoOrganizeConfig,
)
from j_file_kit.app.file_task.application.pipeline import FilePipeline
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_ARCHIVE_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS,
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
    DEFAULT_SUBTITLE_EXTENSIONS,
    DEFAULT_VIDEO_EXTENSIONS,
)
from j_file_kit.app.file_task.domain.ports import FileResultRepository
from j_file_kit.app.file_task.domain.task_config import TaskConfig
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics


class JavVideoOrganizer:
    """JAV 视频收件箱整理用例（`FileTaskRunner` 协议实现）。

    核心流程（读者只需把握这一条链路）：
        1. 构造：注入 `TaskConfig`、`log_dir`、`FileResultRepository`，并将 YAML 中的
           `config` 反序列化为强类型的 `JavVideoOrganizeConfig`（目录与可调删除策略等）；
           扩展名与站标去噪由 `organizer_defaults` 在 `_create_analyze_config` 注入。
        2. run：
           - 要求 `inbox_dir` 已配置，否则立即失败；
           - 把 `JavVideoOrganizeConfig` 压平为 `JavAnalyzeConfig`（供 `analyze_jav_file` 使用）；
           - 用 `inbox_dir` 作为扫描根目录创建 `FilePipeline`，传入同一 `run_id` 与
             `file_result_repository`；
           - 委托 `FilePipeline.run()`：对收件箱内每个文件执行「分析 → Decision →
             执行（或 dry_run 仅预览）→ 写入 SQLite 结果」，返回 `FileTaskRunStatistics`。

    边界：本类不包含遍历目录、`analyze_jav_file`、`execute_decision` 的实现；仅负责
    把本任务类型的配置接到通用管道上。Decision 模式与统计细节见 `pipeline` / `jav_analyzer`。
    """

    def __init__(
        self,
        task_config: TaskConfig,
        log_dir: Path,
        file_result_repository: FileResultRepository,
    ) -> None:
        """绑定任务配置与持久化端口，并解析出 `JavVideoOrganizeConfig`。

        `task_config` 来自 YAML；`get_config(JavVideoOrganizeConfig)` 在此处完成类型化，
        后续 `run()` 只操作 `self.file_config` 与派生的 `JavAnalyzeConfig`。
        """
        self._task_config = task_config
        self.log_dir = log_dir
        self._file_result_repository = file_result_repository

        self.file_config: JavVideoOrganizeConfig = self._task_config.get_config(
            JavVideoOrganizeConfig,
        )

    @property
    def task_type(self) -> str:
        """任务类型常量，供调度层区分 `FileTaskRunner` 实现（与 `TASK_TYPE_*` 一致）。"""
        return TASK_TYPE_JAV_VIDEO_ORGANIZER

    def _create_analyze_config(self) -> JavAnalyzeConfig:
        """从 `JavVideoOrganizeConfig` 生成 `JavAnalyzeConfig`（分析阶段唯一使用的配置 DTO）。

        设计意图：`JavVideoOrganizeConfig` 面向任务/存储；`JavAnalyzeConfig` 面向纯函数
        `analyze_jav_file`。四类扩展名、`jav_filename_strip_substrings`、`misc_file_delete_rules.extensions`
        来自 `organizer_defaults`；YAML 中的 misc extensions 键已在模型层剔除。
        """
        misc_rules = dict(self.file_config.misc_file_delete_rules)
        misc_rules["extensions"] = sorted(DEFAULT_MISC_FILE_DELETE_EXTENSIONS)
        return JavAnalyzeConfig(
            video_extensions=set(DEFAULT_VIDEO_EXTENSIONS),
            image_extensions=set(DEFAULT_IMAGE_EXTENSIONS),
            subtitle_extensions=set(DEFAULT_SUBTITLE_EXTENSIONS),
            archive_extensions=set(DEFAULT_ARCHIVE_EXTENSIONS),
            sorted_dir=self.file_config.sorted_dir,
            unsorted_dir=self.file_config.unsorted_dir,
            archive_dir=self.file_config.archive_dir,
            misc_dir=self.file_config.misc_dir,
            misc_file_delete_rules=misc_rules,
            video_small_delete_bytes=self.file_config.video_small_delete_bytes,
            inbox_delete_rules=self.file_config.inbox_delete_rules,
            jav_filename_strip_substrings=DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS,
        )

    def run(
        self,
        run_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """执行任务：组装 `FilePipeline` 并委托其完成全流程，返回统计快照。

        - `dry_run=True` 时管道只生成 Decision 与预览结果，不落地移动/删除。
        - `cancellation_event` 由上层注入，管道内轮询后提前结束遍历（详见 `FilePipeline.run`）。

        Raises:
            ValueError: `inbox_dir` 未在配置中设置。

        与协议 `FileTaskRunner.run` 签名一致，供 `FileTaskRunManager` 调用。
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
