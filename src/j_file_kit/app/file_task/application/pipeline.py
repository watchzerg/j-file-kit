"""文件处理管道：在给定 `scan_root` 下的通用「扫描 → 分析 → 执行 → 落库」实现。

`JavVideoOrganizer` 将收件箱目录与 `JavAnalyzeConfig` 注入本类；本模块调用 `analyze_jav_file`、
`execute_decision`，并把每条 `FileItemData` 写入 `FileResultRepository`。不承载任务类型的业务含义。
"""

import threading
import time
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.executor import (
    ExecutionResult,
    ExecutionStatus,
    execute_decision,
)
from j_file_kit.app.file_task.application.file_ops import scan_directory_items
from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.application.jav_analyzer import analyze_jav_file
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    FileDecision,
    FileItemData,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.file_types import PathEntryType
from j_file_kit.app.file_task.domain.ports import FileResultRepository
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics
from j_file_kit.shared.utils.file_utils import (
    delete_directory_if_empty,
    sanitize_surrogate_str,
)
from j_file_kit.shared.utils.logging import (
    configure_task_logger,
    remove_task_logger,
)


class FilePipeline:
    """针对某一 `scan_root` 的流式处理管道（与具体任务名解耦，由调用方传入 `run_name`）。

    核心流程：
        1. `_start_task`：挂接本 run 专用日志文件，打 TASK_START；若 `dry_run` 打预览标记。
        2. 深度优先遍历 `scan_root`（`scan_directory_items`）：遇文件走 `_process_file`，遇目录走
           `_cleanup_empty_directory`；循环中检查 `cancellation_event` 可提前跳出。
        3. `_process_file`：`analyze_jav_file` → `execute_decision`（尊重 `dry_run`）→ `save_result`；
           异常时仍写入一条 `decision_type=error` 的结果。内存侧 `_update_statistics` 与日志
           `_log_file_result` 同步更新。
        4. `_finish_task`：调用 `get_statistics` 拉取库内聚合，校验为 `FileTaskRunStatistics` 并打 TASK_END。
        5. `finally`：移除本 run 的 log handler。

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

        # 统计信息
        self.total_items = 0
        self.success_items = 0
        self.error_items = 0
        self.skipped_items = 0
        self.total_duration_ms = 0.0

        # 日志 handler
        self._log_handler_id: int | None = None

    def run(
        self,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """遍历 `scan_root` 执行全流程；正常结束时返回库内聚合统计，取消或异常时仍尽量清理日志 handler。

        `dry_run`：执行路径仍调用 `execute_decision`，由 executor 产生预览态结果而不做破坏性 I/O。
        `cancellation_event`：在每文件之间检查，置位后立即停止遍历并返回当前已处理结果统计（通过 `_finish_task`）。
        """
        try:
            self._start_task(dry_run)

            for path, item_type in scan_directory_items(self.scan_root):
                if cancellation_event and cancellation_event.is_set():
                    logger.bind(
                        run_id=str(self.run_id),
                        run_name=self.run_name,
                    ).info("任务已被取消")
                    break

                if item_type == PathEntryType.FILE:
                    self._process_file(path, dry_run)
                else:
                    self._cleanup_empty_directory(path, dry_run)

            return self._finish_task(dry_run)

        except Exception as e:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).error(f"管道执行失败: {e!s}")
            raise
        finally:
            if self._log_handler_id is not None:
                remove_task_logger(self._log_handler_id)

    def _start_task(self, dry_run: bool) -> None:
        """注册按 run 隔离的 loguru sink，并写 TASK_START / dry_run 提示。"""
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
            return

    def _finish_task(self, dry_run: bool) -> FileTaskRunStatistics:
        """从仓储读取聚合计数，写 TASK_END 日志，并把 dict 校验为 `FileTaskRunStatistics` 返回给调用链。

        终态统计以 `FileResultRepository.get_statistics` 为准。
        """
        stats = self.file_result_repository.get_statistics(self.run_id)

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="TASK_END",
            total_items=stats.get("total_items", 0),
            success_items=stats.get("success_items", 0),
            error_items=stats.get("error_items", 0),
            skipped_items=stats.get("skipped_items", 0),
        ).info(f"任务完成: {self.run_name}")

        if dry_run:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info("预览模式执行完成")
        return FileTaskRunStatistics.model_validate(stats)

    def _process_file(self, path: Path, dry_run: bool) -> None:
        """单文件 happy path：`analyze_jav_file` → `execute_decision` → 持久化 → 内存统计 → 结构化日志。

        任一环节抛错：记录 error 级日志，写入 `decision_type=error` 的 `FileItemData`，并计入 `error_items`，
        不中断整轮扫描（与成功路径一致的「每文件一封」模型）。
        """
        start_time = time.time()

        try:
            decision = analyze_jav_file(path, self.analyze_config)

            result = execute_decision(
                decision,
                dry_run=dry_run,
            )

            duration_ms = (time.time() - start_time) * 1000

            item_data = self._create_item_data(path, decision, result, duration_ms)
            self.file_result_repository.save_result(self.run_id, item_data)

            self._update_statistics(result, duration_ms)

            self._log_file_result(path, decision, result, duration_ms)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            safe_path = sanitize_surrogate_str(str(path))
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
                error=str(e),
            ).error(f"处理文件失败: {safe_path}")

            error_data = FileItemData(
                path=path,
                stem=path.stem,
                file_type=None,
                serial_id=None,
                decision_type="error",
                target_path=None,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
            )
            self.file_result_repository.save_result(self.run_id, error_data)
            self.error_items += 1
            self.total_duration_ms += duration_ms

    def _create_item_data(
        self,
        path: Path,
        decision: FileDecision,
        result: ExecutionResult,
        duration_ms: float,
    ) -> FileItemData:
        """把领域 `FileDecision` 与执行层 `ExecutionResult` 压平为可入库的 `FileItemData`（三态分支匹配）。

        成功判定：`SUCCESS` 或 `PREVIEW` 视为该步达成预期；`ERROR` 携带 `result.message`。
        """
        match decision:
            case MoveDecision():
                return FileItemData(
                    path=path,
                    stem=path.stem,
                    file_type=decision.file_type,
                    serial_id=decision.serial_id,
                    decision_type="move",
                    target_path=result.target_path,
                    success=result.status == ExecutionStatus.SUCCESS
                    or result.status == ExecutionStatus.PREVIEW,
                    error_message=result.message
                    if result.status == ExecutionStatus.ERROR
                    else None,
                    duration_ms=duration_ms,
                )
            case DeleteDecision():
                return FileItemData(
                    path=path,
                    stem=path.stem,
                    file_type=decision.file_type,
                    serial_id=None,
                    decision_type="delete",
                    target_path=None,
                    success=result.status == ExecutionStatus.SUCCESS
                    or result.status == ExecutionStatus.PREVIEW,
                    error_message=result.message
                    if result.status == ExecutionStatus.ERROR
                    else None,
                    duration_ms=duration_ms,
                )
            case SkipDecision():
                return FileItemData(
                    path=path,
                    stem=path.stem,
                    file_type=decision.file_type,
                    serial_id=None,
                    decision_type="skip",
                    target_path=None,
                    success=True,
                    error_message=None,
                    duration_ms=duration_ms,
                )

    def _update_statistics(self, result: ExecutionResult, duration_ms: float) -> None:
        """按本条文件执行结果更新管道内累计计数与耗时（与仓储统计独立，用于日志/观测）。"""
        self.total_items += 1
        self.total_duration_ms += duration_ms

        match result.status:
            case ExecutionStatus.SUCCESS | ExecutionStatus.PREVIEW:
                self.success_items += 1
            case ExecutionStatus.ERROR:
                self.error_items += 1
            case ExecutionStatus.SKIPPED:
                self.skipped_items += 1

    def _log_file_result(
        self,
        path: Path,
        decision: FileDecision,
        result: ExecutionResult,
        duration_ms: float,
    ) -> None:
        """写 ITEM_RESULT 级结构化日志；对 `MoveDecision` 附带来源类型、番号与目标路径。"""
        item_data: dict[str, str | float | None] = {
            "file_path": sanitize_surrogate_str(str(path)),
            "decision_type": decision.decision_type,
            "status": result.status.value,
            "duration_ms": duration_ms,
        }

        if isinstance(decision, MoveDecision):
            item_data["file_type"] = (
                decision.file_type.value if decision.file_type else None
            )
            item_data["serial_id"] = (
                str(decision.serial_id) if decision.serial_id else None
            )
            item_data["target_path"] = (
                str(result.target_path) if result.target_path else None
            )

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="ITEM_RESULT",
            **item_data,
        ).info(f"处理文件: {sanitize_surrogate_str(path.name)}")

    def _cleanup_empty_directory(self, path: Path, dry_run: bool) -> None:
        """后序遍历到的目录：在非 dry_run 且无子内容时尝试删除，但不删除 `scan_root` 本身。

        用于文件搬走或删除后收缩空文件夹；失败静默（由 `delete_directory_if_empty` 决定）。
        """
        if dry_run:
            return

        if path.resolve() == self.scan_root.resolve():
            return

        if delete_directory_if_empty(path):
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info(f"清理空目录: {sanitize_surrogate_str(str(path))}")
