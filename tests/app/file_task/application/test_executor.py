"""文件执行器单元测试

覆盖 ExecutionResult 工厂方法、execute_decision dry_run 及实际执行。
"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.executor import (
    ExecutionResult,
    ExecutionStatus,
    execute_decision,
)
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.file_types import FileType
from j_file_kit.app.file_task.domain.serial_id import SerialId

pytestmark = pytest.mark.unit


def _make_move_decision(source: Path, target: Path) -> MoveDecision:
    return MoveDecision(
        source_path=source,
        target_path=target,
        file_type=FileType.VIDEO,
        serial_id=SerialId(prefix="ABC", number="123"),
    )


def _make_delete_decision(source: Path) -> DeleteDecision:
    return DeleteDecision(
        source_path=source,
        file_type=FileType.MISC,
        reason="测试删除",
    )


def _make_skip_decision(source: Path) -> SkipDecision:
    return SkipDecision(
        source_path=source,
        file_type=FileType.VIDEO,
        reason="测试跳过",
    )


class TestExecutionResultFactoryMethods:
    """ExecutionResult 工厂方法"""

    def test_success(self, tmp_path: Path) -> None:
        result = ExecutionResult.success(
            source_path=tmp_path / "a.mp4",
            target_path=tmp_path / "b.mp4",
            file_type=FileType.VIDEO,
        )
        assert result.status == ExecutionStatus.SUCCESS
        assert result.target_path == tmp_path / "b.mp4"

    def test_error(self, tmp_path: Path) -> None:
        result = ExecutionResult.error(
            source_path=tmp_path / "a.mp4",
            message="failed",
        )
        assert result.status == ExecutionStatus.ERROR
        assert result.target_path is None
        assert result.message == "failed"

    def test_skipped(self, tmp_path: Path) -> None:
        result = ExecutionResult.skipped(
            source_path=tmp_path / "a.mp4",
            message="skip",
        )
        assert result.status == ExecutionStatus.SKIPPED

    def test_preview_move(self, tmp_path: Path) -> None:
        decision = _make_move_decision(
            tmp_path / "a.mp4",
            tmp_path / "sorted" / "ABC-123 a.mp4",
        )
        result = ExecutionResult.preview(decision)
        assert result.status == ExecutionStatus.PREVIEW
        assert result.target_path == tmp_path / "sorted" / "ABC-123 a.mp4"
        assert "预览：移动到" in result.message

    def test_preview_delete(self, tmp_path: Path) -> None:
        decision = _make_delete_decision(tmp_path / "a.tmp")
        result = ExecutionResult.preview(decision)
        assert result.status == ExecutionStatus.PREVIEW
        assert "预览：删除" in result.message

    def test_preview_skip(self, tmp_path: Path) -> None:
        decision = _make_skip_decision(tmp_path / "a.mp4")
        result = ExecutionResult.preview(decision)
        assert result.status == ExecutionStatus.PREVIEW
        assert "预览：跳过" in result.message


class TestExecuteDecisionDryRun:
    """execute_decision dry_run 预览模式"""

    def test_move_preview(self, tmp_path: Path) -> None:
        decision = _make_move_decision(
            tmp_path / "a.mp4",
            tmp_path / "sorted" / "ABC-123 a.mp4",
        )
        result = execute_decision(decision, dry_run=True)
        assert result.status == ExecutionStatus.PREVIEW

    def test_delete_preview(self, tmp_path: Path) -> None:
        decision = _make_delete_decision(tmp_path / "a.tmp")
        result = execute_decision(decision, dry_run=True)
        assert result.status == ExecutionStatus.PREVIEW

    def test_skip_preview(self, tmp_path: Path) -> None:
        decision = _make_skip_decision(tmp_path / "a.mp4")
        result = execute_decision(decision, dry_run=True)
        assert result.status == ExecutionStatus.PREVIEW


class TestExecuteDecisionActualExecution:
    """execute_decision 实际执行（需 tmp_path）"""

    def test_skip_returns_skipped(self, tmp_path: Path) -> None:
        decision = _make_skip_decision(tmp_path / "a.mp4")
        result = execute_decision(decision, dry_run=False)
        assert result.status == ExecutionStatus.SKIPPED

    def test_move_success(self, tmp_path: Path) -> None:
        source = tmp_path / "a.mp4"
        source.write_text("content")
        target = tmp_path / "b" / "a.mp4"
        decision = _make_move_decision(source, target)
        result = execute_decision(decision, dry_run=False)
        assert result.status == ExecutionStatus.SUCCESS
        assert target.exists()
        assert not source.exists()

    def test_delete_success(self, tmp_path: Path) -> None:
        source = tmp_path / "a.tmp"
        source.write_text("content")
        decision = _make_delete_decision(source)
        result = execute_decision(decision, dry_run=False)
        assert result.status == ExecutionStatus.SUCCESS
        assert not source.exists()
