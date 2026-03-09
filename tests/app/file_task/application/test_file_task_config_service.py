"""File task 配置服务单元测试

覆盖 get_jav_video_organizer_config、merge、validate_and_save。
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.file_task_config_service import (
    FileTaskConfigService,
)
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import TaskConfig

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def valid_task_config(tmp_path: Path) -> TaskConfig:
    inbox = tmp_path / "inbox"
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": str(inbox),
            "sorted_dir": None,
            "unsorted_dir": None,
            "archive_dir": None,
            "misc_dir": None,
            "video_extensions": [".mp4"],
            "image_extensions": [".jpg"],
            "archive_extensions": [".zip"],
            "misc_file_delete_rules": {},
        },
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

    def test_empty_update_returns_current(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        current = jav_video_organize_config_factory(inbox_dir=tmp_path)
        result = FileTaskConfigService.merge_jav_video_organizer_config(current, {})
        assert result is current

    def test_partial_update_merges(
        self,
        jav_video_organize_config_factory: Callable[..., JavVideoOrganizeConfig],
        tmp_path: Path,
    ) -> None:
        current = jav_video_organize_config_factory(
            inbox_dir=tmp_path,
            sorted_dir=None,
        )
        result = FileTaskConfigService.merge_jav_video_organizer_config(
            current,
            {"sorted_dir": str(tmp_path / "sorted")},
        )
        assert result.sorted_dir == tmp_path / "sorted"
        assert result.inbox_dir == tmp_path


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
        mock_repository: MagicMock,
        valid_task_config: TaskConfig,
    ) -> None:
        mock_repository.get_by_type.return_value = valid_task_config
        merged = JavVideoOrganizeConfig.model_validate(valid_task_config.config)
        FileTaskConfigService.validate_and_save_jav_video_organizer_config(
            merged,
            mock_repository,
        )
        mock_repository.update.assert_called_once()
        call_args = mock_repository.update.call_args[0][0]
        assert call_args.type == TASK_TYPE_JAV_VIDEO_ORGANIZER

    def test_enabled_passed_to_update(
        self,
        mock_repository: MagicMock,
        valid_task_config: TaskConfig,
    ) -> None:
        mock_repository.get_by_type.return_value = valid_task_config
        merged = JavVideoOrganizeConfig.model_validate(valid_task_config.config)
        FileTaskConfigService.validate_and_save_jav_video_organizer_config(
            merged,
            mock_repository,
            enabled=False,
        )
        call_args = mock_repository.update.call_args[0][0]
        assert call_args.enabled is False
