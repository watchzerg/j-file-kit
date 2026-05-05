"""文件处理管道：在给定 `scan_root` 下的通用「扫描 → 分析 → 执行 → 落库」编排。

单文件闭环见 `item_processor`；结果折叠见 `result_mapper`；日志与内存计数见 `observer`；
空目录收缩见 `directory_cleanup`。

`JavVideoOrganizer` 将收件箱目录与 `JavAnalyzeConfig` 注入本类；本模块不承载任务类型的业务含义。
"""

import threading
from pathlib import Path

from j_file_kit.app.file_task.application.file_ops import scan_directory_items
from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.application.jav_pipeline.directory_cleanup import (
    cleanup_empty_directory_under_scan,
)
from j_file_kit.app.file_task.application.jav_pipeline.item_processor import (
    process_single_file_for_run,
)
from j_file_kit.app.file_task.application.jav_pipeline.observer import (
    PipelineRunCounters,
    finish_task_with_repository_statistics,
    log_pipeline_execution_failed,
    log_task_cancelled,
    log_task_start,
)
from j_file_kit.app.file_task.domain.file_types import PathEntryType
from j_file_kit.app.file_task.domain.ports import FileResultRepository
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics
from j_file_kit.shared.utils.logging import (
    configure_task_logger,
    remove_task_logger,
)


class FilePipeline:
    """针对某一 `scan_root` 的流式处理管道（与具体任务名解耦，由调用方传入 `run_name`）。

    核心流程：
        1. `configure_task_logger` + `log_task_start`：挂接本 run 专用日志并写 TASK_START。
        2. 深度优先遍历 `scan_root`：遇文件走 `process_single_file_for_run`，遇目录走
           `cleanup_empty_directory_under_scan`；循环中检查 `cancellation_event` 可提前跳出。
        3. `finish_task_with_repository_statistics`：以仓储聚合为准写 TASK_END 并返回统计。
        4. `finally`：移除本 run 的 log handler。

    与 `JavVideoOrganizer` 的关系：后者只负责组装参数，不重写上述循环。
    """

    def __init__(
        self,
        run_id: int,
        run_name: str,
        scan_root: Path,
        analyze_config: JavAnalyzeConfig,
        log_dir: Path,
        file_result_repository: FileResultRepository,
    ) -> None:
        """绑定一次 run 的标识、扫描根、分析配置、日志目录与结果仓储。

        `scan_root` 在 JAV 任务中为 `inbox_dir`；`analyze_config` 已不含 inbox 路径。
        `file_result_repository` 由上游注入，pipeline 不关闭连接。
        """
        self.run_id = run_id
        self.run_name = run_name
        self.scan_root = scan_root
        self.analyze_config = analyze_config
        self.log_dir = log_dir
        self.file_result_repository = file_result_repository

        self._counters = PipelineRunCounters()
        self._log_handler_id: int | None = None

    @property
    def total_items(self) -> int:
        """内存侧已处理条数（成功路径递增；与仓储 `get_statistics` 口径独立）。"""
        return self._counters.total_items

    @property
    def success_items(self) -> int:
        return self._counters.success_items

    @property
    def error_items(self) -> int:
        return self._counters.error_items

    @property
    def skipped_items(self) -> int:
        return self._counters.skipped_items

    @property
    def total_duration_ms(self) -> float:
        return self._counters.total_duration_ms

    def run(
        self,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """遍历 `scan_root` 执行全流程；正常结束时返回库内聚合统计。

        `dry_run`：仍调用 `execute_decision` 预览路径，不做破坏性 I/O。
        `cancellation_event`：在每文件之间检查，置位后立即停止遍历并收尾统计。
        """
        try:
            self._log_handler_id = configure_task_logger(
                self.log_dir,
                self.run_name,
                self.run_id,
            )
            log_task_start(
                self.run_id,
                self.run_name,
                self.scan_root,
                dry_run,
            )

            for path, item_type in scan_directory_items(self.scan_root):
                if cancellation_event and cancellation_event.is_set():
                    log_task_cancelled(self.run_id, self.run_name)
                    break

                if item_type == PathEntryType.FILE:
                    process_single_file_for_run(
                        path,
                        dry_run,
                        run_id=self.run_id,
                        run_name=self.run_name,
                        analyze_config=self.analyze_config,
                        file_result_repository=self.file_result_repository,
                        counters=self._counters,
                    )
                else:
                    cleanup_empty_directory_under_scan(
                        path,
                        self.scan_root,
                        dry_run,
                        self.run_id,
                        self.run_name,
                    )

            return finish_task_with_repository_statistics(
                self.run_id,
                self.run_name,
                dry_run,
                self.file_result_repository,
            )

        except Exception as e:
            log_pipeline_execution_failed(self.run_id, self.run_name, e)
            raise
        finally:
            if self._log_handler_id is not None:
                remove_task_logger(self._log_handler_id)
