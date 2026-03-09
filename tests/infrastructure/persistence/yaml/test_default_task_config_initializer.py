from pathlib import Path

import pytest
import yaml

from j_file_kit.app.file_task.domain.models import TaskConfig
from j_file_kit.infrastructure.persistence.yaml.default_task_config_initializer import (
    DefaultTaskConfigInitializer,
)

pytestmark = pytest.mark.unit


def _build_default_task_config(task_type: str) -> TaskConfig:
    return TaskConfig(
        type=task_type,
        enabled=True,
        config={"video_extensions": [".mp4"]},
    )


def test_creates_yaml_when_file_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    default_configs = [_build_default_task_config("task-a")]

    DefaultTaskConfigInitializer(config_path, default_configs).initialize()

    assert config_path.exists()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert "task-a" in data
    assert data["task-a"]["enabled"] is True
    assert data["task-a"]["config"]["video_extensions"] == [".mp4"]


def test_skips_when_file_already_exists(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.dump({"existing": {"enabled": True, "config": {}}}),
        encoding="utf-8",
    )

    default_configs = [_build_default_task_config("task-new")]
    DefaultTaskConfigInitializer(config_path, default_configs).initialize()

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert "existing" in data
    assert "task-new" not in data


def test_creates_parent_directory_if_needed(tmp_path: Path) -> None:
    config_path = tmp_path / "subdir" / "config.yaml"
    default_configs = [_build_default_task_config("task-a")]

    DefaultTaskConfigInitializer(config_path, default_configs).initialize()

    assert config_path.exists()


def test_writes_multiple_task_configs(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    default_configs = [
        _build_default_task_config("task-a"),
        _build_default_task_config("task-b"),
    ]

    DefaultTaskConfigInitializer(config_path, default_configs).initialize()

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert "task-a" in data
    assert "task-b" in data
