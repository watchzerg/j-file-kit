"""YAML 任务配置仓储集成测试"""

from pathlib import Path

import pytest
import yaml

from j_file_kit.app.file_task.domain.models import TaskConfig
from j_file_kit.infrastructure.persistence.yaml.file_task_config_repository import (
    FileTaskConfigRepositoryImpl,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "task_config.yaml"


@pytest.fixture
def repository(config_path: Path) -> FileTaskConfigRepositoryImpl:
    return FileTaskConfigRepositoryImpl(config_path)


class TestFileTaskConfigRepositoryGetByType:
    """get_by_type"""

    def test_empty_file_returns_none(
        self,
        repository: FileTaskConfigRepositoryImpl,
    ) -> None:
        assert repository.get_by_type("jav_video_organizer") is None

    def test_nonexistent_file_returns_none(
        self,
        repository: FileTaskConfigRepositoryImpl,
    ) -> None:
        assert repository.get_by_type("any") is None

    def test_returns_config_when_exists(
        self,
        repository: FileTaskConfigRepositoryImpl,
        config_path: Path,
    ) -> None:
        config_path.write_text(
            yaml.dump(
                {
                    "jav_video_organizer": {
                        "enabled": True,
                        "config": {"inbox_dir": None, "misc_file_delete_rules": {}},
                    },
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        result = repository.get_by_type("jav_video_organizer")
        assert result is not None
        assert result.type == "jav_video_organizer"
        assert result.enabled is True
        assert result.config.get("inbox_dir") is None


class TestFileTaskConfigRepositoryUpdate:
    """update"""

    def test_update_raises_when_type_not_exists(
        self,
        repository: FileTaskConfigRepositoryImpl,
    ) -> None:
        config = TaskConfig(
            type="unknown",
            enabled=True,
            config={},
        )
        with pytest.raises(ValueError, match="任务配置不存在"):
            repository.update(config)

    def test_update_persists(
        self,
        repository: FileTaskConfigRepositoryImpl,
        config_path: Path,
        tmp_path: Path,
    ) -> None:
        config_path.write_text(
            yaml.dump(
                {
                    "jav_video_organizer": {
                        "enabled": True,
                        "config": {"inbox_dir": None},
                    },
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        inbox_dir = str(tmp_path / "inbox")
        config = TaskConfig(
            type="jav_video_organizer",
            enabled=False,
            config={"inbox_dir": inbox_dir},
        )
        repository.update(config)
        result = repository.get_by_type("jav_video_organizer")
        assert result is not None
        assert result.enabled is False
        assert result.config.get("inbox_dir") == inbox_dir


class TestFileTaskConfigRepositoryYamlErrors:
    """YAML 解析错误"""

    def test_invalid_yaml_raises(
        self,
        repository: FileTaskConfigRepositoryImpl,
        config_path: Path,
    ) -> None:
        config_path.write_text("invalid: yaml: [", encoding="utf-8")
        with pytest.raises(ValueError, match="YAML 配置文件解析失败"):
            repository.get_by_type("any")

    def test_non_dict_top_level_raises(
        self,
        repository: FileTaskConfigRepositoryImpl,
        config_path: Path,
    ) -> None:
        config_path.write_text("- list", encoding="utf-8")
        with pytest.raises(ValueError, match="顶层应为字典"):
            repository.get_by_type("any")
