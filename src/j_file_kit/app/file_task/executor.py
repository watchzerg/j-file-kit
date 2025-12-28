"""文件执行函数

提供文件操作执行函数，根据 Decision 执行相应操作。
支持 dry_run 预览模式。

设计意图：
- 根据 Decision 类型执行对应操作
- 支持 dry_run 预览：返回预览结果而不实际执行
- 记录操作日志到 Repository
"""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from j_file_kit.app.file_task.decisions import (
    DeleteDecision,
    FileDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain import FileType, OperationType, SerialId
from j_file_kit.app.file_task.ports import FileProcessorRepository
from j_file_kit.infrastructure.filesystem.operations import (
    create_directory,
    delete_file,
    move_file_with_conflict_resolution,
)


class ExecutionStatus(str, Enum):
    """执行状态枚举"""

    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    PREVIEW = "preview"


class ExecutionResult(BaseModel):
    """执行结果

    记录文件操作的执行结果，包括状态、路径变化等信息。
    """

    status: ExecutionStatus = Field(..., description="执行状态")
    source_path: Path = Field(..., description="源文件路径")
    target_path: Path | None = Field(None, description="目标文件路径（移动操作时有值）")
    file_type: FileType | None = Field(None, description="文件类型")
    serial_id: SerialId | None = Field(None, description="番号")
    message: str = Field("", description="执行消息")

    @classmethod
    def success(
        cls,
        source_path: Path,
        target_path: Path | None = None,
        file_type: FileType | None = None,
        serial_id: SerialId | None = None,
        message: str = "",
    ) -> ExecutionResult:
        """创建成功结果"""
        return cls(
            status=ExecutionStatus.SUCCESS,
            source_path=source_path,
            target_path=target_path,
            file_type=file_type,
            serial_id=serial_id,
            message=message,
        )

    @classmethod
    def error(
        cls,
        source_path: Path,
        file_type: FileType | None = None,
        message: str = "",
    ) -> ExecutionResult:
        """创建错误结果"""
        return cls(
            status=ExecutionStatus.ERROR,
            source_path=source_path,
            target_path=None,
            file_type=file_type,
            serial_id=None,
            message=message,
        )

    @classmethod
    def skipped(
        cls,
        source_path: Path,
        file_type: FileType | None = None,
        message: str = "",
    ) -> ExecutionResult:
        """创建跳过结果"""
        return cls(
            status=ExecutionStatus.SKIPPED,
            source_path=source_path,
            target_path=None,
            file_type=file_type,
            serial_id=None,
            message=message,
        )

    @classmethod
    def preview(
        cls,
        decision: FileDecision,
    ) -> ExecutionResult:
        """创建预览结果（dry_run 模式）"""
        match decision:
            case MoveDecision():
                return cls(
                    status=ExecutionStatus.PREVIEW,
                    source_path=decision.source_path,
                    target_path=decision.target_path,
                    file_type=decision.file_type,
                    serial_id=decision.serial_id,
                    message=f"预览：移动到 {decision.target_path}",
                )
            case DeleteDecision():
                return cls(
                    status=ExecutionStatus.PREVIEW,
                    source_path=decision.source_path,
                    target_path=None,
                    file_type=decision.file_type,
                    serial_id=None,
                    message=f"预览：删除（{decision.reason}）",
                )
            case SkipDecision():
                return cls(
                    status=ExecutionStatus.PREVIEW,
                    source_path=decision.source_path,
                    target_path=None,
                    file_type=decision.file_type,
                    serial_id=None,
                    message=f"预览：跳过（{decision.reason}）",
                )


def execute_decision(
    decision: FileDecision,
    dry_run: bool = False,
    file_processor_repository: FileProcessorRepository | None = None,
) -> ExecutionResult:
    """执行文件操作决策

    设计意图：根据 Decision 类型执行对应操作，支持 dry_run 预览。

    Args:
        decision: 文件处理决策
        dry_run: 是否为预览模式
        file_processor_repository: 文件处理操作仓储（用于记录操作日志）

    Returns:
        执行结果
    """
    if dry_run:
        return ExecutionResult.preview(decision)

    match decision:
        case MoveDecision():
            return _execute_move(decision, file_processor_repository)
        case DeleteDecision():
            return _execute_delete(decision, file_processor_repository)
        case SkipDecision():
            return ExecutionResult.skipped(
                source_path=decision.source_path,
                file_type=decision.file_type,
                message=decision.reason,
            )


def _execute_move(
    decision: MoveDecision,
    file_processor_repository: FileProcessorRepository | None,
) -> ExecutionResult:
    """执行移动操作

    Args:
        decision: 移动决策
        file_processor_repository: 文件处理操作仓储

    Returns:
        执行结果
    """
    try:
        # 创建目标目录
        create_directory(decision.target_path.parent, parents=True)

        # 执行移动（自动处理路径冲突）
        final_path = move_file_with_conflict_resolution(
            decision.source_path,
            decision.target_path,
        )

        # 记录操作日志
        if file_processor_repository:
            file_processor_repository.create_operation(
                OperationType.MOVE,
                decision.source_path,
                final_path,
                file_type=decision.file_type.value if decision.file_type else None,
                serial_id=str(decision.serial_id) if decision.serial_id else None,
            )

        return ExecutionResult.success(
            source_path=decision.source_path,
            target_path=final_path,
            file_type=decision.file_type,
            serial_id=decision.serial_id,
            message=f"移动到 {final_path}",
        )

    except Exception as e:
        return ExecutionResult.error(
            source_path=decision.source_path,
            file_type=decision.file_type,
            message=f"移动失败: {e!s}",
        )


def _execute_delete(
    decision: DeleteDecision,
    file_processor_repository: FileProcessorRepository | None,
) -> ExecutionResult:
    """执行删除操作

    Args:
        decision: 删除决策
        file_processor_repository: 文件处理操作仓储

    Returns:
        执行结果
    """
    try:
        # 执行删除
        delete_file(decision.source_path)

        # 记录操作日志
        if file_processor_repository:
            file_processor_repository.create_operation(
                OperationType.DELETE,
                decision.source_path,
                None,
                file_type=decision.file_type.value if decision.file_type else None,
            )

        return ExecutionResult.success(
            source_path=decision.source_path,
            file_type=decision.file_type,
            message=f"删除成功（{decision.reason}）",
        )

    except Exception as e:
        return ExecutionResult.error(
            source_path=decision.source_path,
            file_type=decision.file_type,
            message=f"删除失败: {e!s}",
        )

