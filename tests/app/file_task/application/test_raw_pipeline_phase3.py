"""RawFilePipeline 阶段 3（files_misc 分流）单元测试。"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

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


def _ctx(tmp_path: Path, cfg: RawAnalyzeConfig) -> PhaseContext:
    return PhaseContext(
        run_id=1,
        run_name="raw_file_organizer",
        scan_root=tmp_path / "inbox",
        analyze_config=cfg,
        file_result_repository=MagicMock(),
    )


def test_phase3_moves_archive_image_audio(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    fp = tmp_path / "files_pic"
    fa = tmp_path / "files_audio"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=fp,
        files_audio=fa,
    )
    (misc / "a.zip").write_text("zip")
    (misc / "b.jpg").write_text("img")
    (misc / "c.mp3").write_text("snd")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_seen_files_misc == 3
    assert counters.phase3_deferred_files_misc == 0
    assert (fc / "a.zip").read_text() == "zip"
    assert (fp / "b.jpg").read_text() == "img"
    assert (fa / "c.mp3").read_text() == "snd"
    assert list(misc.iterdir()) == []


def test_phase3_defers_video_and_unknown(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "v.mp4").write_text("v")
    (misc / "u.txt").write_text("u")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_seen_files_misc == 2
    assert counters.phase3_deferred_files_misc == 2
    assert (misc / "v.mp4").exists()
    assert (misc / "u.txt").exists()


def test_phase3_conflict_resolution(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (fc / "dup.zip").write_text("old")
    (misc / "dup.zip").write_text("new")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    assert not (misc / "dup.zip").exists()
    in_fc = list(fc.glob("dup*.zip"))
    assert len(in_fc) == 2
    assert {p.read_text() for p in in_fc} == {"old", "new"}


def test_phase3_truncates_long_basename(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    long_name = "y" * 240 + ".zip"
    assert len(long_name.encode()) == 244
    (misc / long_name).write_text("x")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    moved = list(fc.iterdir())
    assert len(moved) == 1
    assert (
        len(moved[0].name.encode())
        <= MAX_FILENAME_BYTES - JFK_CONFLICT_STEM_SUFFIX_BYTES
    )


def test_phase3_raises_when_destination_missing(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=None,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "need_dest.zip").write_text("z")

    counters = RawPhaseCounters()
    with pytest.raises(ValueError, match="files_compressed"):
        run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)


def test_phase3_dry_run_does_not_move(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "a.zip").write_text("z")
    (misc / "b.mp4").write_text("v")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=True)

    assert counters.phase3_seen_files_misc == 2
    assert counters.phase3_deferred_files_misc == 1
    assert (misc / "a.zip").exists()
    assert (misc / "b.mp4").exists()
    assert list(fc.iterdir()) == []


def test_phase3_skips_when_misc_missing(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)
    assert counters.phase3_seen_files_misc == 0
    assert counters.phase3_deferred_files_misc == 0
