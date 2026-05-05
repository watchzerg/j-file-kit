"""Raw 管道阶段 1：inbox 第一层文件迁入 `files_misc`。

与仓库根目录 `docs/RAW_FILE_PROCESSING_PIPELINE.md` 中阶段 1 一致；
每文件一条 `FileItemData` 落库，与 JAV `FilePipeline` 的「每文件一封」模型对齐。
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
from j_file_kit.app.file_task.application.file_ops import normalize_move_basename
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.domain.decisions import FileItemData, MoveDecision
from j_file_kit.app.file_task.domain.file_types import FileType
from j_file_kit.shared.utils.file_utils import sanitize_surrogate_str


def _list_inbox_level1_files(scan_root: Path) -> list[Path]:
    """第一层普通文件，确定性排序；与旧 `RawFilePipeline.list_inbox_level1_files` 前置条件一致。"""
    if not scan_root.exists():
        raise FileNotFoundError(f"扫描目录不存在: {scan_root}")
    if not scan_root.is_dir():
        raise NotADirectoryError(f"路径不是目录: {scan_root}")
    return sorted(p for p in scan_root.iterdir() if p.is_file())


def _item_data_from_move(
    path: Path,
    decision: MoveDecision,
    result: ExecutionResult,
    duration_ms: float,
) -> FileItemData:
    """折叠 Move + ExecutionResult 为入库模型。"""
    success = result.status in (
        ExecutionStatus.SUCCESS,
        ExecutionStatus.PREVIEW,
    )
    err_msg = result.message if result.status == ExecutionStatus.ERROR else None
    return FileItemData(
        path=path,
        stem=path.stem,
        file_type=decision.file_type,
        serial_id=decision.serial_id,
        decision_type="move",
        target_path=result.target_path,
        success=success,
        error_message=err_msg,
        duration_ms=duration_ms,
    )


def run_phase1(
    ctx: PhaseContext,
    counters: RawPhaseCounters,
    *,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """阶段 1：收件箱第一层文件 -> `files_misc`；返回 True 表示已请求取消。"""
    dest = ctx.analyze_config.files_misc
    level1_files = _list_inbox_level1_files(ctx.scan_root)
    counters.phase1_seen_files = len(level1_files)

    if dest is None:
        if level1_files:
            raise ValueError("files_misc 未设置")
        return False

    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=1,
    ).info(f"阶段1：处理 inbox 第一层文件 {len(level1_files)} 个")

    for path in level1_files:
        if cancellation_event and cancellation_event.is_set():
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
            ).info("任务已被取消（阶段1）")
            return True

        start_time = time.time()
        try:
            basename = normalize_move_basename(sanitize_surrogate_str(path.name))
            target = dest / basename
            decision = MoveDecision(
                source_path=path,
                target_path=target,
                file_type=FileType.MISC,
                serial_id=None,
            )
            result = execute_decision(decision, dry_run=dry_run)
            duration_ms = (time.time() - start_time) * 1000

            item = _item_data_from_move(path, decision, result, duration_ms)
            ctx.file_result_repository.save_result(ctx.run_id, item)

            if result.status in (
                ExecutionStatus.SUCCESS,
                ExecutionStatus.PREVIEW,
            ):
                counters.phase1_moved_files += 1
            elif result.status == ExecutionStatus.ERROR:
                counters.phase1_error_files += 1

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            safe_path = sanitize_surrogate_str(str(path))
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                error=str(e),
            ).error(f"阶段1 处理文件失败: {safe_path}")
            error_data = FileItemData(
                path=path,
                stem=path.stem,
                file_type=FileType.MISC,
                serial_id=None,
                decision_type="error",
                target_path=None,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
            )
            ctx.file_result_repository.save_result(ctx.run_id, error_data)
            counters.phase1_error_files += 1

    return False
