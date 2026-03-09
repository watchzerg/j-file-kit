"""配置验证器单元测试

覆盖 validate_inbox_dir、check_dir_conflicts、validate_jav_video_organizer_config。
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.config_validator import (
    check_dir_conflicts,
    validate_inbox_dir,
    validate_jav_video_organizer_config,
)

pytestmark = pytest.mark.unit


class TestValidateInboxDir:
    """validate_inbox_dir 验证逻辑"""

    def test_inbox_dir_none_returns_error(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        config = jav_video_organize_config_factory(inbox_dir=None)
        errors = validate_inbox_dir(config)
        assert errors == ["待处理目录（inbox_dir）未设置"]

    def test_inbox_dir_set_returns_empty(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        config = jav_video_organize_config_factory(inbox_dir=tmp_path)
        errors = validate_inbox_dir(config)
        assert errors == []


class TestCheckDirConflicts:
    """check_dir_conflicts 目录冲突检测"""

    def test_no_conflict_when_dirs_different(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        inbox = tmp_path / "inbox"
        sorted_dir = tmp_path / "sorted"
        config = jav_video_organize_config_factory(
            inbox_dir=inbox,
            sorted_dir=sorted_dir,
        )
        errors = check_dir_conflicts(config)
        assert errors == []

    def test_same_path_conflict(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        shared = tmp_path / "shared"
        config = jav_video_organize_config_factory(
            inbox_dir=shared,
            sorted_dir=shared,
        )
        errors = check_dir_conflicts(config)
        assert len(errors) == 1
        assert "都指向同一路径" in errors[0]
        assert "inbox_dir" in errors[0]
        assert "sorted_dir" in errors[0]

    def test_parent_child_conflict(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        parent = tmp_path / "parent"
        child = parent / "child"
        config = jav_video_organize_config_factory(
            inbox_dir=parent,
            sorted_dir=child,
        )
        errors = check_dir_conflicts(config)
        assert len(errors) == 1
        assert "父目录" in errors[0]

    def test_child_parent_conflict(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        parent = tmp_path / "parent"
        child = parent / "child"
        config = jav_video_organize_config_factory(
            inbox_dir=child,
            sorted_dir=parent,
        )
        errors = check_dir_conflicts(config)
        assert len(errors) == 1
        assert "父目录" in errors[0]

    def test_none_dirs_ignored(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        config = jav_video_organize_config_factory(
            inbox_dir=tmp_path,
            sorted_dir=None,
            unsorted_dir=None,
        )
        errors = check_dir_conflicts(config)
        assert errors == []


class TestValidateJavVideoOrganizerConfig:
    """validate_jav_video_organizer_config 组合验证"""

    def test_valid_config_returns_empty(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        config = jav_video_organize_config_factory(inbox_dir=tmp_path)
        errors = validate_jav_video_organizer_config(config)
        assert errors == []

    def test_inbox_missing_and_conflict_both_reported(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        shared = tmp_path / "shared"
        config = jav_video_organize_config_factory(
            inbox_dir=None,
            sorted_dir=shared,
            unsorted_dir=shared,
        )
        errors = validate_jav_video_organizer_config(config)
        assert any("inbox_dir" in e for e in errors)
        assert any("都指向同一路径" in e for e in errors)
