"""phase3 路由行为测试：按文件类型分流。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase3 import run_phase3

pytestmark = pytest.mark.unit


def test_moves_archive_image_audio(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    files_compressed = tmp_path / "files_compressed"
    files_pic = tmp_path / "files_pic"
    files_audio = tmp_path / "files_audio"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=files_compressed,
        files_pic=files_pic,
        files_audio=files_audio,
    )
    (misc / "a.zip").write_text("zip")
    (misc / "b.jpg").write_text("img")
    (misc / "c.mp3").write_text("snd")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_seen_files_misc == 3
    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 0
    assert (files_compressed / "a.zip").read_text() == "zip"
    assert (files_pic / "b.jpg").read_text() == "img"
    assert (files_audio / "c.mp3").read_text() == "snd"
    assert list(misc.iterdir()) == []


def test_routes_video_and_defers_unknown_non_video(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "v.mp4").write_text("v")
    (misc / "u.txt").write_text("u")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_seen_files_misc == 2
    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 1
    assert (tmp_path / "files_video_misc" / "v.mp4").read_text() == "v"
    assert (misc / "u.txt").exists()


def test_dry_run_keeps_files_in_misc(
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
    (misc / "a.zip").write_text("z")
    (misc / "b.mp4").write_text("v")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=True)

    assert counters.phase3_seen_files_misc == 2
    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 0
    assert (misc / "a.zip").exists()
    assert (misc / "b.mp4").exists()
    assert list(files_compressed.iterdir()) == []


def test_skips_when_misc_missing(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=tmp_path / "files_misc",
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)
    assert counters.phase3_seen_files_misc == 0
    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 0
