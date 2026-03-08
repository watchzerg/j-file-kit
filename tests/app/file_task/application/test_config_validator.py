from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.config_validator import (
    check_dir_conflicts,
    validate_inbox_dir,
    validate_jav_video_organizer_config,
)

pytestmark = pytest.mark.unit


def _config(
    *,
    inbox_dir: Path | None = None,
    sorted_dir: Path | None = None,
    unsorted_dir: Path | None = None,
    archive_dir: Path | None = None,
    misc_dir: Path | None = None,
) -> JavVideoOrganizeConfig:
    return JavVideoOrganizeConfig(
        inbox_dir=inbox_dir,
        sorted_dir=sorted_dir,
        unsorted_dir=unsorted_dir,
        archive_dir=archive_dir,
        misc_dir=misc_dir,
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        archive_extensions={".zip"},
    )


def test_validate_inbox_dir_missing_returns_error() -> None:
    errors = validate_inbox_dir(_config())

    assert errors == ["待处理目录（inbox_dir）未设置"]


def test_validate_inbox_dir_present_returns_empty(tmp_path: Path) -> None:
    errors = validate_inbox_dir(_config(inbox_dir=tmp_path / "inbox"))

    assert errors == []


def test_check_dir_conflicts_same_path(tmp_path: Path) -> None:
    shared_path = tmp_path / "same"
    config = _config(inbox_dir=shared_path, sorted_dir=shared_path)

    errors = check_dir_conflicts(config)

    assert errors
    assert "inbox_dir" in errors[0]
    assert "sorted_dir" in errors[0]


def test_check_dir_conflicts_parent_child(tmp_path: Path) -> None:
    parent_dir = tmp_path / "parent"
    child_dir = parent_dir / "child"
    config = _config(inbox_dir=parent_dir, sorted_dir=child_dir)

    errors = check_dir_conflicts(config)

    assert errors
    assert "父目录" in errors[0]


def test_check_dir_conflicts_no_conflict(tmp_path: Path) -> None:
    config = _config(
        inbox_dir=tmp_path / "inbox",
        sorted_dir=tmp_path / "sorted",
        unsorted_dir=tmp_path / "unsorted",
    )

    errors = check_dir_conflicts(config)

    assert errors == []


def test_validate_jav_video_organizer_config_combines_rules() -> None:
    errors = validate_jav_video_organizer_config(_config())

    assert errors == ["待处理目录（inbox_dir）未设置"]


def test_validate_jav_video_organizer_config_passes_when_valid(tmp_path: Path) -> None:
    config = _config(inbox_dir=tmp_path / "inbox")

    errors = validate_jav_video_organizer_config(config)

    assert errors == []
