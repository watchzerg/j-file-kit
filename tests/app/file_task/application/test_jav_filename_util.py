from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.jav_filename_util import (
    generate_jav_filename,
    generate_sorted_dir,
)
from j_file_kit.app.file_task.domain.models import SerialId

pytestmark = pytest.mark.unit


def test_generate_jav_filename_serial_at_start() -> None:
    filename, serial_id = generate_jav_filename("ABC-001_video.mp4")

    assert filename == "ABC-001 video.mp4"
    assert serial_id == SerialId(prefix="ABC", number="001")


def test_generate_jav_filename_serial_not_at_start() -> None:
    filename, serial_id = generate_jav_filename("video_ABC-001_hd.mp4")

    assert filename == "ABC-001 video-serialId-hd.mp4"
    assert serial_id == SerialId(prefix="ABC", number="001")


def test_generate_jav_filename_without_serial_keeps_original() -> None:
    filename, serial_id = generate_jav_filename("no_serial.mp4")

    assert filename == "no_serial.mp4"
    assert serial_id is None


def test_generate_sorted_dir_uses_prefix_hierarchy() -> None:
    serial_id = SerialId(prefix="ABCD", number="123")

    assert generate_sorted_dir(serial_id) == Path("A/AB/ABCD")
