"""jav_defaults JAV 专属常量单元测试。"""

import pytest

from j_file_kit.app.file_task.domain.jav_defaults import (
    DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS,
    DEFAULT_JAV_VR_SERIAL_PREFIXES,
)

pytestmark = pytest.mark.unit


def test_jav_vr_serial_prefixes_nonempty_and_contains_known_prefixes() -> None:
    assert len(DEFAULT_JAV_VR_SERIAL_PREFIXES) > 0
    # 抽样若干常见 VR 番号前缀，作为防误删保护
    for prefix in ("JAVR", "DSVR", "KMVR", "WAVR", "MDVR"):
        assert prefix in DEFAULT_JAV_VR_SERIAL_PREFIXES


def test_jav_filename_strip_substrings_known_entries() -> None:
    assert "BBS-2048" in DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS
    assert "CCTV-12306" in DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS
    assert len(DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS) == 10
