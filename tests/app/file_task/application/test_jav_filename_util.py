"""JAV 文件名工具单元测试

覆盖 generate_jav_filename、generate_sorted_dir。
"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.jav_filename_util import (
    generate_jav_filename,
    generate_sorted_dir,
)
from j_file_kit.app.file_task.domain.models import SerialId

pytestmark = pytest.mark.unit


class TestGenerateJavFilename:
    """generate_jav_filename 文件名重构"""

    def test_serial_at_start_with_part3(self) -> None:
        new_name, serial_id = generate_jav_filename("ABC-001_video.mp4")
        assert new_name == "ABC-001 video.mp4"
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"

    def test_serial_at_start_part3_empty(self) -> None:
        new_name, serial_id = generate_jav_filename("ABC-001.mp4")
        assert new_name == "ABC-001.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_part3_empty(self) -> None:
        new_name, serial_id = generate_jav_filename("prefix_ABC-001.mp4")
        assert new_name == "ABC-001 prefix-serialId.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_with_part3(self) -> None:
        new_name, serial_id = generate_jav_filename("video_ABC-001_hd.mp4")
        assert new_name == "ABC-001 video-serialId-hd.mp4"
        assert serial_id is not None

    def test_no_serial_returns_original(self) -> None:
        new_name, serial_id = generate_jav_filename("no_serial_here.mp4")
        assert new_name == "no_serial_here.mp4"
        assert serial_id is None

    def test_trim_separators(self) -> None:
        new_name, _ = generate_jav_filename("  -  ABC-001  -  suffix  .mp4")
        assert "ABC-001" in new_name
        assert new_name.startswith("ABC-001")

    def test_underscore_separator(self) -> None:
        new_name, serial_id = generate_jav_filename("ABC_123.mp4")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"
        assert new_name == "ABC-123.mp4"

    def test_lowercase_serial_normalized(self) -> None:
        new_name, serial_id = generate_jav_filename("abc-123.mp4")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert new_name == "ABC-123.mp4"


class TestGenerateSortedDir:
    """generate_sorted_dir 子目录路径生成"""

    def test_four_letter_prefix(self) -> None:
        sid = SerialId(prefix="ABCD", number="123")
        result = generate_sorted_dir(sid)
        assert result == Path("A/AB/ABCD")

    def test_three_letter_prefix(self) -> None:
        sid = SerialId(prefix="XYZ", number="456")
        result = generate_sorted_dir(sid)
        assert result == Path("X/XY/XYZ")

    def test_two_letter_prefix(self) -> None:
        sid = SerialId(prefix="AB", number="789")
        result = generate_sorted_dir(sid)
        assert result == Path("A/AB/AB")

    def test_five_letter_prefix(self) -> None:
        sid = SerialId(prefix="ABCDE", number="00001")
        result = generate_sorted_dir(sid)
        assert result == Path("A/AB/ABCDE")
