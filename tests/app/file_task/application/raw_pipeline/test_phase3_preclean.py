"""phase3 预清理行为测试：junk stem 优先迁移 files_to_delete。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase3 import run_phase3

pytestmark = pytest.mark.unit


def test_preclean_moves_junk_then_routes_archive(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    files_compressed = tmp_path / "files_compressed"
    files_to_delete = tmp_path / "files_to_delete"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=files_compressed,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
        files_to_delete=files_to_delete,
    )
    (misc / "ad_FC2-PPV.txt").write_text("junk")
    (misc / "a.zip").write_text("z")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 1
    assert (files_compressed / "a.zip").read_text() == "z"
    assert not (misc / "ad_FC2-PPV.txt").exists()
    moved = list(files_to_delete.glob("*.txt"))
    assert len(moved) == 1
    assert moved[0].read_text() == "junk"


def test_preclean_moves_large_junk_file(
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
    source = misc / "big_FC2-PPV.bin"
    source.write_bytes(b"z" * (1024 * 1024 + 1))

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 0
    assert not source.exists()
    moved = list(files_to_delete.glob("*.bin"))
    assert len(moved) == 1
    assert moved[0].stat().st_size == 1024 * 1024 + 1


def test_only_junk_archive_does_not_require_compressed_target(
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
        files_to_delete=files_to_delete,
    )
    (misc / "junk_FC2-PPV.zip").write_bytes(b"x")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 0
    assert list(misc.iterdir()) == []
    assert (files_to_delete / "junk_FC2-PPV.zip").read_bytes() == b"x"


def test_dry_run_preclean_only_counts_without_unlink(
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
    source = misc / "promo_FC2-PPV.jpg"
    source.write_text("pic")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=True)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 0
    assert counters.phase3_deferred_files_misc == 0
    assert source.exists()
