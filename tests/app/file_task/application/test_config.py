from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.config import (
    JavVideoOrganizeConfig,
    create_default_jav_video_organizer_task_config,
)

pytestmark = pytest.mark.unit


def test_jav_video_organize_config_normalizes_extensions() -> None:
    config = JavVideoOrganizeConfig(
        video_extensions={"mp4", ".mkv"},
        image_extensions={"jpg", ".png"},
        archive_extensions={"zip", ".7z"},
    )

    assert config.video_extensions == {".mp4", ".mkv"}
    assert config.image_extensions == {".jpg", ".png"}
    assert config.archive_extensions == {".zip", ".7z"}


def test_jav_video_organize_config_directory_fields_default_to_none() -> None:
    config = JavVideoOrganizeConfig(
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        archive_extensions={".zip"},
    )

    assert config.inbox_dir is None
    assert config.sorted_dir is None
    assert config.unsorted_dir is None
    assert config.archive_dir is None
    assert config.misc_dir is None


def test_jav_video_organize_config_accepts_directory_paths() -> None:
    config = JavVideoOrganizeConfig(
        inbox_dir=Path("/inbox"),
        sorted_dir=Path("/sorted"),
        unsorted_dir=Path("/unsorted"),
        archive_dir=Path("/archive"),
        misc_dir=Path("/misc"),
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        archive_extensions={".zip"},
    )

    assert config.inbox_dir == Path("/inbox")
    assert config.sorted_dir == Path("/sorted")


def test_default_task_config_includes_directory_fields() -> None:
    task_config = create_default_jav_video_organizer_task_config()

    assert task_config.config["inbox_dir"] is None
    assert task_config.config["sorted_dir"] is None
    assert task_config.config["unsorted_dir"] is None
    assert task_config.config["archive_dir"] is None
    assert task_config.config["misc_dir"] is None
    assert "video_extensions" in task_config.config
