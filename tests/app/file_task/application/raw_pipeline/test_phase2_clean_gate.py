"""Raw 阶段 2.2：目录体积门禁与 ``sum_regular_file_sizes_under`` 单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.file_ops import sum_regular_file_sizes_under
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase2_clean import (
    clean_level1_dir,
)
from j_file_kit.app.file_task.application.raw_pipeline.phase2_preflight import (
    build_phase2_normalized_keywords,
)
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_RAW_SMALL_BATCH_MAX_BYTES,
)

pytestmark = pytest.mark.unit


def _ctx(scan_root: Path) -> PhaseContext:
    """``clean_level1_dir`` 仅需 ``ctx`` 打日志字段；占位配置即可。"""
    return PhaseContext(
        run_id=1,
        run_name="raw_file_organizer",
        scan_root=scan_root,
        analyze_config=MagicMock(),
        file_result_repository=MagicMock(),
    )


def test_sum_regular_file_sizes_under_includes_nested_files(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    (root / "a").write_bytes(b"ab")
    sub = root / "s"
    sub.mkdir()
    (sub / "b").write_bytes(b"cde")
    assert sum_regular_file_sizes_under(root) == 5


def test_clean_skips_all_file_deletes_when_tree_ge_threshold(tmp_path: Path) -> None:
    _, junk_norm = build_phase2_normalized_keywords()
    root = tmp_path / "d"
    root.mkdir()
    (root / "pad.bin").write_bytes(b"x" * DEFAULT_RAW_SMALL_BATCH_MAX_BYTES)
    (root / "keep_FC2-PPV.txt").write_text("junk")

    phases = RawPhaseCounters()
    clean_level1_dir(
        _ctx(tmp_path / "scan"),
        root,
        phases,
        junk_keywords_norm=junk_norm,
        dry_run=False,
        cancellation_event=None,
    )
    assert phases.phase2_cleaned_deleted_files == 0
    assert (root / "keep_FC2-PPV.txt").exists()


def test_clean_deletes_junk_when_tree_below_threshold(tmp_path: Path) -> None:
    _, junk_norm = build_phase2_normalized_keywords()
    root = tmp_path / "d"
    root.mkdir()
    (root / "drop_FC2-PPV.txt").write_text("x")

    phases = RawPhaseCounters()
    clean_level1_dir(
        _ctx(tmp_path / "scan"),
        root,
        phases,
        junk_keywords_norm=junk_norm,
        dry_run=False,
        cancellation_event=None,
    )
    assert phases.phase2_cleaned_deleted_files == 1
    assert not (root / "drop_FC2-PPV.txt").exists()
