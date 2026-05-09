"""phase2_classify：拆解判定等纯逻辑单元测试。"""

import tempfile
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.config_common import raw_workspace_paths
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.phase2_classify import (
    should_flatten_small_dir,
)

pytestmark = pytest.mark.unit


def _cfg() -> RawAnalyzeConfig:
    p = raw_workspace_paths(Path(tempfile.gettempdir()) / "jfk-phase2-classify")
    return RawAnalyzeConfig(
        folders_to_delete=p.folders_to_delete,
        folders_video=p.folders_video,
        folders_compressed=p.folders_compressed,
        folders_pic=p.folders_pic,
        folders_audio=p.folders_audio,
        folders_misc=p.folders_misc,
        files_to_delete=p.files_to_delete,
        files_video_jav=p.files_video_jav,
        files_video_us=p.files_video_us,
        files_video_jav_vr=p.files_video_jav_vr,
        files_video_us_vr=p.files_video_us_vr,
        files_video_movie=p.files_video_movie,
        files_video_misc=p.files_video_misc,
        files_compressed=p.files_compressed,
        files_pic=p.files_pic,
        files_audio=p.files_audio,
        files_misc=p.files_misc,
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
