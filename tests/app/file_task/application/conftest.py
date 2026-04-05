"""file_task application 层测试 fixtures

适合放置：临时 YAML 配置文件路径、具体任务配置对象构造器。
Pipeline 集成测试需真实 SQLite 和 FileResultRepository。
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from j_file_kit.app.file_task.application.config import (
    AnalyzeConfig,
    JavVideoOrganizeConfig,
)
from j_file_kit.app.file_task.application.jav_filename_util import (
    DEFAULT_SERIAL_PATTERN,
)
from j_file_kit.app.file_task.application.pipeline import FilePipeline
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.schema import SQLiteSchemaInitializer


@pytest.fixture
def base_extensions() -> dict[str, list[str]]:
    return {
        "video_extensions": [".mp4", ".mkv"],
        "image_extensions": [".jpg", ".png"],
        "archive_extensions": [".zip"],
    }


@pytest.fixture
def jav_video_organize_config_factory(
    base_extensions: dict[str, list[str]],
) -> Callable[..., JavVideoOrganizeConfig]:
    def _create(
        inbox_dir: Path | None = None,
        sorted_dir: Path | None = None,
        unsorted_dir: Path | None = None,
        archive_dir: Path | None = None,
        misc_dir: Path | None = None,
        **overrides: object,
    ) -> JavVideoOrganizeConfig:
        config = {
            "inbox_dir": inbox_dir,
            "sorted_dir": sorted_dir,
            "unsorted_dir": unsorted_dir,
            "archive_dir": archive_dir,
            "misc_dir": misc_dir,
            **base_extensions,
            "misc_file_delete_rules": {},
            **overrides,
        }
        return JavVideoOrganizeConfig.model_validate(config)

    return _create


@pytest.fixture
def analyze_config_factory(
    base_extensions: dict[str, list[str]],
) -> Callable[..., AnalyzeConfig]:
    def _create(
        sorted_dir: Path | None = None,
        unsorted_dir: Path | None = None,
        archive_dir: Path | None = None,
        misc_dir: Path | None = None,
        misc_file_delete_rules: dict[str, Any] | None = None,
        serial_pattern: re.Pattern[str] = DEFAULT_SERIAL_PATTERN,
    ) -> AnalyzeConfig:
        ext_sets = {k: set(v) for k, v in base_extensions.items()}
        return AnalyzeConfig(
            **ext_sets,
            sorted_dir=sorted_dir,
            unsorted_dir=unsorted_dir,
            archive_dir=archive_dir,
            misc_dir=misc_dir,
            misc_file_delete_rules=misc_file_delete_rules or {},
            serial_pattern=serial_pattern,
        )

    return _create


@pytest.fixture
def sqlite_connection_manager() -> SQLiteConnectionManager:
    """Pipeline 集成测试用：内存 SQLite 连接"""
    manager = SQLiteConnectionManager(Path(":memory:"))
    SQLiteSchemaInitializer(manager).initialize()
    return manager


@pytest.fixture
def file_result_repository(sqlite_connection_manager: SQLiteConnectionManager):
    """Pipeline 集成测试用：真实 FileResultRepository"""
    return FileResultRepositoryImpl(sqlite_connection_manager)


@pytest.fixture
def pipeline_with_real_repo(
    tmp_path: Path,
    analyze_config_factory: Callable[..., AnalyzeConfig],
    file_result_repository: FileResultRepositoryImpl,
) -> FilePipeline:
    """Pipeline 集成测试用：带真实仓储的 FilePipeline"""
    config = analyze_config_factory(
        sorted_dir=tmp_path / "sorted",
        unsorted_dir=tmp_path / "unsorted",
        archive_dir=tmp_path / "archive",
        misc_dir=tmp_path / "misc",
        misc_file_delete_rules={
            "keywords": ["rarbg", "sample"],
            "extensions": [".tmp", ".temp"],
            "max_size": 1048576,
        },
    )
    return FilePipeline(
        run_id=1,
        run_name="test",
        scan_root=tmp_path / "inbox",
        analyze_config=config,
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
