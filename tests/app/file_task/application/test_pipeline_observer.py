"""`PipelineRunCounters` 单元测试：与成功路径 ExecutionResult 累计口径一致。"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.executor import ExecutionResult
from j_file_kit.app.file_task.application.pipeline_observer import PipelineRunCounters
from j_file_kit.app.file_task.domain.decisions import MoveDecision
from j_file_kit.app.file_task.domain.file_types import FileType

pytestmark = pytest.mark.unit


class TestPipelineRunCounters:
    """成功 / 预览 / 错误 / 跳过与耗时累加。"""

    def test_success_increments_success_items(self, tmp_path: Path) -> None:
        counters = PipelineRunCounters()
        result = ExecutionResult.success(source_path=tmp_path / "a.mp4")
        counters.apply_execution_result(result, 1.0)
        assert counters.total_items == 1
        assert counters.success_items == 1
        assert counters.error_items == 0
        assert counters.skipped_items == 0

    def test_preview_increments_success_items(self, tmp_path: Path) -> None:
        counters = PipelineRunCounters()
        decision = MoveDecision(
            source_path=tmp_path / "a.mp4",
            target_path=tmp_path / "b" / "a.mp4",
            file_type=FileType.VIDEO,
            serial_id=None,
        )
        result = ExecutionResult.preview(decision)
        counters.apply_execution_result(result, 1.0)
        assert counters.success_items == 1

    def test_error_increments_error_items(self, tmp_path: Path) -> None:
        counters = PipelineRunCounters()
        result = ExecutionResult.error(
            source_path=tmp_path / "a.mp4",
            message="err",
        )
        counters.apply_execution_result(result, 1.0)
        assert counters.total_items == 1
        assert counters.error_items == 1

    def test_skipped_increments_skipped_items(self, tmp_path: Path) -> None:
        counters = PipelineRunCounters()
        result = ExecutionResult.skipped(
            source_path=tmp_path / "a.mp4",
            message="skip",
        )
        counters.apply_execution_result(result, 1.0)
        assert counters.skipped_items == 1

    def test_total_duration_accumulated(self, tmp_path: Path) -> None:
        counters = PipelineRunCounters()
        result = ExecutionResult.success(source_path=tmp_path / "a.mp4")
        counters.apply_execution_result(result, 10.0)
        counters.apply_execution_result(result, 20.0)
        assert counters.total_duration_ms == 30.0

    def test_exception_path_does_not_increment_total_items(
        self,
        tmp_path: Path,
    ) -> None:
        """抛错路径只计 error 与耗时，与 `FilePipeline` 旧语义一致。"""
        counters = PipelineRunCounters()
        counters.record_file_processing_exception(5.0)
        assert counters.total_items == 0
        assert counters.error_items == 1
        assert counters.total_duration_ms == 5.0
