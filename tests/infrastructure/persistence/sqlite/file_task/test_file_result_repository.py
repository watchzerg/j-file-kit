"""文件处理结果仓储集成测试"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.domain.decisions import FileItemData
from j_file_kit.app.file_task.domain.models import FileType, SerialId
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def file_result_repository(
    sqlite_connection_manager: SQLiteConnectionManager,
) -> FileResultRepositoryImpl:
    return FileResultRepositoryImpl(sqlite_connection_manager)


class TestFileResultRepositorySaveAndGetStatistics:
    """save_result 与 get_statistics"""

    def test_save_and_get_statistics(
        self,
        file_result_repository: FileResultRepositoryImpl,
        tmp_path: Path,
    ) -> None:
        result = FileItemData(
            path=tmp_path / "ABC-123.mp4",
            stem="ABC-123",
            file_type=FileType.VIDEO,
            serial_id=SerialId(prefix="ABC", number="123"),
            decision_type="move",
            target_path=tmp_path / "sorted" / "ABC-123.mp4",
            success=True,
            error_message=None,
            duration_ms=10.5,
        )
        row_id = file_result_repository.save_result(run_id=1, result=result)
        assert row_id > 0
        stats = file_result_repository.get_statistics(1)
        assert stats["total_items"] == 1
        assert stats["success_items"] == 1
        assert stats["error_items"] == 0
        assert stats["skipped_items"] == 0
        assert stats["total_duration_ms"] == 10.5

    def test_get_statistics_empty_run(
        self,
        file_result_repository: FileResultRepositoryImpl,
    ) -> None:
        stats = file_result_repository.get_statistics(999)
        assert stats["total_items"] == 0
        assert stats["success_items"] == 0
        assert stats["total_duration_ms"] == 0.0

    def test_save_result_with_surrogate_path_does_not_raise(
        self,
        file_result_repository: FileResultRepositoryImpl,
        tmp_path: Path,
    ) -> None:
        surrogate_path = tmp_path / "+\udcfe\udca6.jpg"
        result = FileItemData(
            path=surrogate_path,
            stem=surrogate_path.stem,
            file_type=FileType.IMAGE,
            serial_id=None,
            decision_type="move",
            target_path=None,
            success=False,
            error_message="test error",
            duration_ms=1.0,
        )
        row_id = file_result_repository.save_result(run_id=1, result=result)
        assert row_id > 0
        stats = file_result_repository.get_statistics(1)
        assert stats["total_items"] == 1

    def test_multiple_results_aggregated(
        self,
        file_result_repository: FileResultRepositoryImpl,
        tmp_path: Path,
    ) -> None:
        for i in range(3):
            file_result_repository.save_result(
                run_id=2,
                result=FileItemData(
                    path=tmp_path / f"f{i}.mp4",
                    stem=f"f{i}",
                    file_type=FileType.VIDEO,
                    serial_id=None,
                    decision_type="move",
                    target_path=tmp_path / "out" / f"f{i}.mp4",
                    success=True,
                    error_message=None,
                    duration_ms=5.0,
                ),
            )
        stats = file_result_repository.get_statistics(2)
        assert stats["total_items"] == 3
        assert stats["success_items"] == 3
        assert stats["total_duration_ms"] == 15.0
