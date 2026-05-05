"""phase2_classify：拆解判定等纯逻辑单元测试。"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.phase2_classify import (
    should_flatten_small_dir,
)

pytestmark = pytest.mark.unit


def _cfg() -> RawAnalyzeConfig:
    return RawAnalyzeConfig(
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        subtitle_extensions={".srt"},
        archive_extensions={".zip"},
        audio_extensions={".mp3"},
    )


def test_should_flatten_single_video_type() -> None:
    files = [Path("a.mp4"), Path("b.mp4")]
    assert should_flatten_small_dir(files, _cfg()) is True


def test_should_flatten_video_plus_cover_jpg() -> None:
    files = [Path("a.mp4"), Path("cover.jpg")]
    assert should_flatten_small_dir(files, _cfg()) is True


def test_should_flatten_rejects_unknown_extension() -> None:
    files = [Path("a.mp4"), Path("b.xyz")]
    assert should_flatten_small_dir(files, _cfg()) is False


def test_should_flatten_rejects_too_many_files() -> None:
    files = [Path(f"{i}.mp4") for i in range(6)]
    assert should_flatten_small_dir(files, _cfg()) is False
