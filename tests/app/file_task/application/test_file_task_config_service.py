"""File task 配置服务单元测试

覆盖 get_jav_video_organizer_config、merge、validate_and_save。

validate_and_save 系列需要目录真实存在（触发存在性校验），同时路径必须在 JAV_MEDIA_ROOT 下
（已由 JavVideoOrganizeConfig model_validator 自动校验）。测试通过 monkeypatch
config.JAV_MEDIA_ROOT 到 tmp_path，使 tmp_path 路径通过模型约束，
并在 tmp_path 下创建真实子目录满足存在性校验。
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.config import (
    RAW_FILE_ORGANIZE_PATH_FIELD_NAMES,
    JavVideoOrganizeConfig,
    RawFileOrganizeConfig,
    create_default_raw_file_organizer_task_config,
)
from j_file_kit.app.file_task.application.file_task_config_service import (
    FileTaskConfigService,
)
from j_file_kit.app.file_task.domain.constants import (
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
)
from j_file_kit.app.file_task.domain.task_config import TaskConfig

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def valid_task_config() -> TaskConfig:
    """使用 /media/jav_workspace 路径构造 TaskConfig，用于不需要目录真实存在的测试。"""
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": "/media/jav_workspace/inbox",
            "sorted_dir": None,
            "unsorted_dir": None,
            "archive_dir": None,
            "misc_dir": None,
            "misc_file_delete_rules": {},
        },
    )


@pytest.fixture
def valid_task_config_with_real_dirs(tmp_path: Path) -> TaskConfig:
    """使用 tmp_path 路径构造 TaskConfig，配合 monkeypatch config.JAV_MEDIA_ROOT 使用。

    用于需要目录真实存在（存在性校验）的测试，需同时 monkeypatch
    j_file_kit.app.file_task.application.config.JAV_MEDIA_ROOT 为 tmp_path。
    """
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": str(tmp_path / "inbox"),
            "sorted_dir": None,
            "unsorted_dir": None,
            "archive_dir": None,
            "misc_dir": None,
            "misc_file_delete_rules": {},
        },
    )


@pytest.fixture
def valid_raw_task_config_with_real_dirs(tmp_path: Path) -> TaskConfig:
    """Raw 全目录字段指向 tmp_path 子目录；需 monkeypatch RAW_MEDIA_ROOT 为 tmp_path。"""
    cfg = {name: str(tmp_path / name) for name in RAW_FILE_ORGANIZE_PATH_FIELD_NAMES}
    return TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config=cfg,
    )


class TestGetJavVideoOrganizerConfig:
    """get_jav_video_organizer_config"""

    def test_returns_config_when_exists(
        self,
        mock_repository: MagicMock,
        valid_task_config: TaskConfig,
    ) -> None:
        mock_repository.get_by_type.return_value = valid_task_config
        result = FileTaskConfigService.get_jav_video_organizer_config(mock_repository)
        assert isinstance(result, JavVideoOrganizeConfig)
        mock_repository.get_by_type.assert_called_once_with(
            TASK_TYPE_JAV_VIDEO_ORGANIZER,
        )

    def test_raises_when_not_found(self, mock_repository: MagicMock) -> None:
        mock_repository.get_by_type.return_value = None
        with pytest.raises(ValueError, match="任务配置不存在"):
            FileTaskConfigService.get_jav_video_organizer_config(mock_repository)


class TestMergeJavVideoOrganizerConfig:
    """merge_jav_video_organizer_config"""

    def test_empty_update_returns_current(self, valid_task_config: TaskConfig) -> None:
        result = FileTaskConfigService.merge_jav_video_organizer_config(
            valid_task_config.config,
            {},
        )
        assert result.inbox_dir == Path("/media/jav_workspace/inbox")

    def test_partial_update_merges(self, valid_task_config: TaskConfig) -> None:
        result = FileTaskConfigService.merge_jav_video_organizer_config(
            valid_task_config.config,
            {"sorted_dir": "/media/jav_workspace/sorted"},
        )
        assert result.sorted_dir == Path("/media/jav_workspace/sorted")
        assert result.inbox_dir == Path("/media/jav_workspace/inbox")


class TestValidateAndSaveJavVideoOrganizerConfig:
    """validate_and_save_jav_video_organizer_config"""

    def test_validation_failure_raises(
        self,
        mock_repository: MagicMock,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
    ) -> None:
        config = jav_video_organize_config_factory(inbox_dir=None)
        with pytest.raises(ValueError, match="目录配置验证失败"):
            FileTaskConfigService.validate_and_save_jav_video_organizer_config(
                config,
                mock_repository,
            )
        mock_repository.update.assert_not_called()

    def test_valid_config_calls_update(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        mock_repository: MagicMock,
        valid_task_config_with_real_dirs: TaskConfig,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config.JAV_MEDIA_ROOT",
            tmp_path,
        )
        (tmp_path / "inbox").mkdir()
        mock_repository.get_by_type.return_value = valid_task_config_with_real_dirs
        merged = JavVideoOrganizeConfig.model_validate(
            valid_task_config_with_real_dirs.config,
        )
        FileTaskConfigService.validate_and_save_jav_video_organizer_config(
            merged,
            mock_repository,
        )
        mock_repository.update.assert_called_once()
        call_args = mock_repository.update.call_args[0][0]
        assert call_args.type == TASK_TYPE_JAV_VIDEO_ORGANIZER

    def test_enabled_passed_to_update(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        mock_repository: MagicMock,
        valid_task_config_with_real_dirs: TaskConfig,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config.JAV_MEDIA_ROOT",
            tmp_path,
        )
        (tmp_path / "inbox").mkdir()
        mock_repository.get_by_type.return_value = valid_task_config_with_real_dirs
        merged = JavVideoOrganizeConfig.model_validate(
            valid_task_config_with_real_dirs.config,
        )
        FileTaskConfigService.validate_and_save_jav_video_organizer_config(
            merged,
            mock_repository,
            enabled=False,
        )
        call_args = mock_repository.update.call_args[0][0]
        assert call_args.enabled is False


class TestGetRawFileOrganizerConfig:
    """get_raw_file_organizer_config"""

    def test_returns_config_when_exists(self, mock_repository: MagicMock) -> None:
        tc = create_default_raw_file_organizer_task_config()
        mock_repository.get_by_type.return_value = tc
        result = FileTaskConfigService.get_raw_file_organizer_config(mock_repository)
        assert isinstance(result, RawFileOrganizeConfig)
        mock_repository.get_by_type.assert_called_once_with(
            TASK_TYPE_RAW_FILE_ORGANIZER,
        )


class TestValidateAndSaveRawFileOrganizerConfig:
    """validate_and_save_raw_file_organizer_config"""

    def test_valid_config_calls_update(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        mock_repository: MagicMock,
        valid_raw_task_config_with_real_dirs: TaskConfig,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config.RAW_MEDIA_ROOT",
            tmp_path,
        )
        for name in RAW_FILE_ORGANIZE_PATH_FIELD_NAMES:
            (tmp_path / name).mkdir()
        mock_repository.get_by_type.return_value = valid_raw_task_config_with_real_dirs
        merged = RawFileOrganizeConfig.model_validate(
            valid_raw_task_config_with_real_dirs.config,
        )
        FileTaskConfigService.validate_and_save_raw_file_organizer_config(
            merged,
            mock_repository,
        )
        mock_repository.update.assert_called_once()
        call_args = mock_repository.update.call_args[0][0]
        assert call_args.type == TASK_TYPE_RAW_FILE_ORGANIZER
