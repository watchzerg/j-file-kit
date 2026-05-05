"""Raw 收件箱整理管道编排器。

设计意图：与 `FilePipeline` 解耦，采用 inbox **第一层** 文件与目录的三阶段编排：
阶段 1 将散落文件收入 `files_misc`；阶段 2 处理第一层目录（关键字迁出 / 清洗 / 分类占位）；
阶段 3 占位，为后续 `files_misc` 分流预留钩子。分阶段实现位于同包 `phase1`–`phase3`。
"""

import threading
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase1 import run_phase1
from j_file_kit.app.file_task.application.raw_pipeline.phase2 import run_phase2
from j_file_kit.app.file_task.application.raw_pipeline.phase3 import run_phase3
from j_file_kit.app.file_task.domain.ports import FileResultRepository
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics
from j_file_kit.shared.utils.logging import configure_task_logger, remove_task_logger


class RawFilePipeline:
    """Raw 任务专用管道：只遍历 `scan_root` 第一层条目并按阶段编排。"""

    def __init__(
        self,
        run_id: int,
        run_name: str,
        scan_root: Path,
        analyze_config: RawAnalyzeConfig,
        log_dir: Path,
        file_result_repository: FileResultRepository,
    ) -> None:
        """绑定一次 run 的标识与依赖；参数形状与 `FilePipeline` 对齐。"""
        self.run_id = run_id
        self.run_name = run_name
        self.scan_root = scan_root
        self.analyze_config = analyze_config
        self.log_dir = log_dir
        self._file_result_repository = file_result_repository
        self._log_handler_id: int | None = None

    def run(
        self,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """执行三阶段编排；阶段 3 本期仅占位，阶段 1 将第一层文件移入 `files_misc`。"""
        phases = RawPhaseCounters()
        ctx = PhaseContext(
            run_id=self.run_id,
            run_name=self.run_name,
            scan_root=self.scan_root,
            analyze_config=self.analyze_config,
            file_result_repository=self._file_result_repository,
        )
        try:
            self._start_task(dry_run)

            cancelled = run_phase1(
                ctx,
                phases,
                dry_run=dry_run,
                cancellation_event=cancellation_event,
            )
            if cancelled:
                return self._finish_task(dry_run, phases)

            cancelled = run_phase2(
                ctx,
                phases,
                dry_run=dry_run,
                cancellation_event=cancellation_event,
            )
            if cancelled:
                return self._finish_task(dry_run, phases)

            run_phase3(ctx, phases)

            return self._finish_task(dry_run, phases)

        except Exception as e:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).error(f"Raw 管道执行失败: {e!s}")
            raise
        finally:
            if self._log_handler_id is not None:
                remove_task_logger(self._log_handler_id)

    def _start_task(self, dry_run: bool) -> None:
        """注册按 run 隔离的 loguru sink，并写 TASK_START。"""
        self._log_handler_id = configure_task_logger(
            self.log_dir,
            self.run_name,
            self.run_id,
        )

        scan_root_str = str(self.scan_root) if self.scan_root else "未设置"
        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            scan_root=scan_root_str,
            level="TASK_START",
        ).info(f"开始任务: {self.run_name}")

        if dry_run:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info("运行在预览模式（dry_run）")

    def _finish_task(
        self,
        dry_run: bool,
        phases: RawPhaseCounters,
    ) -> FileTaskRunStatistics:
        """合并仓储聚合与阶段计数，写 TASK_END。"""
        repo_stats = self._file_result_repository.get_statistics(self.run_id)
        merged = {**repo_stats, **phases.as_dict()}

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="TASK_END",
            total_items=merged.get("total_items", 0),
            success_items=merged.get("success_items", 0),
            error_items=merged.get("error_items", 0),
            skipped_items=merged.get("skipped_items", 0),
            **phases.as_dict(),
        ).info(f"任务完成: {self.run_name}")

        if dry_run:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info("预览模式执行完成")

        return FileTaskRunStatistics.model_validate(merged)
