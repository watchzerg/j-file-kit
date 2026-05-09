"""raw_analyze_config 纯函数单元测试。"""

import tempfile
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.config_common import raw_workspace_paths
from j_file_kit.app.file_task.application.raw_analyze_config import (
    RawAnalyzeConfig,
    classify_file_media_kind,
)

pytestmark = pytest.mark.unit


def _cfg() -> RawAnalyzeConfig:
    """构造一份只用于 ``classify_file_media_kind`` 的最小配置。

    路径字段必填但当前函数不读取，统一用临时目录占位即可。
    """
    p = raw_workspace_paths(Path(tempfile.gettempdir()) / "jfk-classify-kind")
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
        video_extensions={".mp4", ".mkv", ".m2ts"},
        image_extensions={".jpg", ".jpeg", ".png"},
        subtitle_extensions={".srt", ".ass"},
        archive_extensions={".zip", ".rar"},
        audio_extensions={".mp3", ".flac"},
    )


@pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png"])
def test_classify_image(ext: str) -> None:
    assert classify_file_media_kind(ext, _cfg()) == "image"


@pytest.mark.parametrize("ext", [".mp4", ".mkv", ".m2ts"])
def test_classify_video(ext: str) -> None:
    assert classify_file_media_kind(ext, _cfg()) == "video"


@pytest.mark.parametrize("ext", [".mp3", ".flac"])
def test_classify_audio(ext: str) -> None:
    assert classify_file_media_kind(ext, _cfg()) == "audio"


@pytest.mark.parametrize("ext", [".zip", ".rar"])
def test_classify_archive(ext: str) -> None:
    assert classify_file_media_kind(ext, _cfg()) == "archive"


@pytest.mark.parametrize("ext", [".srt", ".ass"])
def test_classify_subtitle(ext: str) -> None:
    assert classify_file_media_kind(ext, _cfg()) == "subtitle"


@pytest.mark.parametrize("ext", [".txt", ".xyz", ".unknown", ""])
def test_classify_unknown_returns_none(ext: str) -> None:
    assert classify_file_media_kind(ext, _cfg()) is None


@pytest.mark.parametrize(
    ("ext", "expected"),
    [
        (".MP4", "video"),
        (".JPG", "image"),
        (".SRT", "subtitle"),
        (".ZIP", "archive"),
        (".MP3", "audio"),
    ],
)
def test_classify_case_insensitive(ext: str, expected: str) -> None:
    assert classify_file_media_kind(ext, _cfg()) == expected
