"""file_task_config_service 读取与合并行为测试。"""

from pathlib import Path

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
from tests.app.file_task.application._file_task_config_service_testkit import (
    build_jav_task_config,
    build_mock_repository,
)

pytestmark = pytest.mark.unit


def test_get_jav_config_returns_typed_model() -> None:
    repository = build_mock_repository()
    repository.get_by_type.return_value = build_jav_task_config(
        Path("/media/jav_workspace")
    )

    result = FileTaskConfigService.get_jav_video_organizer_config(repository)

    assert isinstance(result, JavVideoOrganizeConfig)
    repository.get_by_type.assert_called_once_with(TASK_TYPE_JAV_VIDEO_ORGANIZER)


def test_get_jav_config_raises_when_missing() -> None:
    repository = build_mock_repository()
    repository.get_by_type.return_value = None

    with pytest.raises(ValueError, match="任务配置不存在"):
        FileTaskConfigService.get_jav_video_organizer_config(repository)


def test_merge_jav_config_with_partial_update() -> None:
    current = build_jav_task_config(Path("/media/jav_workspace"))

    result = FileTaskConfigService.merge_jav_video_organizer_config(
        current.config,
        {"workspace_root": "/media/jav_workspace/custom_root"},
    )

    assert result.workspace_root == Path("/media/jav_workspace/custom_root")


def test_get_raw_config_returns_typed_model() -> None:
    repository = build_mock_repository()
    repository.get_by_type.return_value = (
        create_default_raw_file_organizer_task_config()
    )

    result = FileTaskConfigService.get_raw_file_organizer_config(repository)

    assert isinstance(result, RawFileOrganizeConfig)
    repository.get_by_type.assert_called_once_with(TASK_TYPE_RAW_FILE_ORGANIZER)
