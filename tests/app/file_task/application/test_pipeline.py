"""文件处理管道单元测试

覆盖 FilePipeline._create_item_data、_update_statistics。
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.config import JavAnalyzeConfig
from j_file_kit.app.file_task.application.executor import (
    ExecutionResult,
)
from j_file_kit.app.file_task.application.pipeline import FilePipeline
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    FileItemData,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.models import FileType, SerialId

pytestmark = pytest.mark.unit


@pytest.fixture
def pipeline(tmp_path: Path) -> FilePipeline:
    config = JavAnalyzeConfig(
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        subtitle_extensions={".srt"},
        archive_extensions={".zip"},
    )
    return FilePipeline(
        run_id=1,
        run_name="test",
        scan_root=tmp_path,
        analyze_config=config,
        log_dir=tmp_path,
        file_result_repository=MagicMock(),
    )


class TestPipelineCreateItemData:
    """FilePipeline._create_item_data"""

    def test_move_decision_success(
        self,
        pipeline: FilePipeline,
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
        item = pipeline._create_item_data(path, decision, result, 10.5)
        assert isinstance(item, FileItemData)
        assert item.decision_type == "move"
        assert item.target_path == tmp_path / "sorted" / "ABC-123.mp4"
        assert item.success is True
        assert item.duration_ms == 10.5

    def test_move_decision_preview(
        self,
        pipeline: FilePipeline,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "a.mp4"
        decision = MoveDecision(
            source_path=path,
            target_path=tmp_path / "out" / "a.mp4",
            file_type=FileType.VIDEO,
            serial_id=None,
        )
        result = ExecutionResult.preview(decision)
        item = pipeline._create_item_data(path, decision, result, 1.0)
        assert item.success is True
        assert item.decision_type == "move"

    def test_delete_decision_success(
        self,
        pipeline: FilePipeline,
        tmp_path: Path,
    ) -> None:
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
        item = pipeline._create_item_data(path, decision, result, 5.0)
        assert item.decision_type == "delete"
        assert item.target_path is None
        assert item.success is True

    def test_skip_decision(self, pipeline: FilePipeline, tmp_path: Path) -> None:
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
        item = pipeline._create_item_data(path, decision, result, 0.1)
        assert item.decision_type == "skip"
        assert item.success is True
        assert item.target_path is None

    def test_move_decision_error(self, pipeline: FilePipeline, tmp_path: Path) -> None:
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
        item = pipeline._create_item_data(path, decision, result, 2.0)
        assert item.success is False
        assert item.error_message == "move failed"


class TestPipelineUpdateStatistics:
    """FilePipeline._update_statistics"""

    def test_success_increments_success_items(
        self,
        pipeline: FilePipeline,
        tmp_path: Path,
    ) -> None:
        result = ExecutionResult.success(source_path=tmp_path / "a.mp4")
        pipeline._update_statistics(result, 1.0)
        assert pipeline.total_items == 1
        assert pipeline.success_items == 1
        assert pipeline.error_items == 0
        assert pipeline.skipped_items == 0

    def test_preview_increments_success_items(
        self,
        pipeline: FilePipeline,
        tmp_path: Path,
    ) -> None:
        decision = MoveDecision(
            source_path=tmp_path / "a.mp4",
            target_path=tmp_path / "b" / "a.mp4",
            file_type=FileType.VIDEO,
            serial_id=None,
        )
        result = ExecutionResult.preview(decision)
        pipeline._update_statistics(result, 1.0)
        assert pipeline.success_items == 1

    def test_error_increments_error_items(
        self,
        pipeline: FilePipeline,
        tmp_path: Path,
    ) -> None:
        result = ExecutionResult.error(
            source_path=tmp_path / "a.mp4",
            message="err",
        )
        pipeline._update_statistics(result, 1.0)
        assert pipeline.total_items == 1
        assert pipeline.error_items == 1

    def test_skipped_increments_skipped_items(
        self,
        pipeline: FilePipeline,
        tmp_path: Path,
    ) -> None:
        result = ExecutionResult.skipped(
            source_path=tmp_path / "a.mp4",
            message="skip",
        )
        pipeline._update_statistics(result, 1.0)
        assert pipeline.skipped_items == 1

    def test_total_duration_accumulated(
        self,
        pipeline: FilePipeline,
        tmp_path: Path,
    ) -> None:
        result = ExecutionResult.success(source_path=tmp_path / "a.mp4")
        pipeline._update_statistics(result, 10.0)
        pipeline._update_statistics(result, 20.0)
        assert pipeline.total_duration_ms == 30.0
