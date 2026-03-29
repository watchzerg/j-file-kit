"""配置验证器单元测试

覆盖 validate_inbox_dir、check_dir_conflicts、check_dirs_exist、
validate_jav_video_organizer_config，以及 JavVideoOrganizeConfig 的
/media 路径约束（model_validator）。

路径策略：
- 纯逻辑测试（不涉及文件系统）使用 /media/xxx 字面量路径，无需目录存在。
- check_dirs_exist / validate_jav_video_organizer_config 需要真实目录时使用 tmp_path
  并通过 monkeypatch config.MEDIA_ROOT 指向 tmp_path，使 tmp_path 子目录视为合法路径。
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.config_validator import (
    check_dir_conflicts,
    check_dirs_exist,
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
    ) -> None:
        config = jav_video_organize_config_factory(inbox_dir=Path("/media/inbox"))
        errors = validate_inbox_dir(config)
        assert errors == []


class TestCheckDirConflicts:
    """check_dir_conflicts 目录冲突检测"""

    def test_no_conflict_when_dirs_different(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        config = jav_video_organize_config_factory(
            inbox_dir=Path("/media/inbox"),
            sorted_dir=Path("/media/sorted"),
        )
        errors = check_dir_conflicts(config)
        assert errors == []

    def test_same_path_conflict(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        shared = Path("/media/shared")
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
    ) -> None:
        parent = Path("/media/parent")
        child = Path("/media/parent/child")
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
    ) -> None:
        parent = Path("/media/parent")
        child = Path("/media/parent/child")
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
    ) -> None:
        config = jav_video_organize_config_factory(
            inbox_dir=Path("/media/inbox"),
            sorted_dir=None,
            unsorted_dir=None,
        )
        errors = check_dir_conflicts(config)
        assert errors == []


class TestJavVideoOrganizeConfigDirConstraint:
    """JavVideoOrganizeConfig.validate_dir_paths_under_media_root model_validator

    /media 根目录约束已作为模型不变量内嵌于 JavVideoOrganizeConfig，
    在任何 model_validate 调用时自动触发。
    """

    def test_media_subpath_accepted(
        self,
        base_extensions: dict[str, list[str]],
    ) -> None:
        config = JavVideoOrganizeConfig.model_validate(
            {
                "inbox_dir": "/media/inbox",
                **base_extensions,
                "misc_file_delete_rules": {},
            },
        )
        assert config.inbox_dir == Path("/media/inbox")

    def test_non_media_path_raises(
        self,
        base_extensions: dict[str, list[str]],
    ) -> None:
        with pytest.raises(ValidationError):
            JavVideoOrganizeConfig.model_validate(
                {
                    "inbox_dir": "/nonexistent/inbox",
                    **base_extensions,
                    "misc_file_delete_rules": {},
                },
            )

    def test_multiple_non_media_paths_all_reported(
        self,
        base_extensions: dict[str, list[str]],
    ) -> None:
        with pytest.raises(ValidationError) as exc_info:
            JavVideoOrganizeConfig.model_validate(
                {
                    "inbox_dir": "/nonexistent/inbox",
                    "sorted_dir": "/var/sorted",
                    **base_extensions,
                    "misc_file_delete_rules": {},
                },
            )
        error_str = str(exc_info.value)
        assert "inbox_dir" in error_str
        assert "sorted_dir" in error_str

    def test_none_dirs_accepted(
        self,
        base_extensions: dict[str, list[str]],
    ) -> None:
        config = JavVideoOrganizeConfig.model_validate(
            {"inbox_dir": None, **base_extensions, "misc_file_delete_rules": {}},
        )
        assert config.inbox_dir is None


class TestCheckDirsExist:
    """check_dirs_exist 目录存在性校验"""

    def test_existing_dirs_return_empty(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config.MEDIA_ROOT",
            tmp_path,
        )
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        config = jav_video_organize_config_factory(inbox_dir=inbox)
        errors = check_dirs_exist(config)
        assert errors == []

    def test_nonexistent_dir_returns_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config.MEDIA_ROOT",
            tmp_path,
        )
        inbox = tmp_path / "inbox"  # 不创建目录
        config = jav_video_organize_config_factory(inbox_dir=inbox)
        errors = check_dirs_exist(config)
        assert len(errors) == 1
        assert "inbox_dir" in errors[0]

    def test_none_dirs_skipped(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        config = jav_video_organize_config_factory(inbox_dir=None)
        errors = check_dirs_exist(config)
        assert errors == []

    def test_multiple_nonexistent_dirs_all_reported(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config.MEDIA_ROOT",
            tmp_path,
        )
        config = jav_video_organize_config_factory(
            inbox_dir=tmp_path / "inbox",
            sorted_dir=tmp_path / "sorted",
        )
        errors = check_dirs_exist(config)
        assert len(errors) == 2
        assert any("inbox_dir" in e for e in errors)
        assert any("sorted_dir" in e for e in errors)


class TestValidateJavVideoOrganizerConfig:
    """validate_jav_video_organizer_config 组合验证"""

    def test_valid_config_returns_empty(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        """inbox 在 MEDIA_ROOT 下且存在时，返回空错误列表"""
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config.MEDIA_ROOT",
            tmp_path,
        )
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        config = jav_video_organize_config_factory(inbox_dir=inbox)
        errors = validate_jav_video_organizer_config(config)
        assert errors == []

    def test_inbox_missing_and_conflict_both_reported(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        shared = Path("/media/shared")
        config = jav_video_organize_config_factory(
            inbox_dir=None,
            sorted_dir=shared,
            unsorted_dir=shared,
        )
        errors = validate_jav_video_organizer_config(config)
        assert any("inbox_dir" in e for e in errors)
        assert any("都指向同一路径" in e for e in errors)
