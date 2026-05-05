"""RawFilePipeline 阶段 2 单链折叠行为测试（经 pipeline.run 驱动）。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)

pytestmark = pytest.mark.unit


def test_phase2_collapses_single_chain_directory(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    root = inbox / "abc"
    root.mkdir()
    (root / "def").mkdir()
    (root / "def" / "ghi").mkdir()
    (root / "def" / "ghi" / "clip.mp4").write_text("vid")

    pipe = RawFilePipeline(
        run_id=101,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=raw_analyze_config_factory(
            tmp_path, files_misc=misc, folders_to_delete=td
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert (misc / "abc_def_ghi_clip.mp4").exists()
    assert not (inbox / "abc_def_ghi").exists()
    assert not root.exists()
    assert stats.phase2_collapsed_chain_dirs == 1
    assert stats.phase2_skipped_collapse_dirs == 0
    assert stats.phase2_flattened_dirs == 1
    assert stats.phase2_flattened_files == 1


def test_phase2_collapse_renames_on_destination_conflict(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    (inbox / "abc_def_ghi").mkdir()

    root = inbox / "abc"
    root.mkdir()
    (root / "def").mkdir()
    (root / "def" / "ghi").mkdir()
    (root / "def" / "ghi" / "clip.mp4").write_text("vid")

    pipe = RawFilePipeline(
        run_id=102,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=raw_analyze_config_factory(
            tmp_path, files_misc=misc, folders_to_delete=td
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert stats.phase2_collapsed_chain_dirs == 1
    assert stats.phase2_skipped_collapse_dirs == 0
    assert stats.phase2_flattened_dirs == 1
    dest_files = [p for p in misc.iterdir() if p.is_file()]
    assert len(dest_files) == 1
    assert dest_files[0].suffix == ".mp4"
    assert "-jfk-" in dest_files[0].stem or dest_files[0].stem.startswith("abc_def_ghi")
    assert dest_files[0].read_text() == "vid"
    assert not root.exists()


def test_phase2_collapse_skips_when_merge_budget_impossible(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()

    name_seg = "n" * 9
    root = inbox / name_seg
    root.mkdir()
    cur = root
    for _ in range(34):
        nxt = cur / name_seg
        nxt.mkdir()
        cur = nxt
    (cur / "z.mp4").write_text("p")

    pipe = RawFilePipeline(
        run_id=103,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=raw_analyze_config_factory(
            tmp_path, files_misc=misc, folders_to_delete=td
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert stats.phase2_collapsed_chain_dirs == 0
    assert stats.phase2_skipped_collapse_dirs == 1
    assert not root.exists()
    assert stats.phase2_moved_to_video_dirs == 1
    fv = tmp_path / "folders_video"
    moved_roots = list(fv.iterdir())
    assert len(moved_roots) == 1
    assert list(moved_roots[0].rglob("z.mp4"))


def test_phase2_collapse_dry_run_counts_only(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    root = inbox / "abc"
    root.mkdir()
    (root / "def").mkdir()
    (root / "def" / "ghi").mkdir()
    (root / "def" / "ghi" / "clip.mp4").write_text("vid")

    pipe = RawFilePipeline(
        run_id=104,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=raw_analyze_config_factory(
            tmp_path, files_misc=misc, folders_to_delete=td
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run(dry_run=True)

    assert root.exists()
    assert (root / "def" / "ghi" / "clip.mp4").exists()
    assert stats.phase2_collapsed_chain_dirs == 1
    assert stats.phase2_moved_to_video_dirs == 1
