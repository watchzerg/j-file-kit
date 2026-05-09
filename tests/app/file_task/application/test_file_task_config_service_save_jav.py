"""file_task_config_service JAV 保存行为测试。"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.file_task_config_service import (
    FileTaskConfigService,
)
from j_file_kit.app.file_task.application.jav_task_config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from tests.app.file_task.application._file_task_config_service_testkit import (
    build_jav_task_config,
    build_mock_repository,
    patch_media_roots,
)

pytestmark = pytest.mark.unit


def test_validate_and_save_jav_calls_update(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    patch_media_roots(monkeypatch, tmp_path)
    repository = build_mock_repository()
    task_config = build_jav_task_config(tmp_path)
    repository.get_by_type.return_value = task_config
    merged = JavVideoOrganizeConfig.model_validate(task_config.config)

    FileTaskConfigService.validate_and_save_jav_video_organizer_config(
        merged,
        repository,
    )

    repository.update.assert_called_once()
    call_args = repository.update.call_args[0][0]
    assert call_args.type == TASK_TYPE_JAV_VIDEO_ORGANIZER
    assert (tmp_path / "inbox").is_dir()


def test_validate_and_save_jav_passes_enabled_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    patch_media_roots(monkeypatch, tmp_path)
    repository = build_mock_repository()
    task_config = build_jav_task_config(tmp_path)
    repository.get_by_type.return_value = task_config
    merged = JavVideoOrganizeConfig.model_validate(task_config.config)

    FileTaskConfigService.validate_and_save_jav_video_organizer_config(
        merged,
        repository,
        enabled=False,
    )

    call_args = repository.update.call_args[0][0]
    assert call_args.enabled is False
