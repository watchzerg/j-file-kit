"""phase2 删除目录迁移行为测试。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline

pytestmark = pytest.mark.unit


def test_keyword_moves_dir_to_folders_to_delete(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    folders_to_delete = tmp_path / "folders_to_delete"
    source_dir = inbox / "something-FC2-PPV-xyz"
    source_dir.mkdir(parents=True)
    (source_dir / "kept.mp4").write_text("vid")

    stats = raw_pipeline_factory(run_id=11).run()

    assert not source_dir.exists()
    moved_dirs = [path for path in folders_to_delete.iterdir() if path.is_dir()]
    assert len(moved_dirs) == 1
    assert (moved_dirs[0] / "kept.mp4").read_text() == "vid"
    assert stats.phase2_moved_to_delete_dirs == 1
    assert stats.phase2_removed_dirs == 0


def test_keyword_match_is_case_insensitive(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    source_dir = inbox / "fc2-ppv-pack"
    source_dir.mkdir(parents=True)
    (source_dir / "a.txt").write_text("x")

    stats = raw_pipeline_factory(run_id=22).run()

    assert stats.phase2_moved_to_delete_dirs == 1
    assert not source_dir.exists()
