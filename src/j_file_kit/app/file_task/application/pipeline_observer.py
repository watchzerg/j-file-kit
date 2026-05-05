"""JAV `FilePipeline` 的观测侧：结构化日志与内存侧累计计数。

不负责业务决策与 I/O 执行；仅记录任务边界、逐文件结果，并维护与仓储聚合无关的内存统计
（供日志/排障；终态汇总仍以 `FileResultRepository.get_statistics` 为准）。
"""

from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.executor import (
    ExecutionResult,
    ExecutionStatus,
)
from j_file_kit.app.file_task.domain.decisions import FileDecision, MoveDecision
from j_file_kit.app.file_task.domain.ports import FileResultRepository
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics
from j_file_kit.shared.utils.file_utils import sanitize_surrogate_str


@dataclass
class PipelineRunCounters:
    """单次 run 在内存中累计的逐文件统计（与 SQLite 聚合并行存在）。"""

    total_items: int = 0
    success_items: int = 0
    error_items: int = 0
    skipped_items: int = 0
    total_duration_ms: float = field(default=0.0)

    def apply_execution_result(
        self,
        result: ExecutionResult,
        duration_ms: float,
    ) -> None:
        """按单文件「分析 → 执行」未抛异常时的执行结果更新计数（含 SUCCESS / PREVIEW / ERROR / SKIPPED）。"""
        self.total_items += 1
        self.total_duration_ms += duration_ms
        match result.status:
            case ExecutionStatus.SUCCESS | ExecutionStatus.PREVIEW:
                self.success_items += 1
            case ExecutionStatus.ERROR:
                self.error_items += 1
            case ExecutionStatus.SKIPPED:
                self.skipped_items += 1

    def record_file_processing_exception(
        self,
        duration_ms: float,
    ) -> None:
        """单文件处理抛异常时：计入 error 与耗时，不增加 total_items（与旧实现一致）。"""
        self.error_items += 1
        self.total_duration_ms += duration_ms


def log_item_result(
    run_id: int,
    run_name: str,
    path: Path,
    decision: FileDecision,
    result: ExecutionResult,
    duration_ms: float,
) -> None:
    """写 ITEM_RESULT 级结构化日志；对 `MoveDecision` 附带类型、番号与目标路径。"""
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
        item_data["serial_id"] = str(decision.serial_id) if decision.serial_id else None
        item_data["target_path"] = (
            str(result.target_path) if result.target_path else None
        )

    logger.bind(
        run_id=str(run_id),
        run_name=run_name,
        level="ITEM_RESULT",
        **item_data,
    ).info(f"处理文件: {sanitize_surrogate_str(path.name)}")


def log_file_processing_error(
    run_id: int,
    run_name: str,
    path: Path,
    error: BaseException,
) -> None:
    """单文件处理失败时的 error 级日志。"""
    safe_path = sanitize_surrogate_str(str(path))
    logger.bind(
        run_id=str(run_id),
        run_name=run_name,
        error=str(error),
    ).error(f"处理文件失败: {safe_path}")


def log_task_start(
    run_id: int,
    run_name: str,
    scan_root: Path | None,
    dry_run: bool,
) -> None:
    """注册 sink 之后写入 TASK_START；`dry_run` 时追加预览模式提示。"""
    scan_root_str = str(scan_root) if scan_root else "未设置"
    logger.bind(
        run_id=str(run_id),
        run_name=run_name,
        scan_root=scan_root_str,
        level="TASK_START",
    ).info(f"开始任务: {run_name}")

    if dry_run:
        logger.bind(
            run_id=str(run_id),
            run_name=run_name,
        ).info("运行在预览模式（dry_run）")


def log_task_cancelled(run_id: int, run_name: str) -> None:
    """取消事件置位后跳出扫描循环时写入。"""
    logger.bind(
        run_id=str(run_id),
        run_name=run_name,
    ).info("任务已被取消")


def finish_task_with_repository_statistics(
    run_id: int,
    run_name: str,
    dry_run: bool,
    file_result_repository: FileResultRepository,
) -> FileTaskRunStatistics:
    """从仓储读取聚合计数，写 TASK_END / 预览完成提示，返回校验后的统计模型。"""
    stats = file_result_repository.get_statistics(run_id)

    logger.bind(
        run_id=str(run_id),
        run_name=run_name,
        level="TASK_END",
        total_items=stats.get("total_items", 0),
        success_items=stats.get("success_items", 0),
        error_items=stats.get("error_items", 0),
        skipped_items=stats.get("skipped_items", 0),
    ).info(f"任务完成: {run_name}")

    if dry_run:
        logger.bind(
            run_id=str(run_id),
            run_name=run_name,
        ).info("预览模式执行完成")
    return FileTaskRunStatistics.model_validate(stats)


def log_pipeline_execution_failed(
    run_id: int,
    run_name: str,
    error: BaseException,
) -> None:
    """管道主循环外层的捕获：记录后由调用方重新抛出。"""
    logger.bind(
        run_id=str(run_id),
        run_name=run_name,
    ).error(f"管道执行失败: {error!s}")
