from pathlib import Path

import pytest
from pydantic import BaseModel

from j_file_kit.app.config.domain.models import (
    GlobalConfig,
    TaskConfig,
    create_default_global_config,
)
from j_file_kit.app.file_task.application.config import (
    create_default_jav_video_organizer_task_config,
)

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


class _DummyConfig(BaseModel):
    enabled: bool


def test_task_config_get_config_returns_typed_model() -> None:
    task_config = TaskConfig(
        type="file_organize",
        enabled=True,
        config={"enabled": True},
    )

    parsed: _DummyConfig = task_config.get_config(_DummyConfig)

    assert isinstance(parsed, _DummyConfig)
    assert parsed.enabled is True


def test_create_default_global_config_has_none_fields() -> None:
    global_config = create_default_global_config()

    assert global_config.inbox_dir is None
    assert global_config.sorted_dir is None
    assert global_config.unsorted_dir is None
    assert global_config.archive_dir is None
    assert global_config.misc_dir is None
    assert global_config.starred_dir is None


def test_create_default_jav_video_organizer_task_config() -> None:
    task = create_default_jav_video_organizer_task_config()
    assert task.type == "jav_video_organizer"
    assert task.enabled is True
