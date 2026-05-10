"""raw_defaults Raw 专属常量单元测试。"""

import pytest

from j_file_kit.app.file_task.domain.raw_defaults import (
    DEFAULT_RAW_CLEANUP_JUNK_MAX_BYTES,
    DEFAULT_RAW_JUNK_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS,
)

pytestmark = pytest.mark.unit


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
