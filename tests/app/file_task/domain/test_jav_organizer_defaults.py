"""jav_organizer_defaults 产品常量单元测试"""

import pytest

from j_file_kit.app.file_task.domain.jav_organizer_defaults import (
    DEFAULT_ARCHIVE_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS,
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
    DEFAULT_MUSIC_EXTENSIONS,
    DEFAULT_SUBTITLE_EXTENSIONS,
    DEFAULT_VIDEO_EXTENSIONS,
)

pytestmark = pytest.mark.unit


def test_all_extension_sets_nonempty_and_dotted() -> None:
    for name, ext_set in (
        ("video", DEFAULT_VIDEO_EXTENSIONS),
        ("image", DEFAULT_IMAGE_EXTENSIONS),
        ("subtitle", DEFAULT_SUBTITLE_EXTENSIONS),
        ("archive", DEFAULT_ARCHIVE_EXTENSIONS),
        ("music", DEFAULT_MUSIC_EXTENSIONS),
        ("misc_delete", DEFAULT_MISC_FILE_DELETE_EXTENSIONS),
    ):
        assert len(ext_set) > 0, name
        assert all(e.startswith(".") for e in ext_set), name


def test_known_legacy_entries_present() -> None:
    """抽样断言：与迁移前默认列表对齐的关键项（防止误删大半集合）。"""
    assert ".mp4" in DEFAULT_VIDEO_EXTENSIONS
    assert ".m2ts" in DEFAULT_VIDEO_EXTENSIONS
    assert ".tmp" in DEFAULT_MISC_FILE_DELETE_EXTENSIONS
    assert ".xltd" in DEFAULT_MISC_FILE_DELETE_EXTENSIONS
    assert "BBS-2048" in DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS
    assert "CCTV-12306" in DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS
    assert len(DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS) == 10


def test_music_extensions_include_requested_formats() -> None:
    for ext in (
        ".flac",
        ".ape",
        ".mp3",
        ".m4b",
        ".m4a",
        ".fxp",
        ".mka",
        ".cue",
        ".m3u",
    ):
        assert ext in DEFAULT_MUSIC_EXTENSIONS
