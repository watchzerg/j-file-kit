"""JAV 管道入参映射：将领域 `FileDecision` 与执行层 `ExecutionResult` 压平为 `FileItemData`。

纯函数，无副作用（不读盘、不写日志、不触库）。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.jav_pipeline.executor import (
    ExecutionResult,
    ExecutionStatus,
)
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    FileDecision,
    FileItemData,
    MoveDecision,
    SkipDecision,
)


def build_file_item_data(
    path: Path,
    decision: FileDecision,
    result: ExecutionResult,
    duration_ms: float,
) -> FileItemData:
    """折叠 Decision 与执行结果为可入库行。

    成功口径：`SUCCESS` 与 `PREVIEW` 计为达成预期；`ERROR` 写入 `error_message=result.message`。
    `SkipDecision` 路径固定 `success=True`（与执行器返回的 SKIPPED 并存档一致）。
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
