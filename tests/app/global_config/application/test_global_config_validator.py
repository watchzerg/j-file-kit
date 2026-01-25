from pathlib import Path

import pytest

from j_file_kit.app.global_config.application.global_config_validator import (
    check_dir_conflicts,
    validate_global_config,
    validate_inbox_dir,
)
from j_file_kit.app.global_config.domain.models import GlobalConfig

pytestmark = pytest.mark.unit


def _global_config(
    *,
    inbox_dir: Path | None = None,
    sorted_dir: Path | None = None,
    unsorted_dir: Path | None = None,
    archive_dir: Path | None = None,
    misc_dir: Path | None = None,
    starred_dir: Path | None = None,
) -> GlobalConfig:
    return GlobalConfig(
        inbox_dir=inbox_dir,
        sorted_dir=sorted_dir,
        unsorted_dir=unsorted_dir,
        archive_dir=archive_dir,
        misc_dir=misc_dir,
        starred_dir=starred_dir,
    )


def test_validate_inbox_dir_missing_returns_error() -> None:
    errors = validate_inbox_dir(_global_config())

    assert errors == ["待处理目录（inbox_dir）未设置"]


def test_validate_inbox_dir_present_returns_empty(tmp_path: Path) -> None:
    errors = validate_inbox_dir(_global_config(inbox_dir=tmp_path / "inbox"))

    assert errors == []


def test_check_dir_conflicts_same_path(tmp_path: Path) -> None:
    shared_path = tmp_path / "same"
    global_config = _global_config(inbox_dir=shared_path, sorted_dir=shared_path)

    errors = check_dir_conflicts(global_config)

    assert errors
    assert "inbox_dir" in errors[0]
    assert "sorted_dir" in errors[0]


def test_check_dir_conflicts_parent_child(tmp_path: Path) -> None:
    parent_dir = tmp_path / "parent"
    child_dir = parent_dir / "child"
    global_config = _global_config(inbox_dir=parent_dir, sorted_dir=child_dir)

    errors = check_dir_conflicts(global_config)

    assert errors
    assert "父目录" in errors[0]


def test_validate_global_config_combines_rules() -> None:
    errors = validate_global_config(_global_config())

    assert errors == ["待处理目录（inbox_dir）未设置"]
