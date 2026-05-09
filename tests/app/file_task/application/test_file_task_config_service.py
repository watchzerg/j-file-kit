"""File task 配置服务单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.default_task_configs import (
    create_default_raw_file_organizer_task_config,
)
from j_file_kit.app.file_task.application.file_task_config_service import (
    FileTaskConfigService,
)
from j_file_kit.app.file_task.application.jav_task_config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.raw_task_config import RawFileOrganizeConfig
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
def valid_jav_task_config() -> TaskConfig:
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "workspace_root": "/media/jav_workspace",
            "misc_file_delete_rules": {},
        },
    )


@pytest.fixture
def jav_task_config_for_tmp(tmp_path: Path) -> TaskConfig:
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "workspace_root": str(tmp_path),
            "misc_file_delete_rules": {},
        },
    )


@pytest.fixture
def raw_task_config_for_tmp(tmp_path: Path) -> TaskConfig:
    return TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={"workspace_root": str(tmp_path)},
    )


class TestGetJavVideoOrganizerConfig:
    def test_returns_config_when_exists(
        self,
        mock_repository: MagicMock,
        valid_jav_task_config: TaskConfig,
    ) -> None:
        mock_repository.get_by_type.return_value = valid_jav_task_config
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
    def test_empty_update_returns_current(
        self, valid_jav_task_config: TaskConfig
    ) -> None:
        result = FileTaskConfigService.merge_jav_video_organizer_config(
            valid_jav_task_config.config,
            {},
        )
        assert result.workspace_root == Path("/media/jav_workspace")

    def test_partial_update_merges(self, valid_jav_task_config: TaskConfig) -> None:
        alt = Path("/media/jav_workspace/custom_root")
        result = FileTaskConfigService.merge_jav_video_organizer_config(
            valid_jav_task_config.config,
            {"workspace_root": str(alt)},
        )
        assert result.workspace_root == alt


class TestValidateAndSaveJavVideoOrganizerConfig:
    def test_valid_config_calls_update(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        mock_repository: MagicMock,
        jav_task_config_for_tmp: TaskConfig,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_common.JAV_MEDIA_ROOT",
            tmp_path,
        )
        mock_repository.get_by_type.return_value = jav_task_config_for_tmp
        merged = JavVideoOrganizeConfig.model_validate(jav_task_config_for_tmp.config)
        FileTaskConfigService.validate_and_save_jav_video_organizer_config(
            merged,
            mock_repository,
        )
        mock_repository.update.assert_called_once()
        call_args = mock_repository.update.call_args[0][0]
        assert call_args.type == TASK_TYPE_JAV_VIDEO_ORGANIZER
        assert (tmp_path / "inbox").is_dir()

    def test_enabled_passed_to_update(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        mock_repository: MagicMock,
        jav_task_config_for_tmp: TaskConfig,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_common.JAV_MEDIA_ROOT",
            tmp_path,
        )
        mock_repository.get_by_type.return_value = jav_task_config_for_tmp
        merged = JavVideoOrganizeConfig.model_validate(jav_task_config_for_tmp.config)
        FileTaskConfigService.validate_and_save_jav_video_organizer_config(
            merged,
            mock_repository,
            enabled=False,
        )
        call_args = mock_repository.update.call_args[0][0]
        assert call_args.enabled is False


class TestGetRawFileOrganizerConfig:
    def test_returns_config_when_exists(self, mock_repository: MagicMock) -> None:
        tc = create_default_raw_file_organizer_task_config()
        mock_repository.get_by_type.return_value = tc
        result = FileTaskConfigService.get_raw_file_organizer_config(mock_repository)
        assert isinstance(result, RawFileOrganizeConfig)
        mock_repository.get_by_type.assert_called_once_with(
            TASK_TYPE_RAW_FILE_ORGANIZER,
        )


class TestValidateAndSaveRawFileOrganizerConfig:
    def test_valid_config_calls_update(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        mock_repository: MagicMock,
        raw_task_config_for_tmp: TaskConfig,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_common.RAW_MEDIA_ROOT",
            tmp_path,
        )
        mock_repository.get_by_type.return_value = raw_task_config_for_tmp
        merged = RawFileOrganizeConfig.model_validate(raw_task_config_for_tmp.config)
        FileTaskConfigService.validate_and_save_raw_file_organizer_config(
            merged,
            mock_repository,
        )
        mock_repository.update.assert_called_once()
        call_args = mock_repository.update.call_args[0][0]
        assert call_args.type == TASK_TYPE_RAW_FILE_ORGANIZER
        assert (tmp_path / "inbox").is_dir()
