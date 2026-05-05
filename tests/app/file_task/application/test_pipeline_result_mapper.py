"""`build_file_item_data` 单元测试：Decision + ExecutionResult → FileItemData 口径。"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.executor import ExecutionResult
from j_file_kit.app.file_task.application.pipeline_result_mapper import (
    build_file_item_data,
)
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    FileItemData,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.file_types import FileType
from j_file_kit.app.file_task.domain.serial_id import SerialId

pytestmark = pytest.mark.unit


class TestBuildFileItemData:
    """覆盖 move/delete/skip 与 success、preview、error 判定。"""

    def test_move_decision_success(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "ABC-123.mp4"
        decision = MoveDecision(
            source_path=path,
            target_path=tmp_path / "sorted" / "ABC-123.mp4",
            file_type=FileType.VIDEO,
            serial_id=SerialId(prefix="ABC", number="123"),
        )
        result = ExecutionResult.success(
            source_path=path,
            target_path=tmp_path / "sorted" / "ABC-123.mp4",
            file_type=FileType.VIDEO,
            serial_id=SerialId(prefix="ABC", number="123"),
        )
        item = build_file_item_data(path, decision, result, 10.5)
        assert isinstance(item, FileItemData)
        assert item.decision_type == "move"
        assert item.target_path == tmp_path / "sorted" / "ABC-123.mp4"
        assert item.success is True
        assert item.duration_ms == 10.5

    def test_move_decision_preview(self, tmp_path: Path) -> None:
        path = tmp_path / "a.mp4"
        decision = MoveDecision(
            source_path=path,
            target_path=tmp_path / "out" / "a.mp4",
            file_type=FileType.VIDEO,
            serial_id=None,
        )
        result = ExecutionResult.preview(decision)
        item = build_file_item_data(path, decision, result, 1.0)
        assert item.success is True
        assert item.decision_type == "move"

    def test_delete_decision_success(self, tmp_path: Path) -> None:
        path = tmp_path / "a.tmp"
        decision = DeleteDecision(
            source_path=path,
            file_type=FileType.MISC,
            reason="test",
        )
        result = ExecutionResult.success(
            source_path=path,
            file_type=FileType.MISC,
            message="删除成功",
        )
        item = build_file_item_data(path, decision, result, 5.0)
        assert item.decision_type == "delete"
        assert item.target_path is None
        assert item.success is True

    def test_skip_decision(self, tmp_path: Path) -> None:
        path = tmp_path / "a.mp4"
        decision = SkipDecision(
            source_path=path,
            file_type=FileType.VIDEO,
            reason="skip",
        )
        result = ExecutionResult.skipped(
            source_path=path,
            file_type=FileType.VIDEO,
            message="skip",
        )
        item = build_file_item_data(path, decision, result, 0.1)
        assert item.decision_type == "skip"
        assert item.success is True
        assert item.target_path is None

    def test_move_decision_error(self, tmp_path: Path) -> None:
        path = tmp_path / "a.mp4"
        decision = MoveDecision(
            source_path=path,
            target_path=tmp_path / "out" / "a.mp4",
            file_type=FileType.VIDEO,
            serial_id=None,
        )
        result = ExecutionResult.error(
            source_path=path,
            file_type=FileType.VIDEO,
            message="move failed",
        )
        item = build_file_item_data(path, decision, result, 2.0)
        assert item.success is False
        assert item.error_message == "move failed"
