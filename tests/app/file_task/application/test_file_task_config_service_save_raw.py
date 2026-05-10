"""file_task_config_service RAW 保存行为测试。"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.file_task_config_service import (
    FileTaskConfigService,
)
from j_file_kit.app.file_task.application.raw_task_config import RawFileOrganizeConfig
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_RAW_FILE_ORGANIZER
from tests.app.file_task.application._file_task_config_service_testkit import (
    build_mock_repository,
    build_raw_task_config,
    patch_media_roots,
)

pytestmark = pytest.mark.unit


def test_validate_and_save_raw_calls_update(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    patch_media_roots(monkeypatch, tmp_path)
    repository = build_mock_repository()
    task_config = build_raw_task_config(tmp_path)
    repository.get_by_type.return_value = task_config
    merged = RawFileOrganizeConfig.model_validate(task_config.config)

    FileTaskConfigService.validate_and_save_raw_file_organizer_config(
        merged,
        repository,
    )

    repository.update.assert_called_once()
    call_args = repository.update.call_args[0][0]
    assert call_args.type == TASK_TYPE_RAW_FILE_ORGANIZER
    assert (tmp_path / "inbox").is_dir()


def test_validate_and_save_raw_disabled_does_not_create_inbox(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    patch_media_roots(monkeypatch, tmp_path)
    repository = build_mock_repository()
    task_config = build_raw_task_config(tmp_path)
    repository.get_by_type.return_value = task_config
    merged = RawFileOrganizeConfig.model_validate(task_config.config)

    FileTaskConfigService.validate_and_save_raw_file_organizer_config(
        merged,
        repository,
        enabled=False,
    )

    repository.update.assert_called_once()
    call_args = repository.update.call_args[0][0]
    assert call_args.enabled is False
    assert not (tmp_path / "inbox").exists()
