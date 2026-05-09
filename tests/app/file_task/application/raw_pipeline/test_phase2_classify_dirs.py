"""phase2 目录级分类行为测试。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline

pytestmark = pytest.mark.unit


def test_flatten_skipped_when_more_than_five_files(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    source_dir = inbox / "sixpack"
    source_dir.mkdir(parents=True)
    for idx in range(6):
        (source_dir / f"{idx}.mp4").write_text("x")

    stats = raw_pipeline_factory(run_id=202).run()

    assert stats.phase2_flattened_dirs == 0
    assert stats.phase2_moved_to_video_dirs == 1
    folders_video = tmp_path / "folders_video"
    assert len(list(folders_video.iterdir())) == 1


def test_whole_nested_image_dir_moved_to_pic(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    album = inbox / "vacation"
    album.mkdir(parents=True)
    (album / "a.jpg").write_text("a")
    (album / "deep").mkdir()
    (album / "deep" / "x.jpg").write_text("p")

    stats = raw_pipeline_factory(run_id=204).run()

    assert stats.phase2_moved_to_pic_dirs == 1
    pic_root = tmp_path / "folders_pic" / "vacation"
    assert pic_root.is_dir()
    assert (pic_root / "deep" / "x.jpg").exists()
