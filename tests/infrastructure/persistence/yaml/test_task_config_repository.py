from pathlib import Path

import pytest
import yaml

from j_file_kit.app.task_config.domain.models import TaskConfig
from j_file_kit.infrastructure.persistence.yaml.task_config_repository import (
    TaskConfigRepositoryImpl,
)

pytestmark = pytest.mark.unit


def _write_yaml(path: Path, data: object) -> None:
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _sample_yaml_data() -> dict[str, object]:
    return {
        "test_task": {
            "enabled": True,
            "config": {
                "inbox_dir": "/inbox",
                "video_extensions": [".mp4"],
            },
        },
    }


class TestGetByType:
    def test_returns_task_config_when_exists(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        _write_yaml(config_path, _sample_yaml_data())
        repo = TaskConfigRepositoryImpl(config_path)

        result = repo.get_by_type("test_task")

        assert result is not None
        assert result.type == "test_task"
        assert result.enabled is True
        assert result.config["inbox_dir"] == "/inbox"

    def test_returns_none_when_type_not_found(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        _write_yaml(config_path, _sample_yaml_data())
        repo = TaskConfigRepositoryImpl(config_path)

        result = repo.get_by_type("nonexistent")

        assert result is None

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        config_path = tmp_path / "missing.yaml"
        repo = TaskConfigRepositoryImpl(config_path)

        result = repo.get_by_type("test_task")

        assert result is None

    def test_raises_on_invalid_yaml(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("{{invalid yaml", encoding="utf-8")
        repo = TaskConfigRepositoryImpl(config_path)

        with pytest.raises(ValueError, match="YAML 配置文件解析失败"):
            repo.get_by_type("test_task")

    def test_raises_on_non_dict_yaml(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("- item1\n- item2\n", encoding="utf-8")
        repo = TaskConfigRepositoryImpl(config_path)

        with pytest.raises(ValueError, match="顶层应为字典"):
            repo.get_by_type("test_task")


class TestUpdate:
    def test_updates_existing_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        _write_yaml(config_path, _sample_yaml_data())
        repo = TaskConfigRepositoryImpl(config_path)

        updated = TaskConfig(
            type="test_task",
            enabled=False,
            config={"inbox_dir": "/new_inbox", "video_extensions": [".avi"]},
        )
        repo.update(updated)

        result = repo.get_by_type("test_task")
        assert result is not None
        assert result.enabled is False
        assert result.config["inbox_dir"] == "/new_inbox"

    def test_raises_when_type_not_found(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        _write_yaml(config_path, _sample_yaml_data())
        repo = TaskConfigRepositoryImpl(config_path)

        with pytest.raises(ValueError, match="任务配置不存在"):
            repo.update(TaskConfig(type="nonexistent", enabled=True, config={}))

    def test_atomic_write_preserves_file_on_success(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        _write_yaml(config_path, _sample_yaml_data())
        repo = TaskConfigRepositoryImpl(config_path)

        repo.update(TaskConfig(type="test_task", enabled=True, config={"key": "val"}))

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert raw["test_task"]["config"]["key"] == "val"
