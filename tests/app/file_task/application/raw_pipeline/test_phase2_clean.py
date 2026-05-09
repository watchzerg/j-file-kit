"""phase2 清理行为测试。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline

pytestmark = pytest.mark.unit


def test_clean_deletes_junk_and_removes_empty_root(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    source_dir = inbox / "junk_root"
    source_dir.mkdir(parents=True)
    (source_dir / "note.txt").write_text("rm")
    (source_dir / "preview_FC2-PPV.mp4").write_text("junk stem")
    (source_dir / "zero.mp4").write_bytes(b"")

    stats = raw_pipeline_factory(run_id=33).run()

    assert not source_dir.exists()
    assert stats.phase2_cleaned_deleted_files >= 3
    assert stats.phase2_removed_dirs == 1


def test_clean_keeps_large_junk_stem_file(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "j_file_kit.app.file_task.domain.organizer_defaults.DEFAULT_RAW_CLEANUP_JUNK_MAX_BYTES",
        50,
    )
    inbox = tmp_path / "inbox"
    source_dir = inbox / "big_junk"
    source_dir.mkdir(parents=True)
    (source_dir / "big_FC2-PPV.bin").write_bytes(b"x" * 50)
    (source_dir / "small_FC2-PPV.bin").write_bytes(b"x" * 49)

    stats = raw_pipeline_factory(run_id=77).run()

    big_paths = list(tmp_path.rglob("big_FC2-PPV.bin"))
    assert len(big_paths) == 1
    assert big_paths[0].stat().st_size == 50
    assert not list(tmp_path.rglob("small_FC2-PPV.bin"))
    assert stats.phase2_cleaned_deleted_files == 1


def test_dry_run_counts_without_deleting_contents(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    source_dir = inbox / "trash"
    source_dir.mkdir(parents=True)
    (source_dir / "x.txt").write_text("stay")

    stats = raw_pipeline_factory(run_id=66).run(dry_run=True)

    assert (source_dir / "x.txt").exists()
    assert stats.phase2_cleaned_deleted_files == 1
    assert stats.phase2_moved_to_misc_dirs == 1
