"""phase3 冲突命名与文件名长度限制测试。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.file_ops import (
    JFK_CONFLICT_STEM_SUFFIX_BYTES,
    MAX_FILENAME_BYTES,
)
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase3 import run_phase3

pytestmark = pytest.mark.unit


def test_archive_conflict_resolution(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    files_compressed = tmp_path / "files_compressed"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=files_compressed,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (files_compressed / "dup.zip").write_text("old")
    (misc / "dup.zip").write_text("new")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 0
    assert not (misc / "dup.zip").exists()
    moved = list(files_compressed.glob("dup*.zip"))
    assert len(moved) == 2
    assert {path.read_text() for path in moved} == {"old", "new"}


def test_archive_filename_truncation(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    files_compressed = tmp_path / "files_compressed"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=files_compressed,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    long_name = "y" * 240 + ".zip"
    assert len(long_name.encode()) == 244
    (misc / long_name).write_text("x")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    moved = list(files_compressed.iterdir())
    assert len(moved) == 1
    assert (
        len(moved[0].name.encode())
        <= MAX_FILENAME_BYTES - JFK_CONFLICT_STEM_SUFFIX_BYTES
    )


def test_video_bucket_conflict_resolution(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    files_video_misc = tmp_path / "files_video_misc"
    misc.mkdir()
    files_video_misc.mkdir(parents=True, exist_ok=True)
    (files_video_misc / "dup.mp4").write_text("old")
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
        files_video_misc=files_video_misc,
    )
    (misc / "dup.mp4").write_text("new")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    assert not (misc / "dup.mp4").exists()
    moved = list(files_video_misc.glob("dup*.mp4"))
    assert len(moved) == 2
    assert {path.read_text() for path in moved} == {"old", "new"}


def test_video_bucket_filename_truncation(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    files_video_misc = tmp_path / "files_video_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
        files_video_misc=files_video_misc,
    )
    long_name = "y" * 240 + ".mp4"
    assert len(long_name.encode()) == 244
    (misc / long_name).write_text("x")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    moved = list(files_video_misc.iterdir())
    assert len(moved) == 1
    assert (
        len(moved[0].name.encode())
        <= MAX_FILENAME_BYTES - JFK_CONFLICT_STEM_SUFFIX_BYTES
    )


def test_video_preclean_removes_junk_before_routing(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    files_to_delete = tmp_path / "files_to_delete"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
        files_to_delete=files_to_delete,
    )
    (misc / "junk_FC2-PPV.mp4").write_bytes(b"v")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 0
    assert list(misc.iterdir()) == []
    moved = list(files_to_delete.glob("*.mp4"))
    assert len(moved) == 1
    assert moved[0].read_bytes() == b"v"
