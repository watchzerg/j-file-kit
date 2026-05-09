"""phase2 扁平化行为测试。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline

pytestmark = pytest.mark.unit


def test_clean_keeps_non_junk_then_flattens_small_video_dir(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    source_dir = inbox / "keep_dir"
    source_dir.mkdir(parents=True)
    (source_dir / "video.mp4").write_text("full")
    (source_dir / "junk.txt").write_text("bye")

    stats = raw_pipeline_factory(run_id=44).run()

    assert not source_dir.exists()
    files_video_misc = tmp_path / "files_video_misc"
    assert (files_video_misc / "keep_dir_video.mp4").exists()
    assert stats.phase2_cleaned_deleted_files == 1
    assert stats.phase2_flattened_dirs == 1
    assert stats.phase2_flattened_files == 1
    assert stats.phase2_removed_dirs == 1


def test_flatten_video_plus_cover_jpg(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    release_dir = inbox / "release"
    release_dir.mkdir(parents=True)
    (release_dir / "cover.jpg").write_text("img")
    (release_dir / "main.mp4").write_text("vid")

    stats = raw_pipeline_factory(run_id=201).run()

    assert not release_dir.exists()
    files_pic = tmp_path / "files_pic"
    files_video_misc = tmp_path / "files_video_misc"
    assert (files_pic / "release_cover.jpg").read_text() == "img"
    assert (files_video_misc / "release_main.mp4").read_text() == "vid"
    assert stats.phase2_flattened_dirs == 1
    assert stats.phase2_flattened_files == 2


def test_flatten_preserves_name_when_stem_matches_dir(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    source_dir = inbox / "episode"
    source_dir.mkdir(parents=True)
    (source_dir / "episode.mp4").write_text("z")

    stats = raw_pipeline_factory(run_id=203).run()

    files_video_misc = tmp_path / "files_video_misc"
    assert (files_video_misc / "episode.mp4").exists()
    assert stats.phase2_flattened_files == 1
