"""RawFilePipeline 阶段 1 与基础行为单元测试。"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.file_ops import (
    JFK_CONFLICT_STEM_SUFFIX_BYTES,
    MAX_FILENAME_BYTES,
)
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)

pytestmark = pytest.mark.unit


def _empty_repo_stats() -> dict[str, float | int]:
    return {
        "total_items": 0,
        "success_items": 0,
        "error_items": 0,
        "skipped_items": 0,
        "warning_items": 0,
        "total_duration_ms": 0.0,
    }


def test_run_empty_inbox_mock_repo(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    repo = MagicMock()
    repo.get_statistics.return_value = _empty_repo_stats()
    pipe = RawFilePipeline(
        run_id=1,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=raw_analyze_config_factory(
            tmp_path, files_misc=tmp_path / "misc"
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=repo,
    )
    stats = pipe.run()
    assert stats == FileTaskRunStatistics()
    repo.save_result.assert_not_called()


def test_phase1_moves_level1_file_only(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    sub = inbox / "nested"
    sub.mkdir()
    (sub / "inner.mp4").write_text("in")
    (inbox / "root.txt").write_text("root")

    pipe = RawFilePipeline(
        run_id=42,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=raw_analyze_config_factory(tmp_path, files_misc=misc),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert (misc / "root.txt").exists()
    assert (misc / "root.txt").read_text() == "root"
    assert not (inbox / "root.txt").exists()
    assert (misc / "nested_inner.mp4").exists()
    assert not sub.exists()

    assert stats.phase1_seen_files == 1
    assert stats.phase1_moved_files == 1
    assert stats.phase1_error_files == 0
    assert stats.phase2_seen_dirs == 1
    assert stats.phase2_flattened_dirs == 1
    assert stats.phase2_flattened_files == 1
    assert stats.phase2_moved_to_delete_dirs == 0
    assert stats.phase3_seen_files_misc == 2
    assert stats.phase3_deferred_files_misc == 2
    assert stats.total_items >= 1


def test_phase1_conflict_resolution(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    (misc / "dup.txt").write_text("old")
    (inbox / "dup.txt").write_text("new")

    pipe = RawFilePipeline(
        run_id=7,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=raw_analyze_config_factory(tmp_path, files_misc=misc),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert not (inbox / "dup.txt").exists()
    moved = list(misc.glob("dup*.txt"))
    assert len(moved) == 2
    contents = {p.read_text() for p in moved}
    assert contents == {"old", "new"}
    assert stats.phase1_moved_files == 1


def test_phase1_truncates_long_but_fs_valid_filename(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    long_name = "y" * 246 + ".dat"
    assert len(long_name.encode()) == 250
    (inbox / long_name).write_text("x")

    pipe = RawFilePipeline(
        run_id=3,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=raw_analyze_config_factory(tmp_path, files_misc=misc),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert stats.phase1_moved_files == 1
    remaining = list(misc.iterdir())
    assert len(remaining) == 1
    assert (
        len(remaining[0].name.encode())
        <= MAX_FILENAME_BYTES - JFK_CONFLICT_STEM_SUFFIX_BYTES
    )


def test_dry_run_does_not_move(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    (inbox / "keep.txt").write_text("data")

    pipe = RawFilePipeline(
        run_id=9,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=raw_analyze_config_factory(tmp_path, files_misc=misc),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run(dry_run=True)

    assert (inbox / "keep.txt").exists()
    assert list(misc.iterdir()) == []
    assert stats.phase1_moved_files == 1
    assert stats.success_items >= 1
