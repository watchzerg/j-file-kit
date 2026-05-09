"""organizer_defaults 产品常量单元测试"""

import pytest

from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_ARCHIVE_EXTENSIONS,
    DEFAULT_CAMELCASE_NO_SPLIT_WORDS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS,
    DEFAULT_JAV_VR_SERIAL_PREFIXES,
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
    DEFAULT_MUSIC_EXTENSIONS,
    DEFAULT_RAW_CLEANUP_JUNK_MAX_BYTES,
    DEFAULT_RAW_JUNK_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS,
    DEFAULT_SUBTITLE_EXTENSIONS,
    DEFAULT_VIDEO_EXTENSIONS,
    validate_organizer_extension_sets_disjoint,
)

pytestmark = pytest.mark.unit


def test_extension_sets_pairwise_disjoint() -> None:
    validate_organizer_extension_sets_disjoint()


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


# --- Raw 专属常量 ---


def test_raw_junk_keywords_nonempty_and_contains_known_entries() -> None:
    assert len(DEFAULT_RAW_JUNK_KEYWORDS) > 0
    # FC2-PPV 是 phase2.2 / phase3.0 的核心 junk 关键词
    assert "FC2-PPV" in DEFAULT_RAW_JUNK_KEYWORDS
    # 抽样若干中文广告壳关键词，作为防误删保护
    assert "手机网址" in DEFAULT_RAW_JUNK_KEYWORDS
    assert "扫码" in DEFAULT_RAW_JUNK_KEYWORDS


def test_raw_cleanup_junk_max_bytes_is_positive_int() -> None:
    # 默认 100 MiB；由 phase2 清洗阶段使用，必须为严格正整数
    assert isinstance(DEFAULT_RAW_CLEANUP_JUNK_MAX_BYTES, int)
    assert DEFAULT_RAW_CLEANUP_JUNK_MAX_BYTES == 100 * 1024 * 1024


def test_camelcase_no_split_words_contains_known_roots() -> None:
    # VR / TGirls 是 expand_keywords_camelcase 必须保留的不可拆词根
    assert "VR" in DEFAULT_CAMELCASE_NO_SPLIT_WORDS
    assert "TGirls" in DEFAULT_CAMELCASE_NO_SPLIT_WORDS


def test_jav_vr_serial_prefixes_nonempty_and_contains_known_prefixes() -> None:
    assert len(DEFAULT_JAV_VR_SERIAL_PREFIXES) > 0
    # 抽样若干常见 VR 番号前缀，作为防误删保护
    for prefix in ("JAVR", "DSVR", "KMVR", "WAVR", "MDVR"):
        assert prefix in DEFAULT_JAV_VR_SERIAL_PREFIXES


def test_raw_video_bucket_keywords_nonempty_and_first_entries_match() -> None:
    assert len(DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS) > 0
    # AMZN 是当前唯一的 movie 桶关键词，且必须保序排在第一位
    assert DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS[0] == "AMZN"

    assert len(DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS) > 0
    # LethalHardcoreVR 是 us_vr 桶的首位关键词（CamelCase 优先级最高）
    assert DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS[0] == "LethalHardcoreVR"

    assert len(DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS) > 0
    # HardcoreGangBang 在 us 桶中是较高优先级关键词
    assert "HardcoreGangBang" in DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS
