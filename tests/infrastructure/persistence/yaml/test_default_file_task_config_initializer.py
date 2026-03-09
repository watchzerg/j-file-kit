"""默认 file task 配置初始化器集成测试"""

from pathlib import Path

import pytest
import yaml

from j_file_kit.app.file_task.domain.models import TaskConfig
from j_file_kit.infrastructure.persistence.yaml.default_file_task_config_initializer import (
    DefaultFileTaskConfigInitializer,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "config" / "task_config.yaml"


@pytest.fixture
def default_configs() -> list[TaskConfig]:
    return [
        TaskConfig(
            type="task_a",
            enabled=True,
            config={"key": "value_a"},
        ),
        TaskConfig(
            type="task_b",
            enabled=False,
            config={"key": "value_b"},
        ),
    ]


class TestDefaultFileTaskConfigInitializer:
    """DefaultFileTaskConfigInitializer"""

    def test_creates_file_when_not_exists(
        self,
        config_path: Path,
        default_configs: list[TaskConfig],
    ) -> None:
        initializer = DefaultFileTaskConfigInitializer(config_path, default_configs)
        initializer.initialize()
        assert config_path.exists()
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert "task_a" in data
        assert "task_b" in data
        assert data["task_a"]["enabled"] is True
        assert data["task_b"]["enabled"] is False

    def test_skips_when_file_exists(
        self,
        config_path: Path,
        default_configs: list[TaskConfig],
    ) -> None:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            yaml.dump({"existing": {"enabled": True, "config": {}}}),
            encoding="utf-8",
        )
        initializer = DefaultFileTaskConfigInitializer(config_path, default_configs)
        initializer.initialize()
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert "existing" in data
        assert "task_a" not in data
